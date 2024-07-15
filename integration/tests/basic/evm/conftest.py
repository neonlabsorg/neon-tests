import json
import pathlib

import pytest
from solana.publickey import PublicKey
from web3.contract import Contract
from packaging import version
from clickfile import network_manager
from utils import helpers, web3client
from utils.accounts import EthAccounts
from utils.solana_client import SolanaClient
from utils.web3client import Web3Client

SPL_TOKEN_ADDRESS = "0xFf00000000000000000000000000000000000004"
METAPLEX_ADDRESS = "0xff00000000000000000000000000000000000005"


def pytest_collection_modifyitems(config, items):
    deselected_items = []
    selected_items = []
    deselected_marks = []
    network_name = config.getoption("--network")

    if network_name == "geth":
        return

    settings = network_manager.get_network_object(network_name)
    web3_client = web3client.NeonChainWeb3Client(settings["proxy_url"])

    raw_proxy_version = web3_client.get_proxy_version()["result"]

    if "Neon-proxy/" in raw_proxy_version:
        raw_proxy_version = raw_proxy_version.split("Neon-proxy/")[1].strip()
    proxy_dev = "dev" in raw_proxy_version

    if "-" in raw_proxy_version:
        raw_proxy_version = raw_proxy_version.split("-")[0].strip()
    proxy_version = version.parse(raw_proxy_version)

    if network_name == "devnet":
        deselected_marks.append("only_stands")
    else:
        deselected_marks.append("only_devnet")

    if network_name != "night-stand":
        deselected_marks.append("slow")

    envs_file = config.getoption("--envs")
    with open(pathlib.Path().parent.parent / envs_file, "r+") as f:
        environments = json.load(f)

    if len(environments[network_name]["network_ids"]) == 1:
        deselected_marks.append("multipletokens")

    for item in items:
        raw_item_pv = [mark.args[0] for mark in item.iter_markers(name="proxy_version")]
        select_item = True

        if any([item.get_closest_marker(mark) for mark in deselected_marks]):
            deselected_items.append(item)
            select_item = False
        elif len(raw_item_pv) > 0:
            item_proxy_version = version.parse(raw_item_pv[0])

            if not proxy_dev and item_proxy_version > proxy_version:
                deselected_items.append(item)
                select_item = False

        if select_item:
            selected_items.append(item)

    config.hook.pytest_deselected(items=deselected_items)
    items[:] = selected_items


@pytest.fixture(scope="class")
def precompiled_contract(web3_client, faucet, accounts):
    contract, contract_deploy_tx = web3_client.deploy_and_get_contract(
        "precompiled/CommonCaller", "0.8.10", accounts[0]
    )
    return contract


@pytest.fixture(scope="class")
def metaplex_caller(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract(
        "precompiled/MetaplexCaller", "0.8.10", account=accounts[0], contract_name="MetaplexCaller"
    )
    return contract


@pytest.fixture(scope="class")
def metaplex(web3_client):
    contract_interface = helpers.get_contract_interface("neon-evm/Metaplex", "0.8.10", contract_name="Metaplex")
    contract = web3_client.eth.contract(address=METAPLEX_ADDRESS, abi=contract_interface["abi"])
    return contract


@pytest.fixture(scope="class")
def spl_token(web3_client):
    contract_interface = helpers.get_contract_interface("neon-evm/SPLToken", "0.8.10")
    contract = web3_client.eth.contract(address=SPL_TOKEN_ADDRESS, abi=contract_interface["abi"])
    return contract


@pytest.fixture(scope="class")
def spl_token_caller(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract(
        "precompiled/SplTokenCaller", "0.8.10", account=accounts[0], contract_name="SplTokenCaller"
    )
    return contract


@pytest.fixture(scope="class")
def blockhash_contract(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract(
        "opcodes/BlockHash",
        "0.8.10",
        contract_name="BlockHashTest",
        account=accounts[0],
    )
    return contract


@pytest.fixture(scope="class")
def query_account_caller_contract(
        web3_client: Web3Client,
        accounts: EthAccounts,
) -> Contract:
    contract, _ = web3_client.deploy_and_get_contract(
        "precompiled/QueryAccountCaller.sol",
        "0.8.10",
        contract_name="QueryAccountCaller",
        account=accounts[0],
    )
    return contract


@pytest.fixture(scope="session")
def max_non_existent_solana_address(
        sol_client_session: SolanaClient,
) -> int:
    address_uint_256 = 2 ** 256
    address_exists = True

    while address_exists:
        address_uint_256 -= 1
        pubkey = PublicKey(address_uint_256.to_bytes(32, byteorder='big'))
        address_exists = sol_client_session.get_account_info(pubkey=pubkey).value is not None

    return address_uint_256
