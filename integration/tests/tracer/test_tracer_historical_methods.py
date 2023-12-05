import random
import typing as tp

import pytest

import allure
from assertpy import assert_that

from integration.tests.basic.helpers.basic import BaseMixin
from utils.helpers import wait_condition

# test contract code to check eth_getCode method
CONTRACT_CODE = '6060604052600080fd00a165627a7a72305820e75cae05548a56ec53108e39a532f0644e4b92aa900cc9f2cf98b7ab044539380029'
DEPLOY_CODE = '60606040523415600e57600080fd5b603580601b6000396000f300' + CONTRACT_CODE


def store_value(storage, value, storage_contract):
    nonce = storage.web3_client.eth.get_transaction_count(
        storage.sender_account.address
    )
    instruction_tx = storage_contract.functions.store(value).build_transaction(
        {
            "nonce": nonce,
            "gasPrice": storage.web3_client.gas_price(),
        }
    )
    receipt = storage.web3_client.send_transaction(
        storage.sender_account, instruction_tx)
    assert receipt["status"] == 1


def retrieve_value(storage, storage_contract):
    nonce = storage.web3_client.eth.get_transaction_count(
        storage.sender_account.address
    )
    instruction_tx = storage_contract.functions.retrieve().build_transaction(
        {
            "nonce": nonce,
            "gasPrice": storage.web3_client.gas_price(),
        }
    )
    receipt = storage.web3_client.send_transaction(
        storage.sender_account, instruction_tx)

    assert receipt["status"] == 1
    return instruction_tx, receipt


def call_storage(storage, storage_contract, storage_value, request_type):
    request_value = None
    store_value(storage, storage_value, storage_contract)
    tx, receipt = retrieve_value(storage, storage_contract)

    tx_obj = storage.create_tx_object(sender=storage.sender_account.address,
                                      recipient=storage_contract.address,
                                      amount=tx["value"],
                                      gas=hex(tx["gas"]),
                                      gas_price=hex(tx["gasPrice"]),
                                      data=tx["data"],
                                      estimate_gas=False)
    del tx_obj["chainId"]
    del tx_obj["nonce"]
    tx_obj["value"] = hex(tx_obj["value"])

    if request_type == "blockNumber":
        request_value = hex(receipt[request_type])
    else:
        request_value = receipt[request_type].hex()
    return tx_obj, request_value, receipt


