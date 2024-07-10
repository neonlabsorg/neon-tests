import random
import string
from collections import Counter

import pytest

import allure
from integration.tests.basic.helpers.basic import NeonEventType
from integration.tests.basic.helpers.rpc_checks import (
    assert_event_by_type,
    assert_event_field,
    assert_events_order,
    count_events,
)
from utils.accounts import EthAccounts
from utils.helpers import wait_condition
from utils.models.result import NeonGetTransactionResult
from utils.web3client import NeonChainWeb3Client


@pytest.fixture(scope="class", params=["neon", "sol"])
def client_and_price(web3_client, web3_client_sol, sol_price, neon_price, request, pytestconfig):
    if request.param == "neon":
        return web3_client, neon_price
    elif request.param == "sol":
        if "sol" in pytestconfig.environment.network_ids:
            return web3_client_sol, sol_price
    pytest.skip(f"{request.param} chain is not available")


@allure.feature("JSON-RPC validation")
@allure.story("Verify events")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestEvents:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_basic_transtaction_receipt(self, json_rpc_client):
        sender_account, receiver_account = self.accounts[0], self.accounts[1]
        tx = self.web3_client.make_raw_tx(sender_account, receiver_account, 1000, estimate_gas=True)
        resp = self.web3_client.send_transaction(sender_account, tx)

        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)
        events_counter = count_events(validated_response)
        assert events_counter == Counter({"EnterCall": 1, "ExitStop": 1, "Return": 1})

        assert_events_order(validated_response)

        assert_event_by_type(validated_response, NeonEventType.EnterCreate)
        assert_event_by_type(validated_response, NeonEventType.ExitStop)
        assert_event_by_type(validated_response, NeonEventType.Return)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_basic_transtaction_receipt_transaction_hash(self, json_rpc_client):
        sender_account, receiver_account = self.accounts[0], self.accounts[1]
        tx = self.web3_client.make_raw_tx(sender_account, receiver_account, 1000, estimate_gas=True)
        resp = self.web3_client.send_transaction(sender_account, tx)

        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)

        transaction_hash = resp["transactionHash"].hex()
        assert_event_field(validated_response, NeonEventType.EnterCall, "transactionHash", transaction_hash)
        assert_event_field(validated_response, NeonEventType.ExitStop, "transactionHash", transaction_hash)
        assert_event_field(validated_response, NeonEventType.Return, "transactionHash", transaction_hash)

        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.ExitStop)
        assert_event_by_type(validated_response, NeonEventType.Return)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_basic_transtaction_receipt_to_address(self, json_rpc_client):
        sender_account, receiver_account = self.accounts[0], self.accounts[1]
        tx = self.web3_client.make_raw_tx(sender_account, receiver_account, 1000, estimate_gas=True)
        resp = self.web3_client.send_transaction(sender_account, tx)

        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)

        assert_event_field(validated_response, NeonEventType.EnterCall, "address", receiver_account.address)
        assert_event_field(validated_response, NeonEventType.ExitStop, "address", receiver_account.address)
        assert_event_field(validated_response, NeonEventType.Return, "address", None)

        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.ExitStop)
        assert_event_by_type(validated_response, NeonEventType.Return)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_basic_transtaction_receipt_contract(self, json_rpc_client, event_caller_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        number = random.randint(1, 5)
        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        bytes_array = text.encode().ljust(32, b"\0")

        instruction_tx = event_caller_contract.functions.allTypes(
            sender_account.address, number, text, bytes_array, True
        ).build_transaction(tx)

        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)

        events_counter = count_events(validated_response)
        assert events_counter == Counter({"EnterCall": 1, "ExitStop": 1, "Return": 1, "Log": 1})

        assert_event_field(validated_response, NeonEventType.EnterCall, "address", validated_response.result.to)
        assert_event_field(validated_response, NeonEventType.ExitStop, "address", validated_response.result.to)
        assert_event_field(validated_response, NeonEventType.Log, "address", validated_response.result.to)
        assert_event_field(validated_response, NeonEventType.Return, "address", None)

        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.ExitStop)
        assert_event_by_type(validated_response, NeonEventType.Return)
        assert_event_by_type(validated_response, NeonEventType.Log)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_basic_transtaction_receipt_nested_call(self, json_rpc_client, nested_call_contracts):
        sender_account = self.accounts[0]
        contract_a, contract_b, contract_c = nested_call_contracts
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_a.functions.method1(contract_b.address, contract_c.address).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)
        assert_events_order(validated_response)
        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.ExitStop)
        assert_event_by_type(validated_response, NeonEventType.Return)
        assert_event_by_type(validated_response, NeonEventType.Log)
        assert_event_by_type(validated_response, NeonEventType.ExitRevert)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_contract_interative_operation(
        self, counter_contract, client_and_price, account_with_all_tokens, json_rpc_client, operator
    ):
        w3_client, *_ = client_and_price

        sol_balance_before = operator.get_solana_balance()
        tx = w3_client.make_raw_tx(account_with_all_tokens.address)

        instruction_tx = counter_contract.functions.moreInstruction(0, 1000).build_transaction(tx)
        resp = w3_client.send_transaction(account_with_all_tokens, instruction_tx)
        wait_condition(lambda: sol_balance_before > operator.get_solana_balance())
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)
        assert len(validated_response.result.solanaTransactions) > 1
        assert_events_order(validated_response)

        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.ExitStop)
        assert_event_by_type(validated_response, NeonEventType.Return)
