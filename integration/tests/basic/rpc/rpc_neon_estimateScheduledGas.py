import allure
import pytest
import eth_abi
import requests

from eth_utils import abi
import solders.system_program as sp
from integration.tests.basic.helpers.errors import Error32602

from integration.tests.basic.helpers.rpc_checks import assert_fields_are_hex

from utils.scheduled_trx import ScheduledTrxEstimateRequest


@allure.feature("JSON-RPC validation")
@allure.story("Verify JSON-RPC NeonRPCEstimateScheduledGas work")
@pytest.mark.usefixtures("accounts", "web3_client")
@pytest.mark.neon_only
class TestNeonRPCEstimateScheduledGas:
    def test_send_one_transaction(self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool):
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        resp = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        assert (
            len(resp["gasList"]) == 1
        ), f'Amount of transactions must be 1, but actual amount = {len(resp["gasList"])}'
        assert resp["nonce"] == "0x0"

        assert resp["maxFeePerGas"] > resp["maxPriorityFeePerGas"], (
            f"maxFeePerGas must be greater than maxPriorityFeePerGas, "
            f'but maxFeePerGas = {resp["maxFeePerGas"]} and maxPriorityFeePerGas = {resp["maxPriorityFeePerGas"]}'
        )

        assert_fields_are_hex(resp, ["chainId", "maxFeePerGas", "maxPriorityFeePerGas", "nonce", "treasuryIndex"])

        chain_id = 0x70
        assert resp["chainId"] == hex(chain_id), f'ChainID must be {chain_id}, but actual = {resp["chainId"]}'

        assert (
            len(resp["accountList"]) == 6
        ), f'Amount of accounts must be 6, but actual amount = {len(resp["accountList"])}'
        balance_account = neon_user.get_balance_account(chain_id).__str__()
        treasury_index = int(resp["treasuryIndex"], 16)
        treasury_address = evm_loader.create_treasury_pool_address(treasury_index).__str__()
        assert resp["accountList"][0] == neon_user.solana_account.pubkey().__str__()
        assert resp["accountList"][1] == balance_account
        assert resp["accountList"][2] == treasury_address
        assert resp["accountList"][5] == sp.ID.__str__()

        # как проверить адреса tree_account и pool
        # pool = get_associated_token_address(evm_loader.create_get_authority_address(), wSOL["address_spl"])
        # print(pool)

    def test_send_multiple_transactions(self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool):
        contract_data = 18
        transaction_rate = 4

        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        trx_estimate_obj_list = []
        for i in range(transaction_rate):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
            )

        resp = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)
        assert (
            len(resp["gasList"]) == transaction_rate
        ), f'Amount of transactions must be 1, but actual amount = {len(resp["gasList"])}'
        assert resp["nonce"] == "0x0"

        assert resp["maxFeePerGas"] > resp["maxPriorityFeePerGas"], (
            f"maxFeePerGas must be greater than maxPriorityFeePerGas, "
            f'but maxFeePerGas = {resp["maxFeePerGas"]} and maxPriorityFeePerGas = {resp["maxPriorityFeePerGas"]}'
        )

        assert_fields_are_hex(resp, ["chainId", "maxFeePerGas", "maxPriorityFeePerGas", "nonce", "treasuryIndex"])

        chain_id = 0x70
        assert resp["chainId"] == hex(chain_id), f'ChainID must be {chain_id}, but actual = {resp["chainId"]}'

        assert (
            len(resp["accountList"]) == 6
        ), f'Amount of accounts must be 6, but actual amount = {len(resp["accountList"])}'
        balance_account = neon_user.get_balance_account(chain_id).__str__()
        treasury_index = int(resp["treasuryIndex"], 16)
        treasury_address = evm_loader.create_treasury_pool_address(treasury_index).__str__()
        assert resp["accountList"][0] == neon_user.solana_account.pubkey().__str__()
        assert resp["accountList"][1] == balance_account
        assert resp["accountList"][2] == treasury_address
        assert resp["accountList"][5] == sp.ID.__str__()

    def test_one_of_multiply_transactions_wrong(
        self,
        web3_client_sol,
        neon_user,
        treasury_pool,
        revert_contract_caller,
        event_caller_contract,
        common_contract,
        evm_loader,
    ):
        contract_data = 18
        transaction_rate = 3

        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        trx_estimate_obj_list = []
        for i in range(transaction_rate):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
            )

        data_fail_tx = abi.function_signature_to_4byte_selector("doAssert()")
        trx_estimate_obj_list.append(
            ScheduledTrxEstimateRequest(
                neon_user.checksum_address, revert_contract_caller.address, data_fail_tx, value=100000000
            )
        )

        resp = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), trx_estimate_obj_list, check_result=False
        )

        assert "error" in resp, "error field not in response"
        assert "code" in resp["error"]
        assert resp["error"]["code"] == 3
        assert "message" in resp["error"], "message field not in response"
        assert "execution reverted" in resp["error"]["message"], "message 'execution reverted' not in response"

    def test_no_transactions_in_request(self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool):
        resp = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [], check_result=False)

        assert "error" in resp, "error field not in response"
        assert "code" in resp["error"]
        assert "message" in resp["error"], "message field not in response"
        assert Error32602.CODE == resp["error"]["code"]
        assert Error32602.INVALID_TRANSACTIONID == resp["error"]["message"]

    def test_wrong_chain_id(self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool):
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)

        transactions = []
        for trx in [trx_estimate_obj]:
            trx = {
                "fromAddress": trx.from_address,
                "toAddress": trx.to_address,
                "data": trx.data.hex(),
                "value": trx.value,
            }
            transactions.append(trx)
        params = {"scheduledSolanaPayer": str(neon_user.solana_account.pubkey()), "transactions": transactions}
        json = {
            "jsonrpc": "2.0",
            "method": "neon_estimateScheduledGas",
            "params": [params],
            "id": 0,
        }
        resp = requests.post(
            "http://127.0.0.1:9090/solana/",
            json=json,
        ).json()

        assert "error" in resp, "error field not in response"
        assert "code" in resp["error"]
        assert resp["error"]["code"] == -32000
        assert "message" in resp["error"], "message field not in response"
        assert "wrong chain id" in resp["error"]["message"], "message 'wrong chain id' not in response"

    def test_send_value_greater_than_balance(
        self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool
    ):
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data, 10000)
        resp = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), [trx_estimate_obj], check_result=False
        )

        assert "error" in resp, "error field not in response"
        assert "code" in resp["error"]
        assert resp["error"]["code"] == 3

        assert "message" in resp["error"], "message field not in response"
        assert "execution reverted" in resp["error"]["message"], "message 'execution reverted' not in response"

    def test_sender_has_no_sols(self, web3_client_sol, common_contract, evm_loader, treasury_pool, neon_user_no_sols):

        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        trx_estimate_obj = ScheduledTrxEstimateRequest(
            neon_user_no_sols.checksum_address, common_contract.address, data
        )
        resp = web3_client_sol.estimate_scheduled(neon_user_no_sols.solana_account.pubkey(), [trx_estimate_obj])

        assert (
            len(resp["gasList"]) == 1
        ), f'Amount of transactions must be 1, but actual amount = {len(resp["gasList"])}'
        assert resp["nonce"] == "0x0"

        assert resp["maxFeePerGas"] > resp["maxPriorityFeePerGas"], (
            f"maxFeePerGas must be greater than maxPriorityFeePerGas, "
            f'but maxFeePerGas = {resp["maxFeePerGas"]} and maxPriorityFeePerGas = {resp["maxPriorityFeePerGas"]}'
        )

        assert_fields_are_hex(resp, ["chainId", "maxFeePerGas", "maxPriorityFeePerGas", "nonce", "treasuryIndex"])

        chain_id = 0x70
        assert resp["chainId"] == hex(chain_id), f'ChainID must be {chain_id}, but actual = {resp["chainId"]}'

        assert (
            len(resp["accountList"]) == 6
        ), f'Amount of accounts must be 6, but actual amount = {len(resp["accountList"])}'
        balance_account = neon_user_no_sols.get_balance_account(chain_id).__str__()
        treasury_index = int(resp["treasuryIndex"], 16)
        treasury_address = evm_loader.create_treasury_pool_address(treasury_index).__str__()
        assert resp["accountList"][0] == neon_user_no_sols.solana_account.pubkey().__str__()
        assert resp["accountList"][1] == balance_account
        assert resp["accountList"][2] == treasury_address
        assert resp["accountList"][5] == sp.ID.__str__()

    def test_no_function_in_called_contract(
        self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool
    ):
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("settNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        resp = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), [trx_estimate_obj], check_result=False
        )

        assert "error" in resp, "error field not in response"
        assert "code" in resp["error"]
        assert resp["error"]["code"] == 3
        assert "message" in resp["error"], "message field not in response"
        assert "execution reverted" in resp["error"]["message"], "message 'execution reverted' not in response"
