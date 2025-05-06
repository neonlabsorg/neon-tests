import pytest

from utils.tracer_client import TracerClient
from utils.web3client import NeonChainWeb3Client


@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api")
class TestTraceTransactionMethod:
    web3_client: NeonChainWeb3Client
    tracer_api: TracerClient

    @staticmethod
    def verify_common_fields(tracer_response, tx_data):
        """Common transaction verification logic"""
        assert "error" not in tracer_response
        assert tx_data["from"].lower() == tracer_response["result"][0]["action"]["from"].lower()
        assert tx_data["to"].lower() == tracer_response["result"][0]["action"]["to"].lower()
        assert tx_data["hash"].to_0x_hex() == tracer_response["result"][0]["transactionHash"]
        assert tx_data["input"].to_0x_hex() == tracer_response["result"][0]["action"]["input"]
        assert tx_data["blockHash"].to_0x_hex() == tracer_response["result"][0]["blockHash"]
        assert tx_data["gas"] == int(tracer_response["result"][0]["action"]["gas"], 16)

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

    def test_scheduled_tx(self, scheduled_tx_receipt):
        receipt = scheduled_tx_receipt
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
        self.verify_common_fields(tracer_response, tx_data)
        assert "error" not in tracer_response

    def test_multiply_scheduled_tx(self, multiply_scheduled_tx_receipts):
        for receipt in multiply_scheduled_tx_receipts:
            tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
            tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
            self.verify_common_fields(tracer_response, tx_data)
            assert "error" not in tracer_response

    def test_trivial_revert(self, trivial_revert_tx_receipt):
        receipt = trivial_revert_tx_receipt
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
        self.verify_common_fields(tracer_response, tx_data)
        assert "error" not in tracer_response

    def test_recursion_tx(self, recursion_tx_receipt):
        receipt = recursion_tx_receipt
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
        self.verify_common_fields(tracer_response, tx_data)
        assert "error" not in tracer_response

    def test_multiply_recursion_tx(self, multiply_recursion_tx_receipt):
        receipt = multiply_recursion_tx_receipt
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
        self.verify_common_fields(tracer_response, tx_data)
        assert "error" not in tracer_response

    def test_iteractive_tx(self, iteration_tx_receipt):
        receipt = iteration_tx_receipt
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
        self.verify_common_fields(tracer_response, tx_data)
        assert "error" not in tracer_response

    def test_chain_transactions(self, chain_transactions_receipt):
        receipt = chain_transactions_receipt
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        tracer_response = self.tracer_api.trace_transaction(receipt["transactionHash"].hex())
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
