import random
import string

import pytest

import allure
from utils.accounts import EthAccounts
from utils.models.result import EthGetBlockByHashResult
from utils.web3client import NeonChainWeb3Client


@pytest.fixture(scope="class")
def block_timestamp_contract(web3_client, accounts):
    block_timestamp_contract, receipt = web3_client.deploy_and_get_contract(
        "common/Block.sol", "0.8.10", accounts[0], contract_name="BlockTimestamp"
    )
    return block_timestamp_contract, receipt


@pytest.fixture(scope="class")
def block_number_contract(web3_client, accounts):
    block_number_contract, receipt = web3_client.deploy_and_get_contract(
        "common/Block.sol", "0.8.10", accounts[0], contract_name="BlockNumber"
    )
    return block_number_contract, receipt


@allure.feature("JSON-RPC validation")
@allure.story("Verify events")
@pytest.mark.usefixtures("accounts", "web3_client")
@pytest.mark.neon_only
class TestTimestamp:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    def test_block_timestamp_call(self, block_timestamp_contract, json_rpc_client):
        contract, _ = block_timestamp_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.getBlockTimestamp().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        validate_response = EthGetBlockByHashResult(**response)

        assert hex(contract.functions.getBlockTimestamp().call()) == validate_response.result.timestamp

    def test_block_timestamp_send_simple_trx(self, block_timestamp_contract, json_rpc_client):
        contract, _ = block_timestamp_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.callEvent().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        validate_response = EthGetBlockByHashResult(**response)

        event_logs = contract.events.Result().process_receipt(receipt)
        assert len(event_logs) == 1
        assert hex(event_logs[0]["args"]["block_timestamp"]) == validate_response.result.timestamp

    def test_block_timestamp_iterative(self, block_timestamp_contract, json_rpc_client):
        contract, _ = block_timestamp_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.callEventsInLoop().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        validate_response = EthGetBlockByHashResult(**response)

        event_logs = contract.events.Result().process_receipt(receipt)
        assert len(event_logs) == 1
        assert hex(event_logs[0]["args"]["block_timestamp"]) == validate_response.result.timestamp

    def test_block_timestamp_constructor(self, block_timestamp_contract, json_rpc_client):
        contract, receipt = block_timestamp_contract
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        validate_response = EthGetBlockByHashResult(**response)

        assert hex(contract.functions.getInitBlockTimestamp().call()) == validate_response.result.timestamp

    def test_block_timestamp_mapping_get_data(self, block_timestamp_contract, json_rpc_client):
        contract, _ = block_timestamp_contract
        sender_account = self.accounts[0]

        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.addData(text, 1).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        validate_response = EthGetBlockByHashResult(**response)

        event_logs = contract.events.DataAdded().process_receipt(receipt)
        assert len(event_logs) == 1

        info, value = contract.functions.getData(int(validate_response.result.timestamp, 16)).call()
        assert info == text
        assert value == 1
        assert event_logs[0]["args"]["timestamp"] == int(validate_response.result.timestamp, 16)


@allure.feature("JSON-RPC validation")
@allure.story("Verify events")
@pytest.mark.usefixtures("accounts", "web3_client")
@pytest.mark.neon_only
class TestBlockNumber:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    def test_block_number_call(self, block_number_contract, json_rpc_client):
        contract, _ = block_number_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.getBlockNumber().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        validate_response = EthGetBlockByHashResult(**response)

        assert hex(contract.functions.getBlockNumber().call()) == validate_response.result.number

    def test_block_number_event(self, block_number_contract, json_rpc_client):
        contract, _ = block_number_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.callEvent().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        validate_response = EthGetBlockByHashResult(**response)

        event_logs = contract.events.Result().process_receipt(receipt)
        assert len(event_logs) == 1
        assert hex(event_logs[0]["args"]["block_number"]) == validate_response.result.number
        assert hex(event_logs[0]["blockNumber"]) == validate_response.result.number

    def test_block_number_iterative(self, block_number_contract, json_rpc_client):
        contract, _ = block_number_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.callEventsInLoop().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        validate_response = EthGetBlockByHashResult(**response)

        event_logs = contract.events.Result().process_receipt(receipt)
        assert len(event_logs) == 1
        assert hex(event_logs[0]["args"]["block_number"]) == validate_response.result.number
        assert hex(event_logs[0]["blockNumber"]) == validate_response.result.number

    def test_block_number_constructor(self, block_number_contract, json_rpc_client):
        contract, receipt = block_number_contract
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        validate_response = EthGetBlockByHashResult(**response)

        assert hex(contract.functions.getInitBlockNumber().call()) == validate_response.result.number

    def test_block_number_mapping_get_data(self, block_number_contract, json_rpc_client):
        contract, _ = block_number_contract
        sender_account = self.accounts[0]

        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.addData(text, 1).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        validate_response = EthGetBlockByHashResult(**response)

        event_logs = contract.events.DataAdded().process_receipt(receipt)
        assert len(event_logs) == 1

        info, value = contract.functions.getData(int(validate_response.result.number, 16)).call()
        assert event_logs[0]["args"]["info"] == info
        assert event_logs[0]["args"]["value"] == value
        assert event_logs[0]["args"]["number"] == int(validate_response.result.number, 16)
