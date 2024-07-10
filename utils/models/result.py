import typing as tp
from typing import List, Union

from pydantic import BaseModel, Field, model_validator

from utils.models.model_types import (
    BalanceString,
    EstimateGasPriceString,
    FalseOnly,
    GasPriceString,
    HexString,
    IdField,
    JsonRPCString,
    NeonVersionString,
    NetVersionString,
    NonZeroBytesString,
    StorageString,
    ZeroBytesString,
)

NEON_FIELDS = [
    "neonAccountSeedVersion",
    "neonMaxEvmStepsInLastIteration",
    "neonMinEvmStepsInIteration",
    "neonGasLimitMultiplierWithoutChainId",
    "neonHolderMessageSize",
    "neonPaymentToTreasury",
    "neonStorageEntriesInContractAccount",
    "neonTreasuryPoolCount",
    "neonTreasuryPoolSeed",
    "neonEvmProgramId",
]


class EthResult(BaseModel):
    jsonrpc: JsonRPCString
    id: IdField
    result: HexString

    class Config:
        extra = "forbid"


class NeonGetEvmParamsDetails(BaseModel):
    neonAccountSeedVersion: int
    neonMaxEvmStepsInLastIteration: int
    neonMinEvmStepsInIteration: int
    neonGasLimitMultiplierWithoutChainId: int
    neonHolderMessageSize: int
    neonPaymentToTreasury: int
    neonStorageEntriesInContractAccount: int
    neonTreasuryPoolCount: int
    neonTreasuryPoolSeed: str
    neonEvmProgramId: str

    class Config:
        extra = "forbid"


class NeonGetEvmParamsResult(EthResult):
    result: NeonGetEvmParamsDetails


class EthGasPriceResult(EthResult):
    result: GasPriceString

    class Config:
        extra = "forbid"


class EthGetBalanceResult(EthResult):
    result: BalanceString

    class Config:
        extra = "forbid"


class EthGetCodeResult(EthResult):
    result: NonZeroBytesString

    class Config:
        extra = "forbid"


class EthGetZeroCodeResult(EthResult):
    result: ZeroBytesString

    class Config:
        extra = "forbid"


class Web3ClientVersionResult(EthResult):
    result: str

    class Config:
        extra = "forbid"


class NetVersionResult(EthResult):
    result: NetVersionString

    class Config:
        extra = "forbid"


class EthGetStorageAt(EthResult):
    result: StorageString

    class Config:
        extra = "forbid"


class EthMiningResult(EthResult):
    result: bool

    class Config:
        extra = "forbid"


class SyncingFields(BaseModel):
    startingBlock: HexString
    currentBlock: HexString
    highestBlock: HexString

    class Config:
        extra = "allow"


class EthSyncingResult(EthResult):
    result: Union[SyncingFields, FalseOnly]


class EthEstimateGas(EthResult):
    result: EstimateGasPriceString


class Transaction(BaseModel):
    blockHash: HexString
    blockNumber: HexString
    from_: HexString = Field(alias="from")
    gas: HexString
    gasPrice: HexString
    hash: HexString
    input: HexString
    nonce: HexString
    to: HexString
    transactionIndex: HexString
    value: HexString
    chainId: HexString
    v: HexString
    r: HexString
    s: HexString
    type: HexString

    class Config:
        extra = "forbid"


class EthGetBlockByHashDetails(BaseModel):
    number: Union[HexString, None]
    hash: Union[HexString, None]
    parentHash: HexString
    nonce: Union[HexString, None]
    sha3Uncles: HexString
    logsBloom: HexString
    transactionsRoot: HexString
    stateRoot: HexString
    receiptsRoot: HexString
    miner: tp.Optional[HexString]  # check with newer geth
    difficulty: HexString
    totalDifficulty: HexString
    extraData: HexString
    size: HexString
    gasLimit: HexString
    gasUsed: HexString
    timestamp: HexString
    transactions: Union[List[HexString], List[Transaction]]
    uncles: List[HexString]
    mixHash: HexString

    class Config:
        extra = "forbid"


class EthGetBlockByHashResult(EthResult):
    result: Union[EthGetBlockByHashDetails, None]

    class Config:
        extra = "forbid"


class EthGetLogsDetails(BaseModel):
    removed: bool
    logIndex: Union[HexString, None]
    blockNumber: Union[HexString, None]
    blockHash: Union[HexString, None]
    transactionHash: Union[HexString, None]
    transactionIndex: Union[HexString, None]
    address: HexString
    data: Union[HexString, ZeroBytesString]
    topics: List[HexString]

    class Config:
        extra = "forbid"


class EthGetLogs(EthResult):
    result: List[EthGetLogsDetails]

    class Config:
        extra = "forbid"


class NeonGetLogsDetails(BaseModel):
    removed: bool
    logIndex: Union[HexString, None]
    blockNumber: Union[HexString, None]
    blockHash: Union[HexString, None]
    transactionHash: Union[HexString, None]
    transactionIndex: Union[HexString, None]
    address: HexString
    data: Union[HexString, ZeroBytesString]
    topics: List[HexString]
    solanaTransactionSignature: str
    solanaInstructionIndex: int
    solanaInnerInstructionIndex: Union[int, None]
    neonEventType: str
    neonEventLevel: int
    neonEventOrder: int
    neonIsHidden: bool
    neonIsReverted: bool

    class Config:
        extra = "forbid"


class NeonGetLogs(EthResult):
    result: List[NeonGetLogsDetails]

    class Config:
        extra = "forbid"


class EthGetBlockByNumberAndIndexResult(EthResult):
    result: Transaction


class EthGetBlockByNumberAndIndexNoneResult(EthResult):
    result: None


class ReceiptDetails(BaseModel):
    transactionHash: HexString
    transactionIndex: HexString
    blockHash: HexString
    blockNumber: HexString
    from_: HexString = Field(alias="from")
    to: Union[HexString, None]
    cumulativeGasUsed: HexString
    effectiveGasPrice: HexString
    gasUsed: HexString
    contractAddress: Union[HexString, None]
    logs: List[EthGetLogsDetails]
    logsBloom: HexString
    type: HexString
    status: tp.Optional[HexString] = None
    root: tp.Optional[HexString] = None

    @model_validator(mode="before")
    @classmethod
    def check_status(cls, values):
        if values.get("status") is None and values.get("root") is None:
            raise ValueError("Either status or root must be present")
        if values.get("status") is not None and values.get("root") is not None:
            raise ValueError("Either status or root must be present")
        return values

    class Config:
        extra = "forbid"


class EthGetTransactionReceiptResult(EthResult):
    result: ReceiptDetails


class EthGetTransactionByHashResult(EthResult):
    result: Transaction
