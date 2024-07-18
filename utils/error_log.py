import contextlib
import json
from pathlib import Path
from collections import defaultdict
from typing import Optional, Type, Generator

import pydantic
from filelock import FileLock

from utils.types import TestGroup


CMD_ERROR_LOG = "click_cmd_err.log"


class ErrorLogModel(pydantic.BaseModel):
    failures: defaultdict[TestGroup, list[str]] = defaultdict(list)
    comments: list[str] = []


class ErrorLog:
    def __init__(self, file_path: str = CMD_ERROR_LOG):
        self.model: Type[ErrorLogModel] = ErrorLogModel
        self.root_dir: Path = Path(__file__).resolve().parent.parent
        self.file_path: Path = self.root_dir / file_path
        self.lock = FileLock(lock_file=self.file_path.with_suffix(self.file_path.suffix + ".lock"), is_singleton=True)

        with self.lock:
            if not self.file_path.exists():
                self.__create()

    def __create(self) -> bool:
        try:
            data = self.model().model_dump_json(indent=4)
            self.file_path.write_text(data)
        except FileNotFoundError:
            return False
        else:
            return True

    def clear(self) -> bool:
        with self.lock:
            return self.__create()

    def read(self) -> ErrorLogModel:
        with self.file_path.open() as f:
            data = json.load(f)
            failures = data["failures"]
            failures: defaultdict[TestGroup, list[str]] = defaultdict(list, failures)
            comments = data["comments"]
            log = self.model(failures=failures, comments=comments)
        return log

    def has_logs(self) -> bool:
        log = self.read()
        return bool(log.failures)

    def add_failure(self, test_group: TestGroup, test_name: str) -> ErrorLogModel:
        with self._update() as log:
            log.failures[test_group].append(test_name)
        return log

    def add_failures(self, test_group: TestGroup, test_names: list[str]) -> ErrorLogModel:
        with self._update() as log:
            log.failures[test_group].extend(test_names)
        return log

    @contextlib.contextmanager
    def _update(self) -> Generator[ErrorLogModel, None, None]:
        with self.lock:
            log = self.read()

            yield log

            data = log.model_dump_json(indent=4)
            self.file_path.write_text(data)

    def add_comment(self, text: str) -> ErrorLogModel:
        with self._update() as log:
            log.comments.append(text)
        return log

    def get_count_by_group(self) -> defaultdict[TestGroup, int]:
        log = self.read()
        count_by_group = {group: len(log.failures[group]) for group in log.failures if len(log.failures[group]) > 0}
        return defaultdict(int, count_by_group)


error_log = ErrorLog()
