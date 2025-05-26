import hashlib
import json
import logging
import os
import pathlib
from typing import Literal

import allure
import eth_abi
import pytest
from eth_utils import abi, to_checksum_address
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.rpc.responses import GetTransactionResp

from integration.tests.neon_evm.conftest import prepare_operator
from integration.tests.neon_evm.utils.ethereum import make_eth_transaction, make_contract_call_trx
from integration.tests.neon_evm.utils.neon_api_client import NeonApiClient
from utils.consts import OPERATOR_KEYPAIR_PATH, LAMPORT_PER_SOL
from utils.evm_loader import EvmLoader
from utils.neon_user import NeonUser
from utils.scheduled_trx import ScheduledTransaction
from utils.types import Caller, TreasuryPool

logger = logging.getLogger(__name__)


@pytest.fixture
def deterministic_index_of_process(request: pytest.FixtureRequest) -> int:
    mark: pytest.Mark = request.node.get_closest_marker("deterministic_index_of_process")
    process_index = mark.args[0]
    return process_index


@pytest.fixture(scope="session")
def deterministic_key_pairs() -> dict[Literal["sender_with_tokens", "session_user"], list[Keypair]]:
    pairs: list[Keypair] = []
    count = 50

    for i in range(count):
        seed_bytes = hashlib.sha256(f"Seed_{i}".encode()).digest()
        keypair = Keypair.from_seed(seed_bytes[:32])
        pairs.append(keypair)

    return {
        "sender_with_tokens": [pairs[i] for i in range(count // 2)],
        "session_user": [pairs[i] for i in range(count // 2, count)],
    }


@pytest.fixture
def deterministic_operator_keypair(
    request: pytest.FixtureRequest, evm_loader: EvmLoader, deterministic_index_of_process: int
) -> Keypair:
    key_file = pathlib.Path(f"{OPERATOR_KEYPAIR_PATH}/id{deterministic_index_of_process}.json")
    return prepare_operator(key_file, evm_loader)


@pytest.fixture
def deterministic_treasury_pool(
    request: pytest.FixtureRequest,
    evm_loader: EvmLoader,
    pytestconfig,
    bank_account: Keypair,
    deterministic_index_of_process: int,
) -> TreasuryPool:
    index = deterministic_index_of_process
    evm_loader.create_treasury_pool_address(index)

    if pytestconfig.getoption("--network") == "mainnet":
        address = Pubkey.from_string(os.environ.get("MAINNET_TREASURY_POOL_ADDRESS"))
    else:
        address = evm_loader.create_treasury_pool_address(index)

    index_buf = index.to_bytes(4, "little")
    balance = evm_loader.get_solana_balance(address)

    if balance < 5 * LAMPORT_PER_SOL:
        evm_loader.request_airdrop(address, 5 * LAMPORT_PER_SOL, commitment=Confirmed)

    return TreasuryPool(index, address, index_buf)


@pytest.fixture
def deterministic_sender_with_tokens(
    request: pytest.FixtureRequest,
    evm_loader: EvmLoader,
    deterministic_operator_keypair: Keypair,
    deterministic_key_pairs: dict[Literal["sender_with_tokens", "session_user"], list[Keypair]],
) -> Caller:
    mark: pytest.Mark = request.node.get_closest_marker("deterministic_sender_with_tokens_index")
    index = mark.args[0]
    key = deterministic_key_pairs["sender_with_tokens"][index]
    user = evm_loader.make_new_user(deterministic_operator_keypair, key=key)
    evm_loader.deposit_neon(deterministic_operator_keypair, user.eth_address, 10000000)
    return user


@pytest.fixture
def deterministic_session_user(
    request: pytest.FixtureRequest,
    evm_loader: EvmLoader,
    deterministic_operator_keypair: Keypair,
    deterministic_key_pairs: dict[Literal["sender_with_tokens", "session_user"], list[Keypair]],
) -> Caller:
    mark: pytest.Mark = request.node.get_closest_marker("deterministic_session_user_index")
    index = mark.args[0]
    key = deterministic_key_pairs["session_user"][index]
    return evm_loader.make_new_user(deterministic_operator_keypair, key=key)


@pytest.fixture
def deterministic_holder_acc(
    request: pytest.FixtureRequest, deterministic_operator_keypair: Keypair, evm_loader: EvmLoader
) -> Pubkey:
    mark: pytest.Mark = request.node.get_closest_marker("deterministic_holder_acc_seed")
    seed = f"{mark.args[0]}_seed"
    return evm_loader.create_holder(signer=deterministic_operator_keypair, seed=seed)


def allure_attach_accounts_data(resp: GetTransactionResp, evm_loader: EvmLoader):
    accounts_data = {}

    for pubkey in resp.value.transaction.transaction.message.account_keys:
        info = evm_loader.get_account_info(pubkey).value

        if info:
            accounts_data[str(pubkey)] = str(info.data)

    allure.attach(
        body=json.dumps(obj=accounts_data, indent=2),
        name="Used accounts data",
        attachment_type=allure.attachment_type.JSON,
    )


@pytest.mark.only_stands
class TestComputeUnits:
    @pytest.mark.deterministic_index_of_process(18)  # must be greater than max number of --numprocesses
    @pytest.mark.deterministic_sender_with_tokens_index(0)
    @pytest.mark.deterministic_session_user_index(0)
    @pytest.mark.deterministic_holder_acc_seed(0)
    def test_simple_transfer(
        self,
        deterministic_operator_keypair: Keypair,
        deterministic_treasury_pool: TreasuryPool,
        deterministic_sender_with_tokens: Caller,
        deterministic_session_user: Caller,
        evm_loader: EvmLoader,
        deterministic_holder_acc: Pubkey,
    ):
        signed_tx = make_eth_transaction(
            evm_loader=evm_loader,
            to_addr=deterministic_session_user.eth_address,
            data=None,
            caller=deterministic_sender_with_tokens,
            value=10,
            gas=10000,
        )

        resp = evm_loader.execute_trx_from_instruction(
            operator=deterministic_operator_keypair,
            holder_acc=deterministic_holder_acc,
            treasury_address=deterministic_treasury_pool.account,
            treasury_buffer=deterministic_treasury_pool.buffer,
            instruction=signed_tx,
            additional_accounts=[
                deterministic_sender_with_tokens.balance_account_address,
                deterministic_session_user.balance_account_address,
                deterministic_session_user.solana_account_address,
            ],
            compute_unit_price=5000,
        )

        allure_attach_accounts_data(resp=resp, evm_loader=evm_loader)

        cu_consumed = resp.value.transaction.meta.compute_units_consumed
        assert cu_consumed == 82359

    @pytest.mark.deterministic_index_of_process(19)  # must be greater than max number of --numprocesses
    @pytest.mark.deterministic_session_user_index(1)
    @pytest.mark.deterministic_holder_acc_seed(1)
    @pytest.mark.skip(reason="Used compute units are unstable")
    def test_iterative_with_many_accounts(
        self,
        deterministic_session_user: Caller,
        evm_loader: EvmLoader,
        deterministic_operator_keypair: Keypair,
        deterministic_treasury_pool: TreasuryPool,
        deterministic_holder_acc: Pubkey,
        neon_api_client: NeonApiClient,
    ):
        rw_lock = evm_loader.deploy_contract(
            deterministic_operator_keypair,
            deterministic_session_user,
            "rw_lock",
            neon_api_client,
            deterministic_treasury_pool,
        )

        constructor_args = eth_abi.encode(["address"], [rw_lock.eth_address.hex()])
        rw_lock_caller_contract = evm_loader.deploy_contract(
            deterministic_operator_keypair,
            deterministic_session_user,
            "rw_lock",
            neon_api_client,
            deterministic_treasury_pool,
            encoded_args=constructor_args,
            contract_name="rw_lock_caller",
        )

        signed_eth_tx = make_contract_call_trx(
            evm_loader, deterministic_session_user, rw_lock_caller_contract, "update_storage_map(uint256)", [15]
        )

        func_name = abi.function_signature_to_4byte_selector("update_storage_map(uint256)")
        data = func_name + eth_abi.encode(["uint256"], [15])
        result = neon_api_client.emulate(
            deterministic_session_user.eth_address.hex(), rw_lock_caller_contract.eth_address.hex(), data
        )
        additional_accounts = [
            deterministic_session_user.solana_account_address,
            deterministic_session_user.balance_account_address,
            rw_lock.solana_address,
            rw_lock_caller_contract.solana_address,
        ]

        for acc in result["solana_accounts"]:
            pk = Pubkey.from_string(acc["pubkey"])
            additional_accounts.append(pk)

        planned_accs = sorted(
            list(
                set(
                    [
                        "11111111111111111111111111111111",
                        "ComputeBudget111111111111111111111111111111",
                        "53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io",
                        "DwGmF9kH1sabX2bTrZWmofKK3gCfaVSeJgbB5JzGMLyx",
                    ]
                    + [
                        str(pk)
                        for pk in additional_accounts
                        + [
                            deterministic_operator_keypair.pubkey(),
                            deterministic_treasury_pool.account,
                            deterministic_holder_acc,
                        ]
                    ]
                )
            )
        )

        # # operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(deterministic_operator_keypair)
        # done = False
        # simulated_compute_units = 0
        #
        # while not done:
        #     sol_tx = instructions.TransactionWithComputeBudget(deterministic_operator_keypair)
        #     operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(deterministic_operator_keypair)
        #     sol_tx.add(
        #         instructions.make_ExecuteTrxFromInstruction(
        #             operator=deterministic_operator_keypair,
        #             operator_balance=operator_balance_pubkey,
        #             holder_address=deterministic_holder_acc,
        #             evm_loader_id=evm_loader.loader_id,
        #             treasury_address=deterministic_treasury_pool.account,
        #             treasury_buffer=deterministic_treasury_pool.buffer,
        #             message=signed_eth_tx.raw_transaction,
        #             additional_accounts=additional_accounts,
        #         )
        #     )
        #     sol_tx.sign(deterministic_operator_keypair)
        #
        #     blockhash = base58.b58decode(str(evm_loader.get_latest_blockhash(Finalized).value.blockhash)).hex()
        #     simulate_response = neon_api_client.simulate_solana(
        #         blockhash=blockhash,
        #         transactions=[sol_tx.serialize().hex()],
        #         verify_signature=False,
        #     )
        #     simulated_transactions = simulate_response.json()["value"]["transactions"]
        #
        #     for simulated_transaction in simulated_transactions:
        #         if simulated_transaction["error"]:
        #             raise AssertionError(f"Error in sol trx: {simulated_transaction}")
        #
        #         for log in simulated_transaction["logs"]:
        #             if "ExitError" in log:
        #                 raise AssertionError(f"EVM Return error in logs: {simulated_transaction}")
        #
        #             elif "exit_status" in log:
        #                 done = True
        #                 break
        #
        #     simulated_compute_units += sum(
        #         [simulate_result["executed_units"] for simulate_result in simulated_transactions]
        #     )
        #
        # assert simulated_compute_units == 333506  # unstable

        # -------------------
        resp = evm_loader.execute_transaction_steps_from_instruction(
            operator=deterministic_operator_keypair,
            treasury=deterministic_treasury_pool,
            storage_account=deterministic_holder_acc,
            instruction=signed_eth_tx,
            additional_accounts=additional_accounts,
        )

        allure_attach_accounts_data(resp=resp, evm_loader=evm_loader)

        used_accs = sorted([str(pk) for pk in resp.value.transaction.transaction.message.account_keys])
        assert used_accs == planned_accs

        cu_consumed = resp.value.transaction.meta.compute_units_consumed
        assert abs(cu_consumed - 218000) < 10_000

    @pytest.mark.deterministic_index_of_process(20)  # must be greater than max number of --numprocesses
    @pytest.mark.deterministic_session_user_index(2)
    @pytest.mark.deterministic_holder_acc_seed(2)
    @pytest.mark.skip(reason="Used compute units are unstable")
    def test_iterative_with_math(
        self,
        deterministic_session_user: Caller,
        evm_loader: EvmLoader,
        deterministic_operator_keypair: Keypair,
        deterministic_treasury_pool: TreasuryPool,
        deterministic_holder_acc: Pubkey,
        neon_api_client: NeonApiClient,
    ):
        counter = evm_loader.deploy_contract(
            operator=deterministic_operator_keypair,
            user=deterministic_session_user,
            contract_file_name="common/Counter",
            neon_api_client=neon_api_client,
            treasury_pool=deterministic_treasury_pool,
            version="0.8.10",
        )
        signed_tx = make_contract_call_trx(
            evm_loader=evm_loader,
            user=deterministic_session_user,
            contract=counter,
            function_signature="moreInstructionWithLogs(uint256,uint256)",
            params=[0, 10],
        )

        func_name = abi.function_signature_to_4byte_selector("moreInstructionWithLogs(uint256,uint256)")
        data = func_name + eth_abi.encode(["uint256", "uint256"], [0, 10])

        result = neon_api_client.emulate(deterministic_session_user.eth_address.hex(), counter.eth_address.hex(), data)

        additional_accounts = [
            deterministic_session_user.solana_account_address,
            deterministic_session_user.balance_account_address,
            counter.solana_address,
        ]

        for acc in result["solana_accounts"]:
            pk = Pubkey.from_string(acc["pubkey"])
            additional_accounts.append(pk)

        resp = evm_loader.execute_transaction_steps_from_instruction(
            deterministic_operator_keypair,
            deterministic_treasury_pool,
            deterministic_holder_acc,
            signed_tx,
            additional_accounts,
        )

        allure_attach_accounts_data(resp=resp, evm_loader=evm_loader)

        cu_consumed = resp.value.transaction.meta.compute_units_consumed
        assert cu_consumed == 32505

    @pytest.mark.deterministic_index_of_process(21)  # must be greater than max number of --numprocesses
    @pytest.mark.deterministic_session_user_index(3)
    @pytest.mark.deterministic_holder_acc_seed(3)
    @pytest.mark.skip(reason="Used compute units are unstable")
    def test_nested_calls(
        self,
        deterministic_session_user: Caller,
        evm_loader: EvmLoader,
        deterministic_operator_keypair: Keypair,
        deterministic_treasury_pool: TreasuryPool,
        deterministic_holder_acc: Pubkey,
        neon_api_client: NeonApiClient,
    ):
        contract_a = evm_loader.deploy_contract(
            contract_file_name="common/NestedCallsChecker",
            contract_name="A",
            version="0.8.12",
            operator=deterministic_operator_keypair,
            user=deterministic_session_user,
            neon_api_client=neon_api_client,
            treasury_pool=deterministic_treasury_pool,
        )
        contract_b = evm_loader.deploy_contract(
            contract_file_name="common/NestedCallsChecker",
            contract_name="B",
            version="0.8.12",
            operator=deterministic_operator_keypair,
            user=deterministic_session_user,
            neon_api_client=neon_api_client,
            treasury_pool=deterministic_treasury_pool,
        )
        contract_c = evm_loader.deploy_contract(
            contract_file_name="common/NestedCallsChecker",
            contract_name="C",
            version="0.8.12",
            operator=deterministic_operator_keypair,
            user=deterministic_session_user,
            neon_api_client=neon_api_client,
            treasury_pool=deterministic_treasury_pool,
        )

        contract_b_checksum_address = to_checksum_address("0x" + contract_b.eth_address.hex())
        contract_c_checksum_address = to_checksum_address("0x" + contract_c.eth_address.hex())

        signed_tx = make_contract_call_trx(
            evm_loader=evm_loader,
            user=deterministic_session_user,
            contract=contract_a,
            function_signature="method1(address,address)",
            params=[
                contract_b_checksum_address,
                contract_c_checksum_address,
            ],
        )

        func_name = abi.function_signature_to_4byte_selector("method1(address,address)")
        data = func_name + eth_abi.encode(
            types=["address", "address"],
            args=[contract_b_checksum_address, contract_c_checksum_address],
        )

        emulate_result = neon_api_client.emulate(
            deterministic_session_user.eth_address.hex(), contract_a.eth_address.hex(), data
        )

        additional_accounts = [
            deterministic_session_user.solana_account_address,
            deterministic_session_user.balance_account_address,
            contract_a.solana_address,
            contract_b.solana_address,
            contract_c.solana_address,
        ]

        for acc in emulate_result["solana_accounts"]:
            pk = Pubkey.from_string(acc["pubkey"])
            additional_accounts.append(pk)

        resp = evm_loader.execute_transaction_steps_from_instruction(
            deterministic_operator_keypair,
            deterministic_treasury_pool,
            deterministic_holder_acc,
            signed_tx,
            additional_accounts,
        )

        allure_attach_accounts_data(resp=resp, evm_loader=evm_loader)

        cu_consumed = resp.value.transaction.meta.compute_units_consumed
        assert cu_consumed == 35788

    @pytest.mark.deterministic_index_of_process(22)  # must be greater than max number of --numprocesses
    @pytest.mark.deterministic_session_user_index(4)
    @pytest.mark.deterministic_holder_acc_seed(4)
    @pytest.mark.skip(reason="Used compute units are unstable")
    def test_precompiled(
        self,
        deterministic_session_user: Caller,
        evm_loader: EvmLoader,
        deterministic_operator_keypair: Keypair,
        deterministic_treasury_pool: TreasuryPool,
        deterministic_holder_acc: Pubkey,
        neon_api_client: NeonApiClient,
    ):
        qac_contract = evm_loader.deploy_contract(
            operator=deterministic_operator_keypair,
            user=deterministic_session_user,
            contract_file_name="precompiled/QueryAccountCaller.sol",
            neon_api_client=neon_api_client,
            treasury_pool=deterministic_treasury_pool,
            contract_name="QueryAccountCaller",
            version="0.8.10",
        )
        solana_account_address_uint256 = int.from_bytes(
            deterministic_session_user.solana_account_address, byteorder="big"
        )

        signed_tx = make_contract_call_trx(
            evm_loader=evm_loader,
            user=deterministic_session_user,
            contract=qac_contract,
            function_signature="queryOwner(uint256)",
            params=[solana_account_address_uint256],
        )

        func_name = abi.function_signature_to_4byte_selector("method1(address,address)")
        data = func_name + eth_abi.encode(
            types=["uint256"],
            args=[solana_account_address_uint256],
        )

        emulate_result = neon_api_client.emulate(
            deterministic_session_user.eth_address.hex(), qac_contract.eth_address.hex(), data
        )

        additional_accounts = [
            deterministic_session_user.solana_account_address,
            deterministic_session_user.balance_account_address,
            qac_contract.solana_address,
        ]

        for acc in emulate_result["solana_accounts"]:
            pk = Pubkey.from_string(acc["pubkey"])
            additional_accounts.append(pk)

        resp = evm_loader.execute_transaction_steps_from_instruction(
            deterministic_operator_keypair,
            deterministic_treasury_pool,
            deterministic_holder_acc,
            signed_tx,
            additional_accounts,
        )

        allure_attach_accounts_data(resp=resp, evm_loader=evm_loader)

        cu_consumed = resp.value.transaction.meta.compute_units_consumed
        assert cu_consumed == 40842

    @pytest.mark.deterministic_index_of_process(23)  # must be greater than max number of --numprocesses
    @pytest.mark.deterministic_sender_with_tokens_index(5)
    @pytest.mark.deterministic_holder_acc_seed(5)
    def test_scheduled_transaction(
        self,
        deterministic_sender_with_tokens: Caller,
        evm_loader: EvmLoader,
        deterministic_operator_keypair: Keypair,
        deterministic_treasury_pool: TreasuryPool,
        deterministic_holder_acc: Pubkey,
        neon_api_client: NeonApiClient,
        neon_user: NeonUser,
    ):
        deterministic_neon_user = NeonUser(
            evm_loader_id=str(evm_loader.loader_id),
            keypair=deterministic_sender_with_tokens.solana_account,
        )

        basic_contract = evm_loader.deploy_contract(
            operator=deterministic_operator_keypair,
            user=deterministic_sender_with_tokens,
            contract_file_name="common/Common",
            neon_api_client=neon_api_client,
            treasury_pool=deterministic_treasury_pool,
            version="0.8.12",
        )

        nonce = evm_loader.get_neon_nonce(deterministic_neon_user.neon_address, evm_loader.sol_chain_id)
        contract_data = 18
        func_name = abi.function_signature_to_4byte_selector("setNumber(uint256)")
        data = func_name + eth_abi.encode(
            types=["uint256"],
            args=[contract_data],
        )
        tx = ScheduledTransaction(
            payer=deterministic_neon_user.neon_address,
            sender=None,
            nonce=nonce,
            index=0,
            target=basic_contract.eth_address,
            value=0,
            call_data=data,
            chain_id=evm_loader.sol_chain_id,
        )
        tree_account = evm_loader.create_tree_account(deterministic_neon_user, deterministic_treasury_pool, tx.encode())
        transaction_tree_data = neon_api_client.get_transaction_tree(deterministic_neon_user.neon_address.hex(), nonce)
        assert transaction_tree_data.get_transaction_count() == 1

        evm_loader.write_transaction_to_holder_account(
            tx.encode(), deterministic_holder_acc, deterministic_operator_keypair
        )
        additional_accounts = [
            basic_contract.solana_address,
            deterministic_neon_user.get_balance_account(evm_loader.sol_chain_id),
        ]
        resp = evm_loader.execute_scheduled_trx_from_account(
            0,
            deterministic_operator_keypair,
            deterministic_holder_acc,
            tree_account,
            deterministic_treasury_pool,
            additional_accounts,
            compute_unit_price=3929,
        )

        allure_attach_accounts_data(resp=resp, evm_loader=evm_loader)

        cu_consumed = resp.value.transaction.meta.compute_units_consumed
        assert cu_consumed == 29284
