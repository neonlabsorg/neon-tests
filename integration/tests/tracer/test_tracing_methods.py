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
            pytest.param(
                {"fixture_name": "recursion_tx_receipt", "description": "Recursion transaction"}, id="recursion"
            ),
            pytest.param(
                {"fixture_name": "iteration_tx_receipt", "description": "Iterative transaction"}, id="iterative"
            ),
            pytest.param(
                {
                    "fixture_name": "iterative_tx_with_erc20_for_spl_receipt",
                    "description": "Iterative transaction with 51 contract calls",
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
            pytest.param(
                {
                    "fixture_name": "trivial_revert_tx_receipt",
                    "description": "Trivial revert",
                    "error_message": "Error(string): ('Revert Contract',)",
                },
                id="trivial_revert",
            ),
            pytest.param(
                {
                    "fixture_name": "revert_in_called_contract_tx_receipt",
                    "description": "Revert in called contract",
                    "error_message": "Error(string): ('Insufficient balance for transfer,",
                },
                id="revert_in_called_contract",
            ),
            pytest.param(
                {
                    "fixture_name": "zero_division_tx_receipt",
                    "description": "Zero division transaction",
                    "error_message": "Panic(uint256): Division or modulo by zero",
                },
                id="zero_division",
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

    test_specs = [
        # === НЕГАТИВНЫЕ СЛУЧАИ ===
        # trivial error
        {
            "id": "trivial_error__trace_transaction",
            "fixture_name": "trivial_error_tx_receipt",
            "tracer_name": "trace_transaction",
            "tracer_args": [],
            "validator_name": "check_trace_transaction_response",
            "validator_args": ["tx_data", "receipt"],
            "validator_kwargs": {"error_message": "Error(string): ('Revert Contract',)"},
        },
        # {
        #     "id": "trivial_error__debug_trace_basic",
        #     "fixture_name": "trivial_error_tx_receipt",
        #     "tracer_name": "debug_trace_transaction",
        #     "tracer_args": ["callTracer"],
        #     "validator_name": "check_call_tracer_type",
        #     "validator_args": ["tx_data"],
        #     "validator_kwargs": {"error_message": "execution reverted"},
        # },
        # # trivial revert
        # {
        #     "id": "trivial_revert__trace_transaction",
        #     "fixture_name": "trivial_revert_tx_receipt",
        #     "tracer_name": "trace_transaction",
        #     "tracer_args": [],
        #     "validator_name": "check_trace_transaction_response",
        #     "validator_args": ["tx_data", "receipt"],
        #     "validator_kwargs": {"error_message": "Error(string): ('Revert Contract',)"},
        # },
        # {
        #     "id": "trivial_revert__debug_trace_basic",
        #     "fixture_name": "trivial_revert_tx_receipt",
        #     "tracer_name": "debug_trace_transaction",
        #     "tracer_args": ["callTracer"],
        #     "validator_name": "check_call_tracer_type",
        #     "validator_args": ["tx_data"],
        #     "validator_kwargs": {"error_message": "execution reverted"},
        # },
        # # revert in called contract
        # {
        #     "id": "revert_in_called__trace_transaction",
        #     "fixture_name": "revert_in_called_contract_tx_receipt",
        #     "tracer_name": "trace_transaction",
        #     "tracer_args": [],
        #     "validator_name": "check_trace_transaction_response",
        #     "validator_args": ["tx_data", "receipt"],
        #     "validator_kwargs": {"error_message": "Error(string): ('Insufficient balance for transfer,"},
        # },
        # {
        #     "id": "revert_in_called__debug_trace_basic",
        #     "fixture_name": "revert_in_called_contract_tx_receipt",
        #     "tracer_name": "debug_trace_transaction",
        #     "tracer_args": ["callTracer"],
        #     "validator_name": "check_call_tracer_type",
        #     "validator_args": ["tx_data"],
        #     "validator_kwargs": {"error_message": "execution reverted"},
        # },
        # zero division
        {
            "id": "zero_division__trace_transaction",
            "fixture_name": "zero_division_tx_receipt",
            "tracer_name": "trace_transaction",
            "tracer_args": [],
            "validator_name": "check_trace_transaction_response",
            "validator_args": ["tx_data", "receipt"],
            "validator_kwargs": {"Panic(uint256): Division or modulo by zero"},
        },
        {
            "id": "zero_division__debug_trace_basic",
            "fixture_name": "zero_division_tx_receipt",
            "tracer_name": "debug_trace_transaction",
            "tracer_args": ["callTracer"],
            "validator_name": "check_call_tracer_type",
            "validator_args": ["tx_data"],
            "validator_kwargs": {"error_message": "execution reverted"},
        },
    ]

    @pytest.mark.parametrize("spec", test_specs, ids=[s["id"] for s in test_specs])
    def test_all_tracers(self, spec, request):

        # 1) prepare
        receipt = request.getfixturevalue(spec["fixture_name"])
        tx_hash = receipt["transactionHash"].hex()
        tx_data = self.web3_client.get_transaction_by_hash(tx_hash)

        # 2) call tracer method
        tracer = getattr(self.tracer_api, spec["tracer_name"])
        if spec["tracer_name"] == "debug_trace_call":
            response = tracer(tx_data)
        else:
            response = tracer(tx_hash, *spec["tracer_args"])

        # 3) validate
        validator = getattr(self.tracer_validator, spec["validator_name"])
        # call_args = [response] + [locals()[arg] for arg in spec["validator_args"]]
        call_args = [response, tx_data]
        validator(*call_args, **spec["validator_kwargs"])
