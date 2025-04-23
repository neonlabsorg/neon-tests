import logging
import random

import allure
import pytest
from deepdiff import DeepDiff

from integration.tests.tracer.tracer_helper import (
    validate_response_result,
    check_call_tracer_type,
    check_struct_log_type,
)
from utils.accounts import EthAccounts
from utils.helpers import padhex
from utils.tracer_client import TracerClient
from utils.web3client import NeonChainWeb3Client


@allure.story("Tracer API RPC trace simple transactions")
@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api")
class TestDebugTraceIterativeTransaction:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    tracer_api: TracerClient

    def fill_expected_response(
        self,
        instruction_tx,
        receipt,
        type="CALL",
        logs=False,
        calls=True,
        revert=False,
        revert_reason=None,
        error=None,
        calls_value="0x1",
        calls_type="CALL",
        calls_logs_append=False,
    ):
        expected_response = {}

        address_to = instruction_tx["to"].lower()
        expected_response["from"] = instruction_tx["from"].lower()
        expected_response["to"] = address_to
        expected_response["gasUsed"] = hex(receipt["gasUsed"])
        expected_response["input"] = instruction_tx["data"]
        expected_response["type"] = type

        # gasUsed, gas are 0x0 because NeonEVM has different(from goEth) gas calculation logic
        if calls:
            expected_response["calls"] = []
            expected_response["calls"].append(
                {
                    "from": address_to,
                    "gasUsed": "0x0",
                    "gas": "0x0",
                    "type": calls_type,
                    "value": calls_value,
                }
            )

            if calls_type == "DELEGATECALL":
                expected_response["calls"][0]["from"] = instruction_tx["to"].lower()

            if calls_logs_append:
                for log in receipt["logs"]:
                    if log["logIndex"] == 1:
                        expected_response["calls"].append(
                            {
                                "from": address_to,
                                "gasUsed": "0x0",
                                "gas": "0x0",
                                "type": "CALL",
                                "value": calls_value,
                                "logs": [
                                    {
                                        "topics": ["0x" + log["topics"][0].hex()],
                                        "data": "0x" + log["data"].hex(),
                                    }
                                ],
                            }
                        )

        if logs:
            for log in receipt["logs"]:
                if log["logIndex"] == 0:
                    expected_response["logs"] = [
                        {
                            "address": address_to,
                            "topics": ["0x" + log["topics"][0].hex()],
                            "data": "0x" + log["data"].hex(),
                        }
                    ]

        if revert:
            if error:
                expected_response["calls"][0]["error"] = revert_reason
            else:
                expected_response["calls"][0]["error"] = "execution reverted"
                expected_response["calls"][0]["revertReason"] = revert_reason

        return expected_response

    @allure.step("Check tracer response matches expected response")
    def assert_response_contains_expected(self, pytestconfig, expected_response, response, sort_calls=False):
        if sort_calls:
            expected_response["calls"] = sorted(expected_response["calls"], key=lambda d: d["type"])
            response["result"]["calls"] = sorted(response["result"]["calls"], key=lambda d: d["type"])

        if pytestconfig.getoption("--network") == "geth":
            # we do not fill whole response, that is why we skip some of fields
            # we can build compare function for each field in the future if it needed
            exclude_list = ["root['gas']", "root['output']", "root['value']"]
            if "calls" in expected_response:
                for i in range(len(expected_response["calls"])):
                    exclude_list.append(f"root['calls'][{i}]['to']")
                    exclude_list.append(f"root['calls'][{i}]['gas']")
                    exclude_list.append(f"root['calls'][{i}]['gasUsed']")
                    exclude_list.append(f"root['calls'][{i}]['input']")
                    exclude_list.append(f"root['calls'][{i}]['output']")
                    exclude_list.append(f"root['calls'][{i}]['value']")
                    exclude_list.append(f"root['calls'][{i}]['logs'][0]['address']")
                    exclude_list.append(f"root['calls'][{i}]['logs'][0]['position']")
        else:
            exclude_list = []
        logging.debug(f"Expected response: {expected_response}")
        logging.debug(f"Response: {response['result']}")
        diff = DeepDiff(expected_response, response["result"], exclude_paths=exclude_list)
        # check if expected_response is subset of response
        assert "dictionary_item_removed" not in diff
        # check if expected_response and response match in identical keys
        assert "values_changed" not in diff

    def test_debug_trace_transaction(self, send_neon_tx_receipt, tracer_api):
        tx_hash = send_neon_tx_receipt["transactionHash"].hex()
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", [tx_hash])
        assert "error" not in response, "Error in response"
        validate_response_result(response)

    def test_debug_trace_transaction_non_zero_trace(self, call_storage_tx_receipt):

        call_storage_tx_receipt, store_value = call_storage_tx_receipt
        tx_hash = call_storage_tx_receipt["transactionHash"].hex()
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", [tx_hash])

        assert "error" not in response, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(store_value), 64)[2:]
        validate_response_result(response)

    # GETH: NDEV-3251
    def test_debug_trace_transaction_hash_without_prefix(self, call_storage_tx_receipt):

        call_storage_tx_receipt, store_value = call_storage_tx_receipt
        tx_hash = call_storage_tx_receipt["transactionHash"].hex()

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", [tx_hash])

        assert "error" not in response, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(store_value), 64)[2:]
        validate_response_result(response)

    @pytest.mark.parametrize("tx_hash", [6, "0x0", "", "f23e554"])
    # GETH: NDEV-3250
    def test_debug_trace_transaction_invalid_hash(self, tx_hash):

        response = self.tracer_api.debug_trace_transaction(tx_hash)
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

    def test_debug_get_raw_transaction(self, send_raw_transaction_receipt):
        signed_tx, receipt = send_raw_transaction_receipt
        response = self.tracer_api.send_rpc_and_wait_response(
            "debug_getRawTransaction", [receipt["transactionHash"].hex()]
        )
        assert "error" not in response, "Error in response"
        assert "result" in response and response["result"] == "0x" + signed_tx.raw_transaction.hex()

    # GETH: NDEV-3252
    def test_debug_get_raw_transaction_invalid_tx_hash(self, send_neon_tx_receipt):
        receipt = send_neon_tx_receipt
        response = self.tracer_api.send_rpc(method="debug_getRawTransaction", params=[receipt["blockHash"].hex()])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32603, "Invalid error code"

        blockhash = "".join(["0x", receipt["blockHash"].hex()])
        assert response["error"]["message"] == f"Empty Neon transaction receipt for {blockhash}"

    # GETH: NDEV-3252
    def test_debug_get_raw_transaction_non_existent_tx_hash(self):
        block_hash = "0xd9765b77e470204ae5edb1a796ab92ecb0e20fea50aeb09275aea740af7bbc69"
        response = self.tracer_api.debug_get_raw_transaction(block_hash)
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32603, "Invalid error code"
        assert (
            response["error"]["message"]
            == "Empty Neon transaction receipt for 0xd9765b77e470204ae5edb1a796ab92ecb0e20fea50aeb09275aea740af7bbc69"
        )

    def test_trace_transaction_from_precompiled_contract(self, transaction_receipt_from_precompiled_contract):
        tx_hash = transaction_receipt_from_precompiled_contract["transactionHash"].hex()
        tx_data = self.web3_client.get_transaction_by_hash(tx_hash)
        check_call_tracer_type(self.tracer_api, tx_data)
        check_struct_log_type(self.tracer_api, tx_data, check_struct_logs=False)

    def test_callTracer_call_contract_from_contract_type_static_call(self, pytestconfig, static_call_tx_receipt):

        tx, instruction_tx, receipt = static_call_tx_receipt
        response = self.tracer_api.debug_trace_transaction(receipt["transactionHash"].hex(), wait_response=120)
        expected_response = self.fill_expected_response(
            instruction_tx, receipt, calls_value="0x0", calls_type="STATICCALL"
        )
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    def test_callTracer_call_contract_from_contract_type_static_call_with_events(
        self, pytestconfig, static_call_tx_with_events_receipt
    ):
        tx, instruction_tx, receipt = static_call_tx_with_events_receipt
        response = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), with_log=True, wait_response=120
        )
        expected_response = self.fill_expected_response(
            instruction_tx, receipt, logs=True, calls_value="0x0", calls_type="STATICCALL", calls_logs_append=True
        )
        self.assert_response_contains_expected(pytestconfig, expected_response, response, sort_calls=True)

    def test_callTracer_call_contract_from_contract_type_call_with_events(self, pytestconfig, call_tx_with_receipt):
        tx, instruction_tx, receipt = call_tx_with_receipt
        response = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), with_log=True, wait_response=120
        )
        expected_response = self.fill_expected_response(
            instruction_tx, receipt, logs=True, calls_value="0x0", calls_logs_append=True
        )
        self.assert_response_contains_expected(pytestconfig, expected_response, response, sort_calls=True)

    def test_callTracer_call_contract_from_contract_type_call(self, pytestconfig, call_tx_receipt):
        tx, instruction_tx, receipt = call_tx_receipt
        response = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), with_log=True, wait_response=120
        )
        expected_response = self.fill_expected_response(instruction_tx, receipt, calls_value="0x0")
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    @pytest.mark.skip(reason="SLA-119")
    def test_callTracer_call_contract_from_contract_type_delegate_call(self, pytestconfig, delegate_call_tx_receipt):
        tx, instruction_tx, receipt = delegate_call_tx_receipt
        response = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), with_log=False, wait_response=120
        )
        expected_response = self.fill_expected_response(
            instruction_tx, receipt, calls_value="0x0", calls_type="DELEGATECALL"
        )
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    def test_callTracer_call_contract_from_contract_type_callcode(self, pytestconfig, callcode_tx_receipt):
        tx, instruction_tx, receipt = callcode_tx_receipt
        response = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), with_log=True, wait_response=120
        )
        expected_response = self.fill_expected_response(
            instruction_tx, receipt, calls_value="0x0", calls_type="CALLCODE"
        )
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    def test_callTracer_call_contract_with_zero_division(self, pytestconfig, tx_with_zero_division_receipt):
        tx, instruction_tx, receipt = tx_with_zero_division_receipt
        response = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), with_log=True, wait_response=120
        )
        expected_response = self.fill_expected_response(
            instruction_tx, receipt, revert=True, revert_reason="division or modulo by zero", calls_value="0x0"
        )

        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    def test_callTracer_call_contract_from_other_contract_revert_with_assert(
        self, pytestconfig, tx_revert_with_assert_receipt
    ):

        tx, instruction_tx, receipt = tx_revert_with_assert_receipt
        response = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), with_log=True, wait_response=120
        )
        expected_response = self.fill_expected_response(
            instruction_tx, receipt, logs=True, revert=True, revert_reason="assert(false)", calls_value="0x0"
        )

        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    def test_callTracer_call_contract_from_other_contract_trivial_revert(
        self, pytestconfig, tx_with_trivial_revert_receipt
    ):
        tx, instruction_tx, receipt = tx_with_trivial_revert_receipt
        response = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), with_log=True, wait_response=120
        )
        expected_response = self.fill_expected_response(
            instruction_tx, receipt, logs=True, revert=True, revert_reason="Revert Contract", calls_value="0x0"
        )
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    @pytest.mark.skip(reason="NDEV-3260")
    def test_callTracer_call_contract_from_other_contract_revert(
        self,
        pytestconfig,
        tx_with_revert_in_called_contract,
    ):
        tx, instruction_tx, receipt = tx_with_revert_in_called_contract
        response = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), with_log=True, wait_response=120
        )

        address_to = instruction_tx["to"].lower()
        if pytestconfig.getoption("--network") == "geth":
            reason = "insufficient balance for transfer"
        else:
            reason = f"Insufficient balance for transfer, account = {address_to}, chain = {self.web3_client.eth.chain_id}, required = 1"
        expected_response = self.fill_expected_response(instruction_tx, receipt, logs=True, revert=True, error=reason)
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    def test_callTracer_call_contract_from_other_contract_revert_with_require(
        self,
        pytestconfig,
        tx_call_contract_revert_with_require_receipt,
        events_checker_contract,
        event_checker_callee_address,
    ):

        tx, instruction_tx, receipt = tx_call_contract_revert_with_require_receipt
        response = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), with_log=True, wait_response=120
        )
        expected_response = self.fill_expected_response(
            instruction_tx, receipt, logs=True, revert=True, revert_reason="require False", calls_value="0x0"
        )
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    def test_callTracer_call_to_precompiled_contract(
        self, pytestconfig, eip1052_checker, tx_call_to_precompiled_contract
    ):
        tx, instruction_tx, receipt = tx_call_to_precompiled_contract
        response = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), with_log=False, wait_response=120
        )

        expected_response = self.fill_expected_response(instruction_tx, receipt, calls=False)
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    @pytest.mark.skip(reason="NDEV-2934")
    def test_callTracer_without_tracerConfig(self, pytestconfig, storage_object):
        sender_account = self.accounts[0]
        store_value = random.randint(1, 100)

        tx_obj, _, receipt = storage_object.call_storage(sender_account, store_value, "blockNumber")

        tracer_params = {"tracer": "callTracer"}
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(tx_obj, receipt, calls=False)
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    def test_callTracer_call_contract_with_event_from_other_one_with_two_events(
        self, tx_call_call_contract_with_two_events_receipt
    ):
        tx, instruction_tx, receipt = tx_call_call_contract_with_two_events_receipt
        response = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), with_log=True, wait_response=120
        )

        # check if all topics from receipt logs are in response logs
        log_topics = []
        for log in receipt["logs"]:
            log_topics.append("0x" + log["topics"][0].hex())

        for topic in log_topics:
            assert (
                topic in response["result"]["logs"][0]["topics"]
                or topic in response["result"]["logs"][1]["topics"]
                or topic in response["result"]["calls"][0]["logs"][0]["topics"]
            )

    def test_callTracer_new_contract_and_event_from_constructor(
        self, tx_call_call_contract_with_event_in_constructor_receipt
    ):
        tx, instruction_tx, receipt = tx_call_call_contract_with_event_in_constructor_receipt
        response = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), with_log=True, wait_response=120
        )
        assert len(response["result"]["calls"]) == 1
        assert len(response["result"]["calls"][0]["calls"]) == 1
        assert len(response["result"]["calls"][0]["logs"]) == 1
        assert response["result"]["type"] == "CALL"
        assert response["result"]["calls"][0]["type"] == "CREATE"
        assert response["result"]["calls"][0]["calls"][0]["type"] == "CREATE"
        assert response["result"]["calls"][0]["logs"][0]["topics"][0] == "0x" + receipt["logs"][0]["topics"][0].hex()

    def test_trace_precompiled_neon_contract(self, tx_precompiled_neon_contract_receipt):
        _, _, receipt = tx_precompiled_neon_contract_receipt
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        check_struct_log_type(self.tracer_api, tx_data)
        check_call_tracer_type(self.tracer_api, tx_data)

    def test_trace_trivial_error_tx(self, tx_trivial_error_receipt):

        _, _, receipt = tx_trivial_error_receipt
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        check_call_tracer_type(self.tracer_api, tx_data, wait_error=True, error_message="execution reverted")
        check_struct_log_type(self.tracer_api, tx_data, wait_error=True)
