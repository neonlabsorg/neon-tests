import typing as tp

import pydantic

from utils.models.model_types import HexString


class EthFeeHistoryResult(pydantic.BaseModel):
    baseFeePerGas: list[HexString]
    gasUsedRatio: list[tp.Union[int, float]]
    oldestBlock: HexString
    reward: tp.Optional[list[list[HexString]]] = None
