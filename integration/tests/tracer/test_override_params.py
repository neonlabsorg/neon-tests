import json
import random

import allure
import pytest

from utils.helpers import wait_condition
from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts
from utils.tracer_client import TracerClient
from integration.tests.tracer.test_tracer_historical_methods import call_storage


@allure.feature("Tracer API")
@allure.story("Tracer API RPC calls debug methods with stateOverrides and/or blockOverrides params check")
@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api")
class TestTracerOverrideParams:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    tracer_api: TracerClient

    @pytest.fixture(scope="class")
    def call_storage_tx(self, storage_contract, web3_client):
        sender_account = self.accounts[0]
        _, _, receipt = call_storage(sender_account, storage_contract, 57, "blockNumber", web3_client)
        tx_hash = receipt["transactionHash"].hex()

        wait_condition(
            lambda: self.web3_client.get_transaction_by_hash(tx_hash) is not None,
            timeout_sec=10,
        )
        return self.web3_client.get_transaction_by_hash(tx_hash)
    
    def fill_params_for_storage_contract_trace_call(self, tx):
        return [
            {
                "to": tx["to"],
                "from": tx["from"],
                "gas": hex(tx["gas"]),
                "gasPrice": hex(tx["gasPrice"]),
                "value": hex(tx["value"]),
                "data": tx["input"].hex(),
            },
            hex(tx["blockNumber"]),
        ]

    def test_stateOverrides_debug_traceCall_override_nonce(self, call_storage_tx):
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params.append({"tracer": "prestateTracer"})
        response = self.tracer_api.send_rpc(method="debug_traceCall", params=params)

        address_from = call_storage_tx["from"].lower()
        override_params = {"stateOverrides": {address_from: {"nonce": 17}}, "tracer": "prestateTracer"}
        params.pop(2)
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc(method="debug_traceCall", params=params)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response_overrided["result"][address_from]["nonce"] != response["result"][address_from]["nonce"]
        assert response_overrided["result"][address_from]["nonce"] == 17

    def test_stateOverrides_debug_traceCall_override_balance(self, call_storage_tx):
        address_from = call_storage_tx["from"].lower()
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params.append({"tracer": "prestateTracer"})
        response = self.tracer_api.send_rpc(method="debug_traceCall", params=params)
        params.pop(2)

        override_params = {"stateOverrides": {address_from: {"balance": 170000000000000000}, 
                                              address_to: {"balance": 120000000000000000}},
                            "tracer": "prestateTracer"}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc(method="debug_traceCall", params=params)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response_overrided["result"][address_from]["balance"] != response["result"][address_from]["balance"]
        assert response_overrided["result"][address_from]["balance"] == 170000000000000000
        assert response_overrided["result"][address_to]["balance"] != response["result"][address_to]["balance"]
        assert response_overrided["result"][address_to]["balance"] == 120000000000000000

    def test_stateOverrides_debug_traceCall_override_code_of_accounts(self, call_storage_tx):
        address_from = call_storage_tx["from"].lower()
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params.append({"tracer": "prestateTracer"})
        response = self.tracer_api.send_rpc(method="debug_traceCall", params=params)
        params.pop(2)

        override_params = {"stateOverrides": {address_from: {"code": "0x6080604052348015"}, 
                                              address_to: {"code": "0x23480156994322"} }, 
                            "tracer": "prestateTracer"}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc(method="debug_traceCall", params=params)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert "code" not in response["result"][address_from], "Code have not to be in response"
        assert response_overrided["result"][address_from]["code"] == "0x6080604052348015"
        assert response_overrided["result"][address_to]["code"] != response["result"][address_to]["code"]
        assert response_overrided["result"][address_to]["code"] == "0x23480156994322"

    def test_stateOverrides_debug_traceCall_do_not_override_storage(self, call_storage_tx):
        address_from = call_storage_tx["from"].lower()
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params.append({"tracer": "prestateTracer"})
        response = self.tracer_api.send_rpc(method="debug_traceCall", params=params)
        params.pop(2)

        override_params = {"stateOverrides": {address_to: {"storage": {"0x0": "0x058"}} }, "tracer": "prestateTracer"}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc(method="debug_traceCall", params=params)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response["result"][address_to]["storage"]["0x0000000000000000000000000000000000000000000000000000000000000000"] == \
            "0x0000000000000000000000000000000000000000000000000000000000000039"
        assert response_overrided["result"][address_to]["storage"]["0x0000000000000000000000000000000000000000000000000000000000000000"] == \
            "0x0000000000000000000000000000000000000000000000000000000000000039"

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_stateOverrides_eth_call_override_nonce(self, storage_contract, request_type):
        sender_account = self.accounts[0]
        store_value_1 = random.randint(0, 100)
        tx_obj, request_value, _ = call_storage(
            sender_account, storage_contract, store_value_1, request_type, self.web3_client
        )
        wait_condition(
            lambda: int(
                self.tracer_api.send_rpc(
                    method="eth_call", req_type=request_type, params=[tx_obj, {request_type: request_value}]
                )["result"],
                0,
            )
            == store_value_1,
            timeout_sec=120,
        )

        store_value_2 = random.randint(0, 100)
        tx_obj_2, request_value_2, _ = call_storage(
            sender_account, storage_contract, store_value_2, request_type, self.web3_client
        )
        wait_condition(
            lambda: int(
                self.tracer_api.send_rpc(
                    method="eth_call", req_type=request_type, params=[tx_obj_2, {request_type: request_value_2}]
                )["result"],
                0,
            )
            == store_value_2,
            timeout_sec=120,
        )

        store_value_3 = random.randint(0, 100)
        tx_obj_3, request_value_3, _ = call_storage(sender_account, storage_contract, store_value_3, request_type, self.web3_client)
        wait_condition(
            lambda: int(
                self.tracer_api.send_rpc(
                    method="eth_call", req_type=request_type, params=[tx_obj_3, {request_type: request_value_3}]
                )["result"],
                0,
            )
            == store_value_3,
            timeout_sec=120,
        )
