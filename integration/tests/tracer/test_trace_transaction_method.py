import pytest

from utils.tracer_client import TracerClient
from utils.tracer_validator import TracerValidator
from utils.web3client import NeonChainWeb3Client


@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api", "tracer_validator")
class TestTraceTransactionMethod:
    web3_client: NeonChainWeb3Client
    tracer_api: TracerClient
    tracer_validator: TracerValidator

    @staticmethod
    def verify_common_fields(tracer_response, tx_data):
        assert "error" not in tracer_response
        assert tx_data["from"].lower() == tracer_response["result"][0]["action"]["from"].lower()
        assert tx_data["to"].lower() == tracer_response["result"][0]["action"]["to"].lower()
        assert tx_data["hash"].to_0x_hex() == tracer_response["result"][0]["transactionHash"]
        assert tx_data["input"].to_0x_hex() == tracer_response["result"][0]["action"]["input"]
        assert tx_data["gas"] == int(tracer_response["result"][0]["action"]["gas"], 16)

        for i in range(len(tracer_response["result"])):
            assert tx_data["blockHash"].to_0x_hex() == tracer_response["result"][i]["blockHash"]
            assert tx_data["blockNumber"] == tracer_response["result"][i]["blockNumber"]

    @pytest.mark.parametrize(
        "test_case",
        [
            pytest.param(
                {"fixture_name": "static_call_tx_receipt", "expected_call_types": [("call", 1), ("staticcall", 0)]},
                id="static_call",
            ),
            pytest.param(
                {"fixture_name": "delegate_call_tx_receipt", "expected_call_types": [("call", 1), ("delegatecall", 0)]},
                id="delegate_call",
            ),
            pytest.param(
                {"fixture_name": "call_tx_receipt", "expected_call_types": [("call", 1), ("call", 0)]},
                id="call_tx_receipt",
            ),
            pytest.param(
                {"fixture_name": "static_call_tx_receipt", "expected_call_types": [("call", 1), ("staticcall", 0)]},
                id="static_call_with_events_tx_receipt",
            ),
        ],
    )
    def test_call_types(self, test_case, request):
        receipt = request.getfixturevalue(test_case["fixture_name"])
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
        self.verify_common_fields(tracer_response, tx_data)
        for i, (call_type, subtraces) in enumerate(test_case["expected_call_types"]):
            assert tracer_response["result"][i]["action"]["callType"] == call_type
            assert tracer_response["result"][i]["subtraces"] == subtraces

    def test_multiply_scheduled_tx(self, multiply_scheduled_tx_receipts):
        tx_data = self.web3_client.get_transaction_by_hash(multiply_scheduled_tx_receipts["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(multiply_scheduled_tx_receipts["transactionHash"].hex())
        self.verify_common_fields(tracer_response, tx_data)

    @pytest.mark.parametrize(
        "test_case",
        [
            pytest.param(
                {"fixture_name": "scheduled_tx_receipt", "description": "Scheduled transaction"},
                id="scheduled_transaction",
            ),
            pytest.param(
                {"fixture_name": "trivial_revert_tx_receipt", "description": "Trivial revert"}, id="trivial_revert"
            ),
            pytest.param(
                {"fixture_name": "recursion_tx_receipt", "description": "Recursion transaction"}, id="recursion"
            ),
            pytest.param(
                {"fixture_name": "iteration_tx_receipt", "description": "Iterative transaction"}, id="iterative"
            ),
            pytest.param(
                {
                    "fixture_name": "iterative_tx_with_erc20_for_spl_receipt",
                    "description": "Iterative transaction with ERC20 for SPL (51 transactions in chain)",
                },
                id="iterative_erc20_spl",
            ),
            pytest.param(
                {"fixture_name": "precompile_contract_call_tx_receipt", "description": "Precompile contract call"},
                id="precompile_contract",
            ),
            pytest.param(
                {"fixture_name": "eth_precompile_contract_tx_receipt", "description": "ETH precompile contract"},
                id="eth_precompile",
            ),
            pytest.param(
                {"fixture_name": "precompiled_neon_contract_tx_receipt", "description": "Precompiled NEON contract"},
                id="neon_precompile",
            ),
            pytest.param(
                {"fixture_name": "chain_transactions_receipt", "description": "Chain transactions"},
                id="chain_transactions",
            ),
            pytest.param(
                {"fixture_name": "trivial_revert_tx_receipt", "description": "Trivial revert"}, id="trivial_revert"
            ),
            pytest.param(
                {"fixture_name": "revert_in_called_contract_tx_receipt", "description": "Revert in called contract"},
                id="revert_in_called_contract",
            ),
            pytest.param(
                {"fixture_name": "zero_division_tx_receipt", "description": "Zero division transaction"},
                id="zero_division",
            ),
        ],
    )
    def test_transaction_types(self, test_case, request):
        """
        Test different types of transactions with tracer_transaction method.
        """
        receipt = request.getfixturevalue(test_case["fixture_name"])
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
        self.verify_common_fields(tracer_response, tx_data)

    def test_chain_transactions(self, chain_transactions_receipt):
        tx_data = self.web3_client.get_transaction_by_hash(chain_transactions_receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(chain_transactions_receipt["transactionHash"].hex())
        self.verify_common_fields(tracer_response, tx_data)
        # Expected trace structure based on the contract execution tree
        expected_traces = [
            {"trace": [], "subtraces": 2},  # Root call (Func1)
            {"trace": [0], "subtraces": 0},  # Func2 call
            {"trace": [1], "subtraces": 3},  # Func3 call
            {"trace": [1, 0], "subtraces": 0},  # Func4 call
            {"trace": [1, 1], "subtraces": 1},  # Func5 call
            {"trace": [1, 1, 0], "subtraces": 0},  # Func7 call
            {"trace": [1, 2], "subtraces": 0},  # Func6 call
        ]

        for i, expected in enumerate(expected_traces):
            result = tracer_response["result"][i]
            assert (
                result["traceAddress"] == expected["trace"]
            ), f"Trace {i} mismatch: expected {expected['trace']}, got {result['traceAddress']}"
            assert (
                result["subtraces"] == expected["subtraces"]
            ), f"Subtrace count mismatch for trace {i}: expected {expected['subtraces']}, got {result['subtraces']}"

        assert "error" not in tracer_response

    def test_trivial_reverted_tx(self, trivial_revert_tx_receipt):
        tx_data = self.web3_client.get_transaction_by_hash(trivial_revert_tx_receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(trivial_revert_tx_receipt["transactionHash"].hex())
        self.verify_common_fields(tracer_response, tx_data)

    @pytest.mark.skip("broken")
    def test_cancel_with_hash(self, json_rpc_client, expected_error_checker):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = expected_error_checker.functions.method1().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        receipt = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        assert receipt["result"]["transactionHash"] == resp["transactionHash"].hex()

    @pytest.mark.skip("broken")
    def test_failed_scheduled_tx(self, failed_scheduled_tx_receipt):
        tx_data = self.web3_client.get_transaction_by_hash(failed_scheduled_tx_receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(failed_scheduled_tx_receipt["transactionHash"].hex())
        self.verify_common_fields(tracer_response, tx_data)

    @pytest.mark.skip("broken")
    def test_reverted_iteration_tx(self, reverted_iterative_tx_receipt):
        tx_data = self.web3_client.get_transaction_by_hash(reverted_iterative_tx_receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(reverted_iterative_tx_receipt["transactionHash"].hex())
        self.verify_common_fields(tracer_response, tx_data)
