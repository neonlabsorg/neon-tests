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
