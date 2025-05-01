import allure

from integration.tests.tracer.tracer_helper import validate_response_result


class TracerValidator:

    @staticmethod
    @allure.step("check struct_log response")
    def check_tracer_struct_log(
        tracer_response, wait_result=True, wait_error=False, return_value: str = "", validation: bool = True
    ):
        if wait_error:
            assert tracer_response["result"]["failed"] is True
        else:
            assert "error" not in tracer_response["result"], "Error in tracer_response"
        if return_value:
            assert (
                tracer_response["result"]["returnValue"] == return_value
            ), f'Waited {return_value}, got {tracer_response["result"]["returnValue"]}'
        if wait_result:
            assert "result" in tracer_response
        if validation:
            validate_response_result(tracer_response)
        return True

    @staticmethod
    @allure.step("check callTracer response")
    def check_call_tracer_type(
        tracer_response: dict,
        tx_data,
        error_message="",
    ) -> bool:

        assert tracer_response["result"]["from"].lower() == tx_data["from"].lower()
        assert tracer_response["result"]["to"].lower() == tx_data["to"].lower()
        assert tracer_response["result"]["input"].lower() == "0x" + tx_data["input"].hex().lower()
        assert tracer_response["result"]["type"] == "CALL"

        if error_message:
            assert "error" in tracer_response["result"]
            assert tracer_response["result"]["error"] == error_message
        else:
            assert "error" not in tracer_response["result"]

        return True
