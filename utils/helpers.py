import os
import pathlib
import random
import string
import typing
import typing as tp
import logging
from queue import Queue

import allure
import base58
import solcx
import web3
from eth_abi import abi
from eth_utils import keccak
from solders.pubkey import Pubkey
from solcx import link_code
import polling2
from semantic_version import Version


T = tp.TypeVar('T')


@allure.step("Get contract abi")
def get_contract_abi(name, compiled):
    for key in compiled.keys():
        if name == key.rsplit(":")[-1]:
            return compiled[key]


@allure.step("Get contract interface")
def get_contract_interface(
    contract: str,
    version: str,
    contract_name: tp.Optional[str] = None,
    import_remapping: tp.Optional[dict] = None,
    libraries: tp.Optional[dict] = None,
):
    if not contract.endswith(".sol"):
        contract += ".sol"
    if contract_name is None:
        if "/" in contract:
            contract_name = contract.rsplit("/", 1)[1].rsplit(".", 1)[0]
        else:
            contract_name = contract.rsplit(".", 1)[0]

    solcx.install_solc(version)
    if contract.startswith("/"):
        contract_path = pathlib.Path(contract)
    else:
        contract_path = (pathlib.Path.cwd() / "contracts" / f"{contract}").absolute()
        if not contract_path.exists():
            contract_path = (pathlib.Path.cwd() / "contracts" / "external" / f"{contract}").absolute()

    assert contract_path.exists(), f"Can't found contract: {contract_path}"

    compiled = solcx.compile_files(
        [contract_path],
        output_values=["abi", "bin"],
        solc_version=Version(version),
        import_remappings=import_remapping,
        allow_paths=["."],
        optimize=True,
    )  # this allow_paths isn't very good...
    contract_interface = get_contract_abi(contract_name, compiled)
    if libraries:
        contract_interface["bin"] = link_code(contract_interface["bin"], libraries)

    return contract_interface


@allure.step("Gen hash of block")
def gen_hash_of_block(size: int) -> str:
    """Generates a block hash of the given size"""
    try:
        block_hash = hex(int.from_bytes(os.urandom(size), "big"))
        if len(block_hash[2:]) == size * 2:
            return block_hash
        else:
            return gen_hash_of_block(size)
    except ValueError:
        return gen_hash_of_block(size)


@allure.step("Generate random text")
def generate_text(min_len: int = 2, max_len: int = 200, simple: bool = True) -> str:
    length = random.randint(min_len, max_len)
    if simple:
        chars = string.ascii_letters + string.digits
    else:
        chars = string.printable[:-5]
    return "".join(random.choice(chars) for _i in range(length)).strip()


@allure.step("Wait condition")
def wait_condition(
        func_cond: tp.Callable[..., T],
        timeout_sec: float = 15,
        delay: float = 0.5,
        args: tp.Tuple = (),
        kwargs: tp.Optional[dict[str, tp.Any]] = None,
        max_tries: tp.Optional[int] = None,
        check_success: tp.Callable[[T], bool] = polling2.is_truthy,
        step_function: tp.Callable[[float], float] = polling2.step_constant,
        ignore_exceptions: tp.Tuple[Exception, ...] = (KeyError,),
        poll_forever: bool = False,
        collect_values: tp.Optional[Queue] = None,
        log: int = logging.NOTSET,
        log_error: int = logging.NOTSET
):
    return polling2.poll(
        target=func_cond,
        timeout=timeout_sec,
        step=delay,
        args=args,
        kwargs=kwargs,
        max_tries=max_tries,
        check_success=check_success,
        step_function=step_function,
        ignore_exceptions=ignore_exceptions,
        poll_forever=poll_forever,
        collect_values=collect_values,
        log=log,
        log_error=log_error,
    )


@allure.step("Decode function signature")
def decode_function_signature(function_name: str, args=None) -> str:
    data = keccak(text=function_name)[:4]
    if args is not None:
        types = function_name.split("(")[1].split(")")[0].split(",")
        data += abi.encode(types, args)
    return "0x" + data.hex()


@allure.step("Get functions signatures with params as keccak256 from contract abi")
def get_selectors(abi_):
    """Get functions signatures with params as keccak256 from contract abi"""
    selectors = []
    for function in filter(lambda item: item["type"] == "function", abi_):
        input_types = ""
        for input_ in function["inputs"]:
            if "struct" in input_["internalType"]:
                struct_name = input_["name"]
                struct_types = ",".join(i["type"] for i in input_["components"] if i["name"] != struct_name)
                input_types += "," + f"({struct_types})[]"
            else:
                input_types += "," + input_["type"]

        input_types = input_types[1:]
        encoded_selector = f"{function['name']}({input_types})"
        selectors.append(keccak(text=encoded_selector)[:4])
    return selectors


@allure.step("Create non-existing account address")
def create_invalid_address(length=20) -> str:
    """Create non-existing account address"""
    address = gen_hash_of_block(length)
    while web3.Web3.is_checksum_address(address):
        address = gen_hash_of_block(length)
    return address


def cryptohex(text: str):
    return "0x" + keccak(text=text).hex()


def int_to_hex(number: int):
    return int(number).to_bytes(32, "big").hex()


def hasattr_recursive(obj: typing.Any, attribute: str) -> bool:
    attr = attribute.split(".")
    temp_obj = obj
    for a in attr:
        if hasattr(temp_obj, a):
            temp_obj = getattr(temp_obj, a)
            continue
        return False

    return True


def bytes32_to_solana_pubkey(bytes32_data: str) -> Pubkey:
    byte_data = bytes.fromhex(bytes32_data)
    return Pubkey(byte_data)


def solana_pubkey_to_bytes32(solana_pubkey):
    byte_data = base58.b58decode(str(solana_pubkey))
    return byte_data


def serialize_instruction(program_id: Pubkey, instruction) -> bytes:
    program_id_bytes = solana_pubkey_to_bytes32(program_id)
    serialized = program_id_bytes + len(instruction.accounts).to_bytes(8, "little")

    for key in instruction.accounts:
        serialized += bytes(key.pubkey)
        serialized += key.is_signer.to_bytes(1, "little")
        serialized += key.is_writable.to_bytes(1, "little")

    serialized += len(instruction.data).to_bytes(8, "little") + instruction.data
    return serialized


def case_snake_to_camel(snake_str: str) -> str:
    components = snake_str.split('_')
    camel_case = components[0].lower() + ''.join(x.title() for x in components[1:])
    return camel_case


def padhex(s, size):
    return '0x' + s[2:].zfill(size)
