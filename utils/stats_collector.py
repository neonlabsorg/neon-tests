import contextlib
import inspect
import json
from pathlib import Path
from typing import Callable, Generator
from functools import wraps

from filelock import FileLock
from web3.types import TxReceipt

import conftest
from utils.models.cost_report_model import CostReportModel, CostReportAction


class StatisticsCollector:
    def __init__(self, report_file: Path):
        self.report_file: Path = report_file
        self.model = CostReportModel(name=report_file.stem.removesuffix("-report"))
        self.lock = FileLock(self.report_file.with_suffix(self.report_file.suffix + ".lock"), is_singleton=True)

    def __create(self):
        data = self.model.model_dump_json(indent=4)
        self.report_file.write_text(data)

    def read(self) -> CostReportModel:
        with self.report_file.open() as f:
            data = json.load(f)
        return CostReportModel(**data)

    @contextlib.contextmanager
    def _update(self) -> Generator[CostReportModel, None, None]:
        with self.lock:
            if not self.report_file.exists():
                self.__create()

            report = self.read()

            yield report

            data = report.model_dump_json(indent=4)
            self.report_file.write_text(data)


def cost_report(func: Callable[..., TxReceipt]) -> Callable[..., TxReceipt]:
    @wraps(func)
    def wrapper(*args, **kwargs) -> TxReceipt:
        receipt = func(*args, **kwargs)

        if conftest.COST_REPORT_DIR != Path():
            file_path = Path(inspect.getfile(func)).resolve()
            neon_tests_index = file_path.parts.index('neon-tests')
            relative_path = Path(*file_path.parts[neon_tests_index + 1:]).with_suffix('')
            class_name = ".".join(func.__qualname__.split(".")[:-1]) if "." in func.__qualname__ else ""
            report_file_name = '.'.join(relative_path.parts) + f".{class_name}" + "-report.json"
            report_file = conftest.COST_REPORT_DIR / report_file_name

            collector = StatisticsCollector(report_file)

            used_gas = receipt['gasUsed']
            gas_price = receipt['effectiveGasPrice']
            tx_hash = receipt['transactionHash'].hex()

            action = CostReportAction(
                name=func.__name__,
                usedGas=used_gas,
                gasPrice=gas_price,
                tx=tx_hash,
            )

            with collector._update() as report:
                report.actions.append(action)

        return receipt

    return wrapper
