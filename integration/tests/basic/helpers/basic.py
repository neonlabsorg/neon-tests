from dataclasses import dataclass
from enum import Enum


@dataclass
class AccountData:
    address: str
    key: str = ""


class Tag(Enum):
    EARLIEST = "earliest"
    LATEST = "latest"
    PENDING = "pending"
    SAFE = "safe"
    FINALIZED = "finalized"


class NeonEventType(Enum):
    EnterCreate = "EnterCreate"
    ExitStop = "ExitStop"
    Return = "Return"
    Log = "Log"
    EnterCall = "EnterCall"
    EnterCallCode = "EnterCallCode"
    EnterStaticCall = "EnterStaticCall"
    EnterDelegateCall = "EnterDelegateCall"
    EnterCreate2 = "EnterCreate2"
    ExitReturn = "ExitReturn"
    ExitSelfDestruct = "ExitSelfDestruct"
    ExitRevert = "ExitRevert"
    ExitSendAll = "ExitSendAll"
    Cancel = "Cancel"
    Lost = "Lost"
    InvalidRevision = "InvalidRevision"
    StepReset = "StepReset"

class SolanaInstructionName(Enum):
    CollectTreasure = "CollectTreasure"
    HolderCreate = "HolderCreate"
    HolderDelete = "HolderDelete"
    HolderWrite = "HolderWrite"
    CreateAccountBalance = "CreateAccountBalance"
    Deposit = "Deposit"
    TxExecFromData = "TxExecFromData"
    TxExecFromAccount = "TxExecFromAccount"
    TxStepFromData = "TxStepFromData"
    TxStepFromAccount = "TxStepFromAccount"
    TxStepFromAccountNoChainId = "TxStepFromAccountNoChainId"
    TxExecFromDataSolanaCall = "TxExecFromDataSolanaCall"
    TxExecFromAccountSolanaCall = "TxExecFromAccountSolanaCall"
    CancelWithHash = "CancelWithHash"
    CreateOperatorBalance = "CreateOperatorBalance"
    DeleteOperatorBalance = "DeleteOperatorBalance"
    WithdrawOperatorBalance = "WithdrawOperatorBalance"
    OldDepositV1004 = "OldDepositV1004"
    OldCreateAccountV1004 = "OldCreateAccountV1004"
    OldTxExecFromDataV1004 = "OldTxExecFromDataV1004"
    OldTxExecFromAccountV1004 = "OldTxExecFromAccountV1004"
    OldTxStepFromDataV1004 = "OldTxStepFromDataV1004"
    OldTxStepFromAccountV1004 = "OldTxStepFromAccountV1004"
    OldTxStepFromAccountNoChainIdV1004 = "OldTxStepFromAccountNoChainIdV1004"
    OldCancelWithHashV1004 = "OldCancelWithHashV1004"

class SolanaInstructionCode(Enum):
    CollectTreasure = 30
    HolderCreate = 36
    HolderDelete = 37
    HolderWrite = 38
    CreateAccountBalance = 48
    Deposit = 49
    TxExecFromData = 50
    TxExecFromAccount = 51
    TxStepFromData = 52
    TxStepFromAccount = 53
    TxStepFromAccountNoChainId = 54
    TxExecFromDataSolanaCall = 56
    TxExecFromAccountSolanaCall = 57
    CancelWithHash = 55
    CreateOperatorBalance = 58
    DeleteOperatorBalance = 59
    WithdrawOperatorBalance = 60
    OldDepositV1004 = 39
    OldCreateAccountV1004 = 40
    OldTxExecFromDataV1004 = 31
    OldTxExecFromAccountV1004 = 42
    OldTxStepFromDataV1004 = 32
    OldTxStepFromAccountV1004 = 33
    OldTxStepFromAccountNoChainIdV1004 = 34
    OldCancelWithHashV1004 = 35
