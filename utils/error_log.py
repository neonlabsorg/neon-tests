import contextlib
import json
from pathlib import Path
from collections import defaultdict
from typing import Optional, Type, Generator

import pydantic

from utils.types import TestGroup


CMD_ERROR_LOG = "click_cmd_err.log"


class ErrorLogModel(pydantic.BaseModel):
    failures: defaultdict[TestGroup, list[str]] = defaultdict(list)
    errors: defaultdict[TestGroup, list[str]] = defaultdict(list)
    comments: list[str] = []


class ErrorLog:
    def __init__(self, file_path: str = CMD_ERROR_LOG):
        self.root_dir: Path = Path(__file__).resolve().parent.parent
        self.file_path: Path = self.root_dir / file_path
        self.model: Type[ErrorLogModel] = ErrorLogModel
        if not self.file_path.exists():
            self.create()

    def create(self) -> bool:
        try:
            data = self.model().model_dump_json(indent=4)
            self.file_path.write_text(data)
        except FileNotFoundError:
            return False
        else:
            return True

    def clear(self) -> bool:
        return self.create()

    def read(self) -> ErrorLogModel:
        with self.file_path.open() as f:
            data = json.load(f)
            log = self.model(**data)
        return log

    def has_logs(self) -> bool:
        log = self.read()
        return bool(log.failures or log.errors)

    def add_failure(self, test_group: TestGroup, test_name: str) -> ErrorLogModel:
        return self.__add_failure(test_group=test_group, test_name=test_name)

    def add_error(self, test_group: TestGroup, test_name: str) -> ErrorLogModel:
        with self._update() as log:
            log.errors[test_group].append(test_name)
        return log

    def add_failures(self, test_group: TestGroup, test_names: list[str]) -> ErrorLogModel:
        return self.__add_failure(test_group=test_group, test_names=test_names)

    @contextlib.contextmanager
    def _update(self) -> Generator[ErrorLogModel, None, None]:
        log = self.read()

        yield log

        data = log.model_dump_json(indent=4)
        self.file_path.write_text(data)

    def __add_failure(
            self,
            test_group: TestGroup,
            test_name: Optional[str] = None,
            test_names: Optional[list[str]] = None,
    ) -> ErrorLogModel:
        with self._update() as log:
            if test_name:
                log.failures[test_group].append(test_name)
            else:
                assert test_names
                log.failures[test_group].extend(test_names)
        return log

    def add_comment(self, text: str) -> ErrorLogModel:
        with self._update() as log:
            log.comments.append(text)
        return log

    def get_count_by_group(self) -> dict[TestGroup, int]:
        """Get count of both failed and errored tests by group"""
        log = self.read()
        failed_by_group = {group: len(log.failures[group]) for group in log.failures if len(log.failures[group]) > 0}
        errored_by_group = {group: len(log.errors[group]) for group in log.errors if len(log.errors[group]) > 0}
        count_by_group = {
            key: failed_by_group.get(key, 0) + errored_by_group.get(key, 0)
            for key in failed_by_group.keys() | errored_by_group.keys()
        }
        return count_by_group


error_log = ErrorLog()
