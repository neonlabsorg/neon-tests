import random
import typing as tp
import allure
import pytest
from integration.tests.basic.helpers.basic import BaseMixin
from utils.helpers import wait_condition

CONTRACT_CODE = '6060604052600080fd00a165627a7a72305820e75cae05548a56ec53108e39a532f0644e4b92aa900cc9f2cf98b7ab044539380029'
DEPLOY_CODE = '60606040523415600e57600080fd5b603580601b6000396000f300' + CONTRACT_CODE


@allure.story("Tracer API RPC calls historical methods check")
class TestTracerRpcCalls(BaseMixin):
    _contract: tp.Optional[tp.Any] = None

    @pytest.fixture
    def storage_contract(self) -> tp.Any:
        if not TestTracerRpcCalls._contract:
            contract, _ = self.web3_client.deploy_and_get_contract(
                "StorageSoliditySource.sol",
                "0.8.8",
                self.sender_account,
                contract_name="Storage",
                constructor_args=[],
            )
            TestTracerRpcCalls._contract = contract
        yield TestTracerRpcCalls._contract
        self.store_value(0, TestTracerRpcCalls._contract)

    def store_value(self, value, storage_contract):
        nonce = self.web3_client.eth.get_transaction_count(
            self.sender_account.address
        )
        instruction_tx = storage_contract.functions.store(value).build_transaction(
            {
                "nonce": nonce,
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        receipt = self.web3_client.send_transaction(
            self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        return instruction_tx, receipt

    def retrieve_value(self, storage_contract):
        nonce = self.web3_client.eth.get_transaction_count(
            self.sender_account.address
        )
        instruction_tx = storage_contract.functions.retrieve().build_transaction(
            {
                "nonce": nonce,
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        receipt = self.web3_client.send_transaction(
            self.sender_account, instruction_tx)

        assert receipt["status"] == 1
        return instruction_tx, receipt

    def make_tx_object(self, sender=None, receiver=None, tx=None) -> tp.Dict:
        if sender is None:
            sender = self.sender_account.address

        tx_call_obj = {
            "from": sender,
            "to": receiver,
            "value": hex(tx["value"]),
            "gas": hex(tx["gas"]),
            "gasPrice": hex(tx["gasPrice"]),
            "data": tx["data"],
        }

        return tx_call_obj

    def call_storage(self, storage_contract, storage_value, request_type):
        request_value = None
        _, _ = self.store_value(storage_value, storage_contract)
        tx, reciept = self.retrieve_value(storage_contract)
        tx_obj = self.make_tx_object(
            self.sender_account.address, storage_contract.address, tx)

        if request_type == "blockNumber":
            request_value = hex(reciept[request_type])
        else:
            request_value = reciept[request_type].hex()
        return tx_obj, request_value, reciept

    def test_eth_call_without_params(self):
        response = self.tracer_api.send_rpc(method="eth_call", params=[None])
        assert "error" in response, "Error not in response"

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_call(self, storage_contract, request_type):
        store_value_1 = random.randint(0, 100)
        tx_obj, request_value, _ = self.call_storage(
            storage_contract, store_value_1, request_type)
        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_call",
                                                                   req_type=request_type,
                                                                   params=[tx_obj, {request_type: request_value}])["result"], 0) == store_value_1,
                       timeout_sec=120)

        store_value_2 = random.randint(0, 100)
        tx_obj_2, request_value_2, _ = self.call_storage(
            storage_contract, store_value_2, request_type)
        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_call",
                                                                   req_type=request_type,
                                                                   params=[tx_obj_2, {request_type: request_value_2}])["result"], 0) == store_value_2,
                       timeout_sec=120)

        store_value_3 = random.randint(0, 100)
        tx_obj_3, request_value_3, _ = self.call_storage(
            storage_contract, store_value_3, request_type)
        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_call",
                                                                   req_type=request_type,
                                                                   params=[tx_obj_3, {request_type: request_value_3}])["result"], 0) == store_value_3,
                       timeout_sec=120)

    def test_eth_call_by_block_and_hash(self, storage_contract):
        store_value_1 = random.randint(0, 100)
        tx_obj, _, reciept = self.call_storage(
            storage_contract, store_value_1, "blockNumber")
        request_value_block = hex(reciept["blockNumber"])
        request_value_hash = reciept["blockHash"].hex()

        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_call",
                                                                   req_type="blockNumber",
                                                                   params=[tx_obj, {"blockNumber": request_value_block}])["result"], 0) == store_value_1,
                       timeout_sec=120)

        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_call",
                                                                   req_type="blockHash",
                                                                   params=[tx_obj, {"blockHash": request_value_hash}])["result"], 0) == store_value_1,
                       timeout_sec=120)

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_get_storage_at(self, storage_contract, request_type):
        store_value_1 = random.randint(0, 100)
        _, request_value_1, _ = self.call_storage(
            storage_contract, store_value_1, request_type)

        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_getStorageAt",
                                                                   req_type=request_type,
                                                                   params=[storage_contract.address,
                                                                           '0x0',
                                                                           {request_type: request_value_1}])["result"], 0) == store_value_1,
                       timeout_sec=120)

        store_value_2 = random.randint(0, 100)
        _, request_value_2, _ = self.call_storage(
            storage_contract, store_value_2, request_type)

        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_getStorageAt",
                                                                   req_type=request_type,
                                                                   params=[storage_contract.address,
                                                                           '0x0',
                                                                           {request_type: request_value_2}])["result"], 0) == store_value_2,
                       timeout_sec=120)

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_get_transaction_count(self, storage_contract, request_type):
        nonce = self.web3_client.eth.get_transaction_count(
            self.sender_account.address
        )
        store_value_1 = random.randint(0, 100)
        _, request_value_1, _ = self.call_storage(
            storage_contract, store_value_1, request_type)

        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_getTransactionCount",
                                                                   req_type=request_type,
                                                                   params=[self.sender_account.address,
                                                                           {request_type: request_value_1}])["result"], 0) == nonce + 2,
                       timeout_sec=120)

        request_value_2 = None
        _, reciept = self.retrieve_value(storage_contract)

        if request_type == "blockNumber":
            request_value_2 = hex(reciept[request_type])
        else:
            request_value_2 = reciept[request_type].hex()

        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_getTransactionCount",
                                                                   req_type=request_type,
                                                                   params=[self.sender_account.address,
                                                                           {request_type: request_value_2}])["result"], 0) == nonce + 3,
                       timeout_sec=120)

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_get_balance(self, request_type):
        transfer_amount = 0.1

        reciept_1 = self.send_neon(
            self.sender_account, self.recipient_account, transfer_amount)

        sender_balance = self.get_balance_from_wei(
            self.sender_account.address)
        recipient_balance = self.get_balance_from_wei(
            self.recipient_account.address)

        if request_type == "blockNumber":
            request_value = hex(reciept_1[request_type])
        else:
            request_value = reciept_1[request_type].hex()

        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_getBalance",
                                                                   req_type=request_type,
                                                                   params=[self.sender_account.address,
                                                                           {request_type: request_value}])["result"], 0) / 1e18 == sender_balance,
                       timeout_sec=120)

        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_getBalance",
                                                                   req_type=request_type,
                                                                   params=[self.recipient_account.address,
                                                                           {request_type: request_value}])["result"], 0) / 1e18 == recipient_balance,
                       timeout_sec=150)

        reciept_2 = self.send_neon(
            self.sender_account, self.recipient_account, transfer_amount)

        sender_balance_after = self.get_balance_from_wei(
            self.sender_account.address)
        recipient_balance_after = self.get_balance_from_wei(
            self.recipient_account.address)

        if request_type == "blockNumber":
            request_value = hex(reciept_2[request_type])
        else:
            request_value = reciept_2[request_type].hex()

        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_getBalance",
                                                                   req_type=request_type,
                                                                   params=[self.sender_account.address,
                                                                           {request_type: request_value}])["result"], 0) / 1e18 == sender_balance_after,
                       timeout_sec=120)

        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_getBalance",
                                                                   req_type=request_type,
                                                                   params=[self.recipient_account.address,
                                                                           {request_type: request_value}])["result"], 0) / 1e18 == recipient_balance_after,
                       timeout_sec=150)

    def test_eth_get_code(self):
        request_type = "blockNumber"

        nonce = self.web3_client.eth.get_transaction_count(
            self.sender_account.address
        )
        transaction = {
            "from": self.sender_account.address,
            "chainId": self.web3_client._chain_id,
            "gas": 987654321,
            "gasPrice": self.web3_client.gas_price(),
            "nonce": nonce,
            "value": 0,
            "data": bytes.fromhex(DEPLOY_CODE)
        }
        signed_tx = self.web3_client._web3.eth.account.sign_transaction(
            transaction, self.sender_account.key)
        tx = self.web3_client._web3.eth.send_raw_transaction(
            signed_tx.rawTransaction)
        receipt = self.web3_client._web3.eth.wait_for_transaction_receipt(tx)
        assert receipt["status"] == 1

        wait_condition(lambda: (self.tracer_api.tracer_send_rpc(method="eth_getCode",
                                                                req_type=request_type,
                                                                params=[receipt["contractAddress"],
                                                                        {request_type: hex(receipt[request_type] - 1)}]))["result"] == "",
                       timeout_sec=120)

        wait_condition(lambda: (self.tracer_api.tracer_send_rpc(method="eth_getCode",
                                                                req_type="blockHash",
                                                                params=[receipt["contractAddress"],
                                                                        {"blockHash": receipt["blockHash"].hex()}]))["result"] == CONTRACT_CODE,
                       timeout_sec=120)

        wait_condition(lambda: (self.tracer_api.tracer_send_rpc(method="eth_getCode",
                                                                req_type=request_type,
                                                                params=[receipt["contractAddress"],
                                                                        {request_type: hex(receipt[request_type])}]))["result"] == CONTRACT_CODE,
                       timeout_sec=120)

        wait_condition(lambda: (self.tracer_api.tracer_send_rpc(method="eth_getCode",
                                                                req_type=request_type,
                                                                params=[receipt["contractAddress"],
                                                                        {request_type: hex(receipt[request_type] + 1)}]))["result"] == CONTRACT_CODE,
                       timeout_sec=120)

    @pytest.mark.skip("Wait for NDEV-2135 will be merged and released to devnet")
    def test_check_neon_revision(self):
        revision = self.tracer_api.send_rpc(
            method="get_neon_revision", params={"slot": 1})
        assert revision["result"]["neon_revision"] is not None