@allure.feature("Tracer API")
@allure.story("Tracer API RPC calls historical methods check")
class TestTracerHistoricalMethods(BaseMixin):
    _contract: tp.Optional[tp.Any] = None

    @pytest.fixture
    def storage_contract(self, storage_contract) -> tp.Any:
        if not TestTracerHistoricalMethods._contract:
            contract = storage_contract
            TestTracerHistoricalMethods._contract = contract
        yield TestTracerHistoricalMethods._contract
        store_value(self, 0, TestTracerHistoricalMethods._contract)

    def test_eth_call_without_params(self):
        response = self.tracer_api.send_rpc(method="eth_call", params=[None])
        assert "error" in response, "Error not in response"

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_call(self, storage_contract, request_type):
        store_value_1 = random.randint(0, 100)
        tx_obj, request_value, _ = call_storage(
            self, storage_contract, store_value_1, request_type)
        wait_condition(lambda: assert_that(int(self.tracer_api.send_rpc(method="eth_call",
                                                            req_type=request_type,
                                                            params=[tx_obj, {request_type: request_value}])["result"], 0)).is_equal_to(store_value_1),
                       timeout_sec=120)

        store_value_2 = random.randint(0, 100)
        tx_obj_2, request_value_2, _ = call_storage(self,
            storage_contract, store_value_2, request_type)
        wait_condition(lambda: assert_that(int(self.tracer_api.send_rpc(method="eth_call",
                                                            req_type=request_type,
                                                            params=[tx_obj_2, {request_type: request_value_2}])["result"], 0)).is_equal_to(store_value_2),
                       timeout_sec=120)

        store_value_3 = random.randint(0, 100)
        tx_obj_3, request_value_3, _ = call_storage(self,
            storage_contract, store_value_3, request_type)
        wait_condition(lambda: assert_that(int(self.tracer_api.send_rpc(method="eth_call",
                                                            req_type=request_type,
                                                            params=[tx_obj_3, {request_type: request_value_3}])["result"], 0)).is_equal_to(store_value_3),
                       timeout_sec=120)

    def test_eth_call_by_block_and_hash(self, storage_contract):
        store_value_1 = random.randint(0, 100)
        tx_obj, _, receipt = call_storage(self,
            storage_contract, store_value_1, "blockNumber")
        request_value_block = hex(receipt["blockNumber"])
        request_value_hash = receipt["blockHash"].hex()

        wait_condition(lambda: assert_that(int(self.tracer_api.send_rpc(method="eth_call",
                                                            req_type="blockNumber",
                                                            params=[tx_obj, {"blockNumber": request_value_block}])["result"], 0)).is_equal_to(store_value_1),
                       timeout_sec=120)

        wait_condition(lambda: assert_that(int(self.tracer_api.send_rpc(method="eth_call",
                                                            req_type="blockHash",
                                                            params=[tx_obj, {"blockHash": request_value_hash}])["result"], 0)).is_equal_to(store_value_1),
                       timeout_sec=120)

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_get_storage_at(self, storage_contract, request_type):
        store_value_1 = random.randint(0, 100)
        _, request_value_1, _ = call_storage(self,
            storage_contract, store_value_1, request_type)

        wait_condition(lambda: assert_that(int(self.tracer_api.send_rpc(method="eth_getStorageAt",
                                                            req_type=request_type,
                                                            params=[storage_contract.address,
                                                                    '0x0',
                                                                    {request_type: request_value_1}])["result"], 0)).is_equal_to(store_value_1),
                       timeout_sec=120)

        store_value_2 = random.randint(0, 100)
        _, request_value_2, _ = call_storage(self,
            storage_contract, store_value_2, request_type)

        wait_condition(lambda: assert_that(int(self.tracer_api.send_rpc(method="eth_getStorageAt",
                                                            req_type=request_type,
                                                            params=[storage_contract.address,
                                                                    '0x0',
                                                                    {request_type: request_value_2}])["result"], 0)).is_equal_to(store_value_2),
                       timeout_sec=120)

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_get_transaction_count(self, storage_contract, request_type):
        nonce = self.web3_client.eth.get_transaction_count(
            self.sender_account.address
        )
        store_value_1 = random.randint(0, 100)
        _, request_value_1, _ = call_storage(self,
            storage_contract, store_value_1, request_type)

        wait_condition(lambda: assert_that(int(self.tracer_api.send_rpc(method="eth_getTransactionCount",
                                                            req_type=request_type,
                                                            params=[self.sender_account.address,
                                                                    {request_type: request_value_1}])["result"], 0)).is_equal_to(nonce + 2),
                       timeout_sec=120)

        request_value_2 = None
        _, receipt = retrieve_value(self, storage_contract)

        if request_type == "blockNumber":
            request_value_2 = hex(receipt[request_type])
        else:
            request_value_2 = receipt[request_type].hex()

        wait_condition(lambda: assert_that(int(self.tracer_api.send_rpc(method="eth_getTransactionCount",
                                                            req_type=request_type,
                                                            params=[self.sender_account.address,
                                                                    {request_type: request_value_2}])["result"], 0)).is_equal_to(nonce + 3),
                       timeout_sec=120)

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_get_balance(self, request_type):
        transfer_amount = 0.1

        receipt_1 = self.send_neon(
            self.sender_account, self.recipient_account, transfer_amount)
        assert receipt_1["status"] == 1

        sender_balance = self.get_balance(self.sender_account.address)
        recipient_balance = self.get_balance(self.recipient_account.address)

        if request_type == "blockNumber":
            request_value = hex(receipt_1[request_type])
        else:
            request_value = receipt_1[request_type].hex()

        wait_condition(lambda: assert_that(int(self.tracer_api.send_rpc(method="eth_getBalance",
                                                                        req_type=request_type,
                                                                        params=[self.sender_account.address,
                                                                                {request_type: request_value}])[
                                                   "result"], 0)).is_equal_to(sender_balance),
                       timeout_sec=120)

        wait_condition(lambda: assert_that(int(self.tracer_api.send_rpc(method="eth_getBalance",
                                                                        req_type=request_type,
                                                                        params=[self.recipient_account.address,
                                                                                {request_type: request_value}])[
                                                   "result"], 0)).is_equal_to(recipient_balance),
                       timeout_sec=120)

        receipt_2 = self.send_neon(
            self.sender_account, self.recipient_account, transfer_amount)
        assert receipt_2["status"] == 1

        sender_balance_after = self.get_balance(self.sender_account.address)
        recipient_balance_after = self.get_balance(self.recipient_account.address)

        if request_type == "blockNumber":
            request_value = hex(receipt_2[request_type])
        else:
            request_value = receipt_2[request_type].hex()

        wait_condition(lambda: assert_that(int(self.tracer_api.send_rpc(method="eth_getBalance",
                                                                        req_type=request_type,
                                                                        params=[self.sender_account.address,
                                                                                {request_type: request_value}])[
                                                   "result"], 0)).is_equal_to(sender_balance_after),
                       timeout_sec=120)

        wait_condition(lambda: assert_that(int(self.tracer_api.send_rpc(method="eth_getBalance",
                                                                        req_type=request_type,
                                                                        params=[self.recipient_account.address,
                                                                                {request_type: request_value}])[
                                                   "result"], 0)).is_equal_to(recipient_balance_after),
                       timeout_sec=120)

        assert_that(recipient_balance_after / 1e18).is_close_to((recipient_balance + transfer_amount * 1e18) / 1e18, 1e-9)
        assert_that(sender_balance_after).is_less_than(sender_balance - transfer_amount * 1e18)

    def test_eth_get_code(self):
        request_type = "blockNumber"

        tx = self.create_tx_object(sender=self.sender_account.address,
                                   amount=0,
                                   nonce=self.web3_client.eth.get_transaction_count(
                                       self.sender_account.address),
                                   data=bytes.fromhex(DEPLOY_CODE))
        del tx["to"]
        del tx["gas"]

        receipt = self.web3_client.send_transaction(
            account=self.sender_account, transaction=tx)
        assert receipt["status"] == 1

        wait_condition(lambda: assert_that(self.tracer_api.send_rpc(method="eth_getCode",
                                                         req_type=request_type,
                                                         params=[receipt["contractAddress"],
                                                                 {request_type: hex(receipt[request_type] - 1)}])["result"]).is_equal_to(""),
                       timeout_sec=120)

        wait_condition(lambda: assert_that(self.tracer_api.send_rpc(method="eth_getCode",
                                                         req_type="blockHash",
                                                         params=[receipt["contractAddress"],
                                                                 {"blockHash": receipt["blockHash"].hex()}])["result"]).is_equal_to(CONTRACT_CODE),
                       timeout_sec=120)

        wait_condition(lambda: assert_that(self.tracer_api.send_rpc(method="eth_getCode",
                                                         req_type=request_type,
                                                         params=[receipt["contractAddress"],
                                                                 {request_type: hex(receipt[request_type])}])["result"]).is_equal_to(CONTRACT_CODE),
                       timeout_sec=120)

        wait_condition(lambda: assert_that(self.tracer_api.send_rpc(method="eth_getCode",
                                                         req_type=request_type,
                                                         params=[receipt["contractAddress"],
                                                                 {request_type: hex(receipt[request_type] + 1)}])["result"]).is_equal_to(CONTRACT_CODE),
                       timeout_sec=120)

    @pytest.mark.skip("Not released yet")
    def test_check_neon_revision(self):
        revision = self.tracer_api.send_rpc(
            method="get_neon_revision", params={"slot": 1})
        assert revision["result"]["neon_revision"] is not None
