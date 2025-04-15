from integration.tests.tracer.tracer_helper import validate_response_result


class TracerValidator:
    def __init__(self, web3_client, tracer_api):
        self.web3_client = web3_client
        self.tracer_api = tracer_api

    def get_tx_data(self, tx_receipt):
        """Get transaction data by receipt."""
        return self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"].hex())

    def check_tracer_struct_log(
        self, tx_data, wait_error=False, error_message="", wait_return_value=False, return_value=""
    ) -> dict:
        params = [
            {
                "to": tx_data["to"],
                "from": tx_data["from"],
                "gas": hex(tx_data["gas"]),
                "gasPrice": hex(tx_data["gasPrice"]),
                "value": hex(tx_data["value"]),
                "data": "0x" + tx_data["input"].hex(),
            },
            hex(tx_data["blockNumber"]),
        ]

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        if wait_error:
            assert response["result"]["failed"] is True
        else:
            assert "error" not in response["result"], "Error in response"
        if wait_return_value:
            assert (
                response["result"]["returnValue"] == return_value
            ), f'Waited {return_value}, got {response["result"]["returnValue"]}'
        validate_response_result(response)

        return response

    def check_call_tracer_type(
        self,
        tx_data,
        wait_error=False,
        error_message="",
    ) -> dict:

        params = [tx_data["hash"].hex(), {"tracer": "callTracer", "tracerConfig": {"withLog": True}}]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        assert response["result"]["from"].lower() == tx_data["from"].lower()
        assert response["result"]["to"].lower() == tx_data["to"].lower()
        assert response["result"]["input"].lower() == "0x" + tx_data["input"].hex().lower()
        assert response["result"]["type"] == "CALL"

        if wait_error:
            assert "error" in response["result"]
            assert response["result"]["error"] == error_message
        else:
            assert "error" not in response["result"]

        return response

    def check_all_tracer_types(self, receipt):
        """Check that all trace types work correctly with tx"""
        tx_data = self.get_tx_data(receipt)
        self.check_tracer_struct_log(tx_data)
        self.check_call_tracer_type(tx_data)
        return tx_data
