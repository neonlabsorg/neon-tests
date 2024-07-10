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
from utils.models.result import NeonGetTransactionResult
from utils.web3client import NeonChainWeb3Client


@allure.feature("JSON-RPC validation")
@allure.story("Verify events")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestNeonEventType:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_log(self, json_rpc_client, event_caller_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = event_caller_contract.functions.nonArgs().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)

        events_counter = count_events(validated_response)
        assert events_counter == Counter({"EnterCall": 1, "ExitStop": 1, "Return": 1, "Log": 1})
        assert_event_field(validated_response, NeonEventType.Log, "address", validated_response.result.to)
        assert_event_by_type(validated_response, NeonEventType.Log)
        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.ExitStop)
        assert_event_by_type(validated_response, NeonEventType.Return)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_enter_call(self, json_rpc_client, event_caller_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = event_caller_contract.functions.nonArgs().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)

        events_counter = count_events(validated_response)
        assert events_counter == Counter({"EnterCall": 1, "ExitStop": 1, "Return": 1, "Log": 1})
        assert_event_field(validated_response, NeonEventType.EnterCall, "address", validated_response.result.to)
        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.ExitStop)
        assert_event_by_type(validated_response, NeonEventType.Return)
        assert_event_by_type(validated_response, NeonEventType.Log)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_enter_call_code(self, json_rpc_client, opcodes_checker):
        # Will be depricated in the future https://eips.ethereum.org/EIPS/eip-2488
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = opcodes_checker.functions.test_callcode().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)

        events_counter = count_events(validated_response)
        assert events_counter == Counter(
            {"EnterCall": 1, "ExitStop": 1, "Return": 1, "EnterCallCode": 1, "ExitReturn": 1}
        )
        assert_events_order(validated_response)
        assert_event_by_type(validated_response, NeonEventType.EnterCallCode)
        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.ExitReturn)
        assert_event_by_type(validated_response, NeonEventType.ExitStop)
        assert_event_by_type(validated_response, NeonEventType.Return)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_enter_static_call(self, json_rpc_client, tracer_caller_contract, tracer_callee_contract_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = tracer_caller_contract.functions.emitEventAndGetBalanceOfContractCalleeWithEvents(
            tracer_callee_contract_address
        ).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.send_rpc(
            method="neon_getTransactionReceipt", params=[receipt["transactionHash"].hex()]
        )
        validated_response = NeonGetTransactionResult(**response)
        assert count_events(validated_response) == Counter(
            {"EnterCall": 2, "ExitStop": 1, "Return": 1, "Log": 2, "EnterStaticCall": 1, "ExitReturn": 2}
        )
        assert_events_order(validated_response)
        assert_event_by_type(validated_response, NeonEventType.EnterStaticCall)
        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.ExitReturn)
        assert_event_by_type(validated_response, NeonEventType.ExitStop)
        assert_event_by_type(validated_response, NeonEventType.Return)
        assert_event_by_type(validated_response, NeonEventType.Log)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_enter_delegate_call(self, json_rpc_client, tracer_caller_contract, tracer_callee_contract_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = tracer_caller_contract.functions.setParamWithDelegateCall(
            tracer_callee_contract_address, 9
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)
        assert count_events(validated_response) == Counter(
            {"EnterCall": 1, "ExitStop": 2, "Return": 1, "EnterDelegateCall": 1}
        )
        assert_events_order(validated_response)
        assert_event_by_type(validated_response, NeonEventType.EnterDelegateCall)
        assert_event_field(
            validated_response, NeonEventType.EnterDelegateCall, "address", validated_response.result.to, "!="
        )
        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.ExitStop)
        assert_event_by_type(validated_response, NeonEventType.Return)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_enter_create(self, json_rpc_client, recursion_factory):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = recursion_factory.functions.deployFirstContractViaCreate().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)
        assert count_events(validated_response) == Counter(
            {"EnterCall": 4, "ExitStop": 3, "Return": 1, "EnterCreate": 3, "ExitReturn": 4, "Log": 3}
        )
        assert_events_order(validated_response)
        assert_event_by_type(validated_response, NeonEventType.EnterCreate)
        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.ExitStop)
        assert_event_by_type(validated_response, NeonEventType.ExitReturn)
        assert_event_by_type(validated_response, NeonEventType.Return)
        assert_event_by_type(validated_response, NeonEventType.Log)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_enter_create_2(self, json_rpc_client, tracer_caller_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = tracer_caller_contract.functions.callTypeCreate2().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)
        assert_events_order(validated_response)
        # There is no EnterCreate2 event for now. Expecting EnterCreate.
        assert count_events(validated_response) == Counter(
            {"EnterCall": 1, "Return": 1, "EnterCreate": 1, "ExitReturn": 2}
        )
        assert_events_order(validated_response)
        assert_event_by_type(validated_response, NeonEventType.EnterCreate)
        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.ExitReturn)
        assert_event_by_type(validated_response, NeonEventType.Return)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_exit_stop(self, json_rpc_client):
        sender_account, receiver_account = self.accounts[0], self.accounts[1]
        tx = self.web3_client.make_raw_tx(sender_account, receiver_account, 1000, estimate_gas=True)
        resp = self.web3_client.send_transaction(sender_account, tx)

        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)
        events_counter = count_events(validated_response)
        assert events_counter == Counter({"EnterCall": 1, "ExitStop": 1, "Return": 1})
        assert_events_order(validated_response)
        assert_event_by_type(validated_response, NeonEventType.ExitStop)
        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.Return)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_exit_return(self, json_rpc_client, opcodes_checker):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = opcodes_checker.functions.test_callcode().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)

        events_counter = count_events(validated_response)
        assert events_counter == Counter(
            {"EnterCall": 1, "ExitStop": 1, "Return": 1, "EnterCallCode": 1, "ExitReturn": 1}
        )
        assert_events_order(validated_response)
        assert_event_by_type(validated_response, NeonEventType.ExitReturn)
        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.ExitStop)
        assert_event_by_type(validated_response, NeonEventType.Return)
        assert_event_by_type(validated_response, NeonEventType.EnterCallCode)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_exit_self_destruct(self, json_rpc_client, destroyable_contract):
        # SELFDESTRUCT by changing it to SENDALL https://eips.ethereum.org/EIPS/eip-4758
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = destroyable_contract.functions.destroy(sender_account.address).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)

        events_counter = count_events(validated_response)
        assert events_counter == Counter({"EnterCall": 1, "ExitSendAll": 1, "Return": 1})
        assert_events_order(validated_response)
        assert_event_by_type(validated_response, NeonEventType.ExitSendAll)
        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.Return)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_exit_revert_predefined(self, json_rpc_client, revert_contract_caller):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, gas=10000000)
        instruction_tx = revert_contract_caller.functions.doStringBasedRevert().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)
        assert count_events(validated_response, is_removed=True) == Counter(
            {"EnterCall": 1, "ExitRevert": 2, "EnterStaticCall": 1}
        )
        assert_events_order(validated_response)
        assert_event_by_type(validated_response, NeonEventType.ExitRevert)
        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.Return)
        assert_event_by_type(validated_response, NeonEventType.EnterStaticCall)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_exit_revert_trivial(self, json_rpc_client, revert_contract_caller):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, gas=10000000)
        instruction_tx = revert_contract_caller.functions.doTrivialRevert().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)
        assert count_events(validated_response, is_removed=True) == Counter(
            {"ExitRevert": 2, "EnterCall": 1, "EnterStaticCall": 1}
        )
        assert_events_order(validated_response)
        assert_event_by_type(validated_response, NeonEventType.Return)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_exit_revert_custom_error(self, json_rpc_client, revert_contract_caller):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, gas=10000000)
        instruction_tx = revert_contract_caller.functions.doCustomErrorRevert(1, 2).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)
        assert count_events(validated_response) == Counter({"Return": 1})
        assert_events_order(validated_response)
        assert_event_by_type(validated_response, NeonEventType.Return)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_exit_send_all(self, json_rpc_client, destroyable_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = destroyable_contract.functions.destroy(sender_account.address).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)

        events_counter = count_events(validated_response)
        assert events_counter == Counter({"EnterCall": 1, "ExitSendAll": 1, "Return": 1})
        assert_events_order(validated_response)
        assert_event_by_type(validated_response, NeonEventType.ExitSendAll)
        assert_event_by_type(validated_response, NeonEventType.EnterCall)
        assert_event_by_type(validated_response, NeonEventType.Return)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_return(self, json_rpc_client, common_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = common_contract.functions.getText().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)

        events_counter = count_events(validated_response)
        assert events_counter == Counter({"EnterCall": 1, "ExitReturn": 1, "Return": 1})
        assert_events_order(validated_response)
        assert_event_by_type(validated_response, NeonEventType.Return)
        assert_event_by_type(validated_response, NeonEventType.ExitReturn)
        assert_event_by_type(validated_response, NeonEventType.EnterCall)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_event_cancel(self, json_rpc_client, expected_error_checker):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = expected_error_checker.functions.method1().build_transaction(tx)
        try:
            resp = self.web3_client.send_transaction(sender_account, instruction_tx)
            assert resp["status"] == 0
        except ValueError as exc:
            assert "Error: memory allocation failed, out of memory." in exc.args[0]["message"]
        finally:
            response = json_rpc_client.send_rpc(
                method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()]
            )
            validated_response = NeonGetTransactionResult(**response)
            assert count_events(validated_response) == Counter({"Cancel": 1})
            assert_events_order(validated_response)
            assert_event_by_type(validated_response, NeonEventType.Cancel)
            assert_event_by_type(validated_response, NeonEventType.EnterCall)
            assert_event_by_type(validated_response, NeonEventType.ExitStop)
