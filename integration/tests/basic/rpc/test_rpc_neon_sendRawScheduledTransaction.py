import allure
import eth_abi
import pytest
import requests
from eth_utils import abi

from integration.tests.basic.helpers.errors import Error32602, Error32000
from integration.tests.basic.helpers.rpc_checks import is_hex
from utils.helpers import wait_condition

from utils.models.result import EthResult
from utils.consts import wSOL
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData, ScheduledTrxEstimateRequest


@allure.feature("Solana native")
@allure.story("Test sending scheduled transaction")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestScheduledTrx:

    @pytest.fixture(scope="function")
    def tree_account_for_simple_trx(self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool):
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )

        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        tree_account = evm_loader.create_tree_account(
            neon_user, treasury_pool, tx.encode(), wSOL["address_spl"], chain_id=evm_loader.sol_chain_id
        )

        return web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool, tx, tree_account

    def test_send_simple_single_trx(self, tree_account_for_simple_trx):
        web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool, tx, tree_account = (
            tree_account_for_simple_trx
        )
        resp = web3_client_sol.send_scheduled_transaction(tx, check_result=True)
        EthResult(**resp)
        assert is_hex(resp["result"])

    def test_send_reverted_trx(
        self,
        web3_client_sol,
        neon_user,
        treasury_pool,
        event_caller_contract,
        evm_loader,
        common_contract,
        revert_contract_caller,
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        call_data = abi.function_signature_to_4byte_selector("doAssert()")

        gas_limit = 3000000
        base_fee_per_gas = web3_client_sol.base_fee_per_gas()
        max_priority_fee_per_gas = 2500000000
        max_fee_per_gas = base_fee_per_gas * 2 + max_priority_fee_per_gas

        tx0 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=0,
            target=revert_contract_caller.address,
            call_data=call_data,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit,
        )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
        )
        tree_acc_data.add_trx(tx0, 0xFFFF, 0)
        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"])

        resp = web3_client_sol.send_scheduled_transaction(tx0, check_result=True)
        assert is_hex(resp["result"])

    def test_two_transactions_in_params(self, tree_account_for_simple_trx):
        web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool, tx, tree_account = (
            tree_account_for_simple_trx
        )

        url = "http://127.0.0.1:9090/solana/sol"
        resp = requests.post(
            url,
            json={
                "jsonrpc": "2.0",
                "method": "neon_sendRawScheduledTransaction",
                "params": [tx.encode().hex(), tx.encode().hex()],
                "id": 0,
            },
        ).json()

        assert "error" in resp
        assert Error32602.CODE == resp["error"]["code"]
        assert Error32602.INVALID_TRANSACTIONID == resp["error"]["message"]
        assert (
            resp["error"]["data"]["errors"][0] == "Method neon_sendRawScheduledTransaction expect 1 parameters, got 2."
        )  # Todo вынести в константу

    def test_repeat_call_with_same_trx_hash(self, tree_account_for_simple_trx):

        web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool, tx, tree_account = (
            tree_account_for_simple_trx
        )
        web3_client_sol.wait_for_transaction_receipt(tx.hash(), timeout=180)  # wait until first tx finished
        resp = web3_client_sol.send_scheduled_transaction(tx, check_result=False)

        assert "error" in resp
        assert Error32000.CODE == resp["error"]["code"]
        assert Error32000.UNKNOWN_TRANSACTION_HASH == resp["error"]["message"]

    def test_no_tree_account_for_trx(self, tree_account_for_simple_trx):
        web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool, trx, tree_account = (
            tree_account_for_simple_trx
        )
        resp = web3_client_sol.send_scheduled_transaction(trx, check_result=False)

        assert "error" in resp
        assert Error32000.CODE == resp["error"]["code"]
        assert Error32000.UNKNOWN_TRANSACTION_HASH == resp["error"]["message"]

    def test_tree_account_deleted_before_send_trx(self, tree_account_for_simple_trx):
        web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool, trx, tree_account = (
            tree_account_for_simple_trx
        )

        assert evm_loader.account_exists(account_address=tree_account)
        wait_condition(lambda: not evm_loader.account_exists(account_address=tree_account), timeout_sec=120)
        resp = web3_client_sol.send_scheduled_transaction(trx, check_result=False)

        assert "error" in resp
        assert Error32000.CODE == resp["error"]["code"]
        assert Error32000.UNKNOWN_TRANSACTION_HASH == resp["error"]["message"]

    def test_bad_chain_id_url(self, tree_account_for_simple_trx):
        web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool, trx, tree_account = (
            tree_account_for_simple_trx
        )

        wrong_url = "http://127.0.0.1:9090/solana/"
        resp = requests.post(
            wrong_url,
            json={
                "jsonrpc": "2.0",
                "method": "neon_sendRawScheduledTransaction",
                "params": [trx.encode().hex()],
                "id": 0,
            },
        ).json()

        assert "error" in resp
        assert Error32000.CODE == resp["error"]["code"]
        assert Error32000.WRONG_CHAIN_ID == resp["error"]["message"]

    def test_bad_hash_of_trx(self):
        url = "http://127.0.0.1:9090/solana/sol"
        resp = requests.post(
            url,
            json={
                "jsonrpc": "2.0",
                "method": "neon_sendRawScheduledTransaction",
                "params": [""],
                "id": 0,
            },
        ).json()

        assert "error" in resp
        assert Error32602.CODE == resp["error"]["code"]
        assert Error32602.WRONG_TRANSACTION_FOWMAT == resp["error"]["message"]
