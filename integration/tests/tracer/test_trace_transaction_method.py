import pytest

from utils.models.result import TraceTransactionResponse
from utils.tracer_client import TracerClient


@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api")
class TestTraceTransactionMethod:
    tracer_api: TracerClient

    def test_1(self, static_call_tx_receipt):

        response = self.tracer_api.trace_transaction(static_call_tx_receipt["transactionHash"].hex())
        print(response)
        TraceTransactionResponse(**response)
        assert "error" not in response

    def test_static_call(self, static_call_tx_receipt):
        pass

    def test_call_contract(self, call_tx_receipt):
        pass

    def test_delegate_call(self, delegate_call_tx_receipt):
        pass

    def test_call_code(self, call_code_tx_receipt):
        pass

    def test_call_with_events(self, call_with_events_tx_receipt):
        pass

    def test_iteractive_tx(self):
        pass

    def test_scheduled_tx(self):
        pass

    def test_multiply_scheduled_tx(self):
        pass

    def test_trivial_revert(self):
        pass

    def test_revert_with_fail(self):
        pass

    def test_eth_precompile_contract(self):
        pass

    def test_solana_precompile_contract(self):
        pass

    def test_neon_precompile_contract(self):
        pass
