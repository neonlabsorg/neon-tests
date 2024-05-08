import random

import allure
import pytest

from utils.helpers import wait_condition
from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts
from utils.tracer_client import TracerClient
from integration.tests.tracer.test_tracer_historical_methods import call_storage, store_value

CODE_OVERRIDED = "0x608060405234801561001057600080fd5b506004361061004c5760003560e01c80632e64cec1146100515780635e383d211461006c5780636057361d1461007f578063dce4a44714610094575b600080fd5b6100596100b4565b6040519081526020015b60405180910390f35b61005961007a36600461019b565b6100c8565b61009261008d36600461019b565b6100e9565b005b6100a76100a23660046101b4565b61010d565b60405161006391906101e4565b600080546100c3906001610239565b905090565b600181815481106100d857600080fd5b600091825260209091200154905081565b60008190556040805160208101909152818152610109906001908161013b565b5050565b6060816001600160a01b0316803b806020016040519081016040528181526000908060200190933c92915050565b828054828255906000526020600020908101928215610176579160200282015b8281111561017657825182559160200191906001019061015b565b50610182929150610186565b5090565b5b808211156101825760008155600101610187565b6000602082840312156101ad57600080fd5b5035919050565b6000602082840312156101c657600080fd5b81356001600160a01b03811681146101dd57600080fd5b9392505050565b600060208083528351808285015260005b81811015610211578581018301518582016040015282016101f5565b81811115610223576000604083870101525b50601f01601f1916929092016040019392505050565b6000821982111561025a57634e487b7160e01b600052601160045260246000fd5b50019056fea264697066735822122027ccfc0daba8d2d69d8a56122f60c379952cad9600de2be04409fc7cb4c51c5c64736f6c63430008080033"

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

    @pytest.fixture(scope="class")
    def call_store_value(self, storage_contract, web3_client):
        sender_account = self.accounts[0]
        receipt = store_value(sender_account, 57, storage_contract, web3_client)
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

    def test_stateOverrides_debug_traceCall_override_nonce_for_both_accounts(self, call_storage_tx):
        address_from = call_storage_tx["from"].lower()
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params.append({"tracer": "prestateTracer"})
        response = self.tracer_api.send_rpc(method="debug_traceCall", params=params)

        
        override_params = {"stateOverrides": {address_from: {"nonce": 17}, address_to: {"nonce": 9}}, 
                           "tracer": "prestateTracer"}
        params.pop(2)
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc(method="debug_traceCall", params=params)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response_overrided["result"][address_to]["nonce"] != response["result"][address_to]["nonce"]
        assert response_overrided["result"][address_to]["nonce"] == 9
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

        override_params = {"stateOverrides": {address_from: {"balance": "0x25bf6196bd1"}, 
                                              address_to: {"balance": "0x1aa535d3d0c"}},
                            "tracer": "prestateTracer"}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc(method="debug_traceCall", params=params)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response_overrided["result"][address_from]["balance"] != response["result"][address_from]["balance"]
        assert response_overrided["result"][address_from]["balance"] == "0x25bf6196bd1"
        assert response_overrided["result"][address_to]["balance"] != response["result"][address_to]["balance"]
        assert response_overrided["result"][address_to]["balance"] == "0x1aa535d3d0c"

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

    def test_stateOverrides_debug_traceCall_override_state(self, call_storage_tx):
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params.append({"tracer": "prestateTracer"})
        response = self.tracer_api.send_rpc(method="debug_traceCall", params=params)
        params.pop(2)

        override_params = {"stateOverrides": {address_to: {"state": {"0x0" : "0x01"}}}, "tracer": "prestateTracer"}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc(method="debug_traceCall", params=params)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        index_0 = "0x0000000000000000000000000000000000000000000000000000000000000000"
        assert int(response["result"][address_to]["storage"][index_0], 0) == 57
        assert int(response_overrided["result"][address_to]["storage"][index_0], 0) == 1

    @pytest.mark.skip("NDEV-3002")
    def test_stateOverrides_debug_traceCall_override_stateDiff(self, call_store_value):
        address_to = call_store_value["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_store_value)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params.append({"tracer": "prestateTracer"})
        response = self.tracer_api.send_rpc(method="debug_traceCall", params=params)
        params.pop(2)

        override_params = {"stateOverrides": {address_to: {"stateDiff": {"0x3" : "0x11", "0x4": "0x12"}}}, "tracer": "prestateTracer"}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc(method="debug_traceCall", params=params)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        index = "0xb10e2d527612073b26eecdfd717e6a320cf44b4afac2b0732d9fcbe2b7fa0cf6"
        index_0 = "0x0000000000000000000000000000000000000000000000000000000000000000"
        index_1 = "0x0000000000000000000000000000000000000000000000000000000000000001"
        index_3 = "0x0000000000000000000000000000000000000000000000000000000000000003"
        index_4 = "0x0000000000000000000000000000000000000000000000000000000000000004"
        assert int(response["result"][address_to]["storage"][index_0], 0) == int(response_overrided["result"][address_to]["storage"][index_0], 0)
        assert int(response["result"][address_to]["storage"][index_1], 0) == int(response_overrided["result"][address_to]["storage"][index_1], 0)
        assert int(response["result"][address_to]["storage"][index], 0) == int(response_overrided["result"][address_to]["storage"][index], 0)
        assert int(response_overrided["result"][address_to]["storage"][index_3], 0) == 17
        assert int(response_overrided["result"][address_to]["storage"][index_4], 0) == 18
   
    def test_stateOverrides_debug_traceCall_override_all_params(self, call_storage_tx):
        address_from = call_storage_tx["from"].lower()
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params.append({"tracer": "prestateTracer"})
        response = self.tracer_api.send_rpc(method="debug_traceCall", params=params)
        params.pop(2)

        override_params = {"stateOverrides": {address_from: {"code": "0x6080604052348015",  
                                                             "nonce": 25,
                                                             "state": {"0x0" : "0x058"},
                                                             "balance": "0x01"}}, 
                            "tracer": "prestateTracer"}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc(method="debug_traceCall", params=params)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert "code" not in response["result"][address_from], "Code have not to be in response"
        assert response_overrided["result"][address_to]["code"] != response["result"][address_to]["code"]
        assert response_overrided["result"][address_from]["code"] == "0x6080604052348015"
        assert response_overrided["result"][address_from]["nonce"] != response["result"][address_from]["nonce"]
        assert response_overrided["result"][address_from]["nonce"] == 25
        index_0 = "0x0000000000000000000000000000000000000000000000000000000000000000"
        assert int(response["result"][address_to]["storage"][index_0], 0) == 57
        assert int(response_overrided["result"][address_to]["storage"][index_0], 0) == 88
        assert response_overrided["result"][address_from]["balance"] != response["result"][address_from]["balance"]
        assert response_overrided["result"][address_from]["balance"] == "0x01"

    def test_stateOverrides_debug_traceCall_do_not_override_storage(self, call_storage_tx):
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
        index_0 = "0x0000000000000000000000000000000000000000000000000000000000000000"
        assert int(response["result"][address_to]["storage"][index_0], 0) == 57
        assert int(response_overrided["result"][address_to]["storage"][index_0], 0) == 57

    @pytest.mark.skip("NDEV-3001")
    def test_stateOverrides_debug_traceCall_override_with_state_and_stateDiff(self, call_store_value):
        address_to = call_store_value["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_store_value)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params.append({"tracer": "prestateTracer"})
        response = self.tracer_api.send_rpc(method="debug_traceCall", params=params)
        params.pop(2)

        override_params = {"stateOverrides": {address_to: {"stateDiff": {"0x3" : "0x11"}, "state": {"0x0": "0x15"}}}, 
                           "tracer": "prestateTracer"}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc(method="debug_traceCall", params=params)
        assert "error" in response_overrided, "State and stateDiff are not allowed to be used together"
    
    @pytest.mark.skip("NDEV-3003")
    def test_stateOverrides_eth_call_override_nonce(self, call_storage_tx):
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        response = self.tracer_api.send_rpc_and_wait_response("eth_call", params)

        override_params = {address_to: {"code": CODE_OVERRIDED} }
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("eth_call", params)

        assert response_overrided["result"] != response["result"]
        assert int(response["result"], 0) == 57 
        assert int(response_overrided["result"], 0) == 58
