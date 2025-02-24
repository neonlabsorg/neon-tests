import allure
import pytest
import eth_abi
import requests
from solders.pubkey import Pubkey

from eth_utils import abi
import solders.system_program as sp
from integration.tests.basic.helpers.errors import Error32602, Error32000, Error3

from integration.tests.basic.helpers.rpc_checks import assert_fields_are_hex

from utils.models.result import EstimateScheduledGas
from utils.scheduled_trx import ScheduledTrxEstimateRequest


CHAIN_ID = 0x70


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
        resp = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), [trx_estimate_obj], check_result=False
        )

        EstimateScheduledGas(**resp)
        result = resp["result"]
        assert (
            len(result["gasList"]) == 1
        ), f'Amount of transactions must be 1, but actual amount = {len(result["gasList"])}'
        assert result["nonce"] == "0x0"

        assert result["maxFeePerGas"] > result["maxPriorityFeePerGas"], (
            f"maxFeePerGas must be greater than maxPriorityFeePerGas, "
            f'but maxFeePerGas = {result["maxFeePerGas"]} and maxPriorityFeePerGas = {result["maxPriorityFeePerGas"]}'
        )

        assert result["chainId"] == hex(0x70), f'ChainID must be {CHAIN_ID}, but actual = {result["chainId"]}'

        assert (
            len(result["accountList"]) == 6
        ), f'Amount of accounts must be 6, but actual amount = {len(result["accountList"])}'

        balance_account = str(neon_user.get_balance_account(CHAIN_ID))
        treasury_index = int(result["treasuryIndex"], 16)
        treasury_address = str(evm_loader.create_treasury_pool_address(treasury_index))

        payer_nonce = evm_loader.get_neon_nonce(neon_user.neon_address, CHAIN_ID).to_bytes(8, "little")
        tree_account = evm_loader.create_tree_account_address(neon_user.neon_address, payer_nonce, CHAIN_ID)
        authority_pool = Pubkey.find_program_address([b"Deposit"], evm_loader.loader_id)[0]

        assert result["accountList"][0] == str(neon_user.solana_account.pubkey())
        assert result["accountList"][1] == balance_account
        assert result["accountList"][2] == treasury_address
        assert result["accountList"][3] == str(tree_account)
        assert result["accountList"][4] == str(authority_pool)
        assert result["accountList"][5] == str(sp.ID)

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
        assert resp["chainId"] == hex(CHAIN_ID), f'ChainID must be {CHAIN_ID}, but actual = {resp["chainId"]}'
        assert (
            len(resp["accountList"]) == 6
        ), f'Amount of accounts must be 6, but actual amount = {len(resp["accountList"])}'

        balance_account = str(neon_user.get_balance_account(CHAIN_ID))
        treasury_index = int(resp["treasuryIndex"], 16)
        treasury_address = str(evm_loader.create_treasury_pool_address(treasury_index))

        payer_nonce = evm_loader.get_neon_nonce(neon_user.neon_address, CHAIN_ID).to_bytes(8, "little")
        tree_account = evm_loader.create_tree_account_address(neon_user.neon_address, payer_nonce, CHAIN_ID)
        authority_pool = Pubkey.find_program_address([b"Deposit"], evm_loader.loader_id)[0]

        assert resp["accountList"][0] == str(neon_user.solana_account.pubkey())
        assert resp["accountList"][1] == balance_account
        assert resp["accountList"][2] == treasury_address
        assert resp["accountList"][3] == str(tree_account)
        assert resp["accountList"][4] == str(authority_pool)
        assert resp["accountList"][5] == str(sp.ID)

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
        assert "message" in resp["error"], "message field not in response"
        assert Error3.CODE == resp["error"]["code"]

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

        assert resp["chainId"] == hex(CHAIN_ID), f'ChainID must be {CHAIN_ID}, but actual = {resp["chainId"]}'

        assert (
            len(resp["accountList"]) == 6
        ), f'Amount of accounts must be 6, but actual amount = {len(resp["accountList"])}'

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
        assert "message" in resp["error"], "message field not in response"
        assert Error3.CODE == resp["error"]["code"] == 3
        assert Error3.EXECUTION_REVERTED == resp["error"]["message"]

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
        assert "message" in resp["error"], "message field not in response"
        assert Error32000.CODE == resp["error"]["code"]
        assert Error32000.WRONG_CHAIN_ID == resp["error"]["message"]

    @pytest.mark.parametrize(
        "field, invalid_value,error_code,error_msg",
        [
            ("fromAddress", "invalid_from_address", Error32602.CODE, Error32602.INVALID_PARAMETERS),
            ("toAddress", "invalid_to_address", Error32602.CODE, Error32602.INVALID_PARAMETERS),
            ("data", "0xdeadbeef", Error3.CODE, Error3.EXECUTION_REVERTED),
            ("value", -100, Error32602.CODE, Error32602.INVALID_PARAMETERS),
        ],
    )
    def test_wrong_format_field(
        self,
        web3_client_sol,
        neon_user,
        common_contract,
        evm_loader,
        treasury_pool,
        field,
        invalid_value,
        error_code,
        error_msg,
    ):
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)

        tx = {
            "fromAddress": trx_estimate_obj.from_address,
            "toAddress": trx_estimate_obj.to_address,
            "data": trx_estimate_obj.data.hex(),
            "value": trx_estimate_obj.value,
            field: invalid_value,
        }

        params = {"scheduledSolanaPayer": str(neon_user.solana_account.pubkey()), "transactions": [tx]}

        json = {
            "jsonrpc": "2.0",
            "method": "neon_estimateScheduledGas",
            "params": [params],
            "id": 0,
        }
        resp = requests.post(
            "http://127.0.0.1:9090/solana/sol",
            json=json,
        ).json()

        assert "error" in resp, "error field not in response"
        assert resp["error"]["code"] == error_code
        assert resp["error"]["message"] == error_msg
