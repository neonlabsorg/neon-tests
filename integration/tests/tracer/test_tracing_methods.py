import pytest

from utils.tracer_client import TracerClient
from utils.tracer_validator import TracerValidator
from utils.web3client import NeonChainWeb3Client


@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api", "tracer_validator")
class TestTraceTransactionMethod:
    web3_client: NeonChainWeb3Client
    tracer_api: TracerClient
    tracer_validator: TracerValidator

    @pytest.mark.parametrize(
        "test_case",
        [
            pytest.param(
                {"fixture_name": "send_neon_tx_receipt", "description": "simple send transaction"},
                id="send neon transaction",
            ),
        ],
    )
    @pytest.mark.parametrize(
        "tracer_name, tracer_args, validator_name",
        [
            ("trace_transaction", [], "check_trace_transaction_response"),
            ("debug_trace_transaction", ["callTracer"], "check_call_tracer_type"),
            ("debug_trace_transaction", ["callTracer", True, True], "check_call_tracer_type"),
            ("debug_trace_transaction", ["callTracer", True, False], "check_call_tracer_type"),
            ("debug_trace_transaction", ["callTracer", False, True], "check_call_tracer_type"),
            ("debug_trace_transaction", ["callTracer", False, False], "check_call_tracer_type"),
            ("debug_trace_call", [], "check_tracer_struct_log"),
        ],
        ids=[
            "trace_transaction",
            "debug_trace_transaction_basic",
            "debug_trace_transaction_with_log_and_onlytopcall",
            "debug_trace_transaction_with_log_no_OnlyTopCall",
            "debug_trace_transaction_no_log_with_onlytopcall",
            "debug_trace_transaction_no_log_no_onlytopcall",
            "debug_trace_call",
        ],
    )
    def test_positive_transaction_types(self, test_case, tracer_name, tracer_args, validator_name, request):
        """
        Test different tracer methods for various transaction types.
        """
        receipt = request.getfixturevalue(test_case["fixture_name"])
        tx_hash = receipt["transactionHash"].hex()
        tx_data = self.web3_client.get_transaction_by_hash(tx_hash)

        # Dynamically call the selected tracer method
        tracer_method = getattr(self.tracer_api, tracer_name)
        if tracer_name == "debug_trace_call":
            response = tracer_method(tx_data)
        else:
            response = tracer_method(tx_hash, *tracer_args)

        # Dynamically call the corresponding validator
        validator_method = getattr(self.tracer_validator, validator_name)
        # trace_transaction requires receipt as third arg
        if tracer_name == "trace_transaction":
            validator_method(response, tx_data, receipt)
        else:
            validator_method(response, tx_data)

    @pytest.mark.parametrize(
        "test_case",
        [
            pytest.param(
                {"fixture_name": "trivial_error_tx_receipt", "description": "trivial error transaction"},
                id="trivial error transaction",
            ),
        ],
    )
    @pytest.mark.parametrize(
        "tracer_name, tracer_args, validator_name,  validator_kwargs",
        [
            ("trace_transaction", [], "check_trace_transaction_response", {}),
            (
                "debug_trace_transaction",
                ["callTracer"],
                "check_call_tracer_type",
                {"error_message": "execution reverted"},
            ),
            (
                "debug_trace_transaction",
                ["callTracer", True, True],
                "check_call_tracer_type",
                {"error_message": "execution reverted"},
            ),
            (
                "debug_trace_transaction",
                ["callTracer", True, False],
                "check_call_tracer_type",
                {"error_message": "execution reverted"},
            ),
            (
                "debug_trace_transaction",
                ["callTracer", False, True],
                "check_call_tracer_type",
                {"error_message": "execution reverted"},
            ),
            (
                "debug_trace_transaction",
                ["callTracer", False, False],
                "check_call_tracer_type",
                {"error_message": "execution reverted"},
            ),
            ("debug_trace_call", [], "check_tracer_struct_log", {"wait_error": "True"}),
        ],
        ids=[
            "trace_transaction",
            "debug_trace_transaction_basic",
            "debug_trace_transaction_with_log_and_onlytopcall",
            "debug_trace_transaction_with_log_no_OnlyTopCall",
            "debug_trace_transaction_no_log_with_onlytopcall",
            "debug_trace_transaction_no_log_no_onlytopcall",
            "debug_trace_call",
        ],
    )
    def test_negative_cases_transaction_types(
        self, test_case, tracer_name, tracer_args, validator_name, validator_kwargs, request
    ):
        """
        Test different tracer methods for various transaction types.
        """
        receipt = request.getfixturevalue(test_case["fixture_name"])
        tx_hash = receipt["transactionHash"].hex()
        tx_data = self.web3_client.get_transaction_by_hash(tx_hash)

        # Dynamically call the selected tracer method
        tracer_method = getattr(self.tracer_api, tracer_name)
        if tracer_name == "debug_trace_call":
            response = tracer_method(tx_data)
        else:
            response = tracer_method(tx_hash, *tracer_args)

        # Dynamically call the corresponding validator with its args and kwargs
        validator_method = getattr(self.tracer_validator, validator_name)
        call_args = [response, tx_data]
        validator_method(*call_args, **validator_kwargs)
