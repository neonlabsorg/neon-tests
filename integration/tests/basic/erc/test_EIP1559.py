import typing as tp

import rlp
import allure
import pytest
import requests
import web3
import web3.types
from eth_account.signers.local import LocalAccount
from web3._utils.fee_utils import _fee_history_priority_fee_estimate  # noqa
from eth_utils import is_hex
from web3.contract import Contract
from web3.exceptions import TimeExhausted

from conftest import EnvName
from utils import helpers
from utils.apiclient import JsonRPCSession
from utils.models.fee_history_model import EthFeeHistoryResult
from utils.solana_client import SolanaClient
from utils.types import TransactionType
from utils.web3client import NeonChainWeb3Client, Web3Client
from utils.accounts import EthAccounts


TX_TIMEOUT = 10

NEGATIVE_PARAMETERS = (
    "max_priority_fee_per_gas, max_fee_per_gas, expected_exception, exception_message_regex",
    [
        (  # Zero values
            0,
            0,
            Exception,
            None,
        ),
        (  # Negative values
            -1000,
            -500,
            rlp.exceptions.ObjectSerializationError,
            r'Serialization failed because of field maxPriorityFeePerGas \("Cannot serialize negative integers"\)',
        ),
        (  # Large values (potential overflow)
            2 ** 256,
            2 ** 256,
            ValueError,
            "{'code': -32000, 'message': '.+'}",
        ),
        (  # Fractional values
            1.5,
            1.5,
            TypeError,
            "Transaction had invalid fields: {'maxPriorityFeePerGas': 1.5, 'maxFeePerGas': 1.5}",
        ),
        (  # Invalid types
            "invalid",
            "invalid",
            TypeError,
            "Transaction had invalid fields: {'maxPriorityFeePerGas': 'invalid', 'maxFeePerGas': 'invalid'}",
        ),
        (  # Mismatched values
            100000000000,
            50000000000,
            Exception,
            r"{'code': -32000, 'message': .*}",
        ),
        (  # Underpriced
            10000000000,
            5000000000,
            Exception,
            r"{'code': -32000, 'message': .*}",
        ),
        (  # Zero base fee
            0,
            1000000000,
            Exception,
            None
        ),
        (  # Missing max_priority_fee_per_gas
            None,
            1000000000,
            TypeError,
            r"Missing kwargs: \['maxPriorityFeePerGas'\]",
        ),
        (  # Missing max_fee_per_gas
            1000000000,
            None,
            TypeError,
            r"Missing kwargs: \['maxFeePerGas'\]",
        ),
    ]
)


def validate_transfer_positive(
        accounts: EthAccounts,
        web3_client: NeonChainWeb3Client,
        access_list: tp.Optional[list[web3.types.AccessListEntry]],
):
    sender = accounts[0]
    recipient = web3_client.create_account()

    balance_sender_before = web3_client.get_balance(sender.address)
    balance_recipient_before = web3_client.get_balance(recipient.address)

    latest_block: web3.types.BlockData = web3_client._web3.eth.get_block(block_identifier="latest")  # noqa
    base_fee_per_gas = latest_block.baseFeePerGas  # noqa
    max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee() or 20000  # noqa
    base_fee_multiplier = 1.1
    max_fee_per_gas = int((base_fee_multiplier * base_fee_per_gas) + max_priority_fee_per_gas)

    value = balance_sender_before // 2

    tx_params = web3_client.make_raw_tx_eip_1559(
        chain_id="auto",
        from_=sender.address,
        to=recipient.address,
        value=value,
        nonce="auto",
        gas="auto",
        max_priority_fee_per_gas=max_priority_fee_per_gas,
        max_fee_per_gas=max_fee_per_gas,
        base_fee_multiplier=base_fee_multiplier,
        data=None,
        access_list=access_list,
    )

    receipt = web3_client.send_transaction(account=sender, transaction=tx_params, timeout=15)
    assert receipt.type == 2

    balance_sender_after = web3_client.get_balance(sender.address)
    balance_recipient_after = web3_client.get_balance(recipient.address)
    estimated_gas = tx_params["gas"]
    block_gas_limit = latest_block["gasLimit"]
    gas_used = receipt["gasUsed"]
    effective_gas_price = receipt["effectiveGasPrice"]
    cumulative_gas_used = receipt["cumulativeGasUsed"]
    total_fee_paid = gas_used * effective_gas_price
    expected_balance_sender_after = balance_sender_before - value - total_fee_paid

    # Validate the base fee
    block = web3_client._web3.eth.get_block(receipt['blockNumber'])  # noqa
    assert abs(base_fee_per_gas * base_fee_multiplier - block['baseFeePerGas']) < 10

    # Validate the priority fee
    gas_price_actual_type_2 = receipt.effectiveGasPrice
    priority_fee_per_gas_actual = gas_price_actual_type_2 - block.baseFeePerGas
    assert priority_fee_per_gas_actual <= max_priority_fee_per_gas

    assert balance_sender_after == expected_balance_sender_after, (
        f"Expected sender balance: {expected_balance_sender_after}, "
        f"Actual sender balance: {balance_sender_after}"
    )
    assert balance_recipient_after == balance_recipient_before + value, (
        f"Expected recipient balance: {balance_recipient_before + value}, "
        f"Actual recipient balance: {balance_recipient_after}"
    )

    # Verify that the effective gas price does not exceed the max fee per gas
    assert effective_gas_price <= max_fee_per_gas, (
        f"Effective gas price: {effective_gas_price}, Max fee per gas: {max_fee_per_gas}"
    )

    # Validate gas used does not exceed the estimated gas
    assert gas_used <= estimated_gas, (
        f"Gas used: {gas_used}, Estimated gas: {estimated_gas}"
    )

    # Validate cumulative gas used does not exceed block gas limit
    assert cumulative_gas_used <= block_gas_limit, (
        f"Cumulative gas used: {cumulative_gas_used}, Block gas limit: {block_gas_limit}"
    )


def validate_deploy_positive(
        accounts: EthAccounts,
        web3_client: NeonChainWeb3Client,
        access_list: tp.Optional[list[web3.types.AccessListEntry]],
):
    account = accounts[0]
    balance_before = web3_client.get_balance(account.address)

    contract_iface = helpers.get_contract_interface(
        contract="common/Common.sol",
        version="0.8.12",
        contract_name="Common",
    )

    latest_block: web3.types.BlockData = web3_client._web3.eth.get_block(block_identifier="latest")  # noqa
    base_fee_per_gas = latest_block.baseFeePerGas  # noqa
    max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa
    max_fee_per_gas = (5 * base_fee_per_gas) + max_priority_fee_per_gas

    tx_params = web3_client.make_raw_tx_eip_1559(
        chain_id="auto",
        from_=account.address,
        to=None,
        value=0,
        nonce="auto",
        gas="auto",
        max_priority_fee_per_gas=max_priority_fee_per_gas,
        max_fee_per_gas=max_fee_per_gas,
        data=contract_iface["bin"],
        access_list=access_list,
    )

    receipt = web3_client.send_transaction(account=account, transaction=tx_params)
    assert receipt.type == 2
    contract = web3_client._web3.eth.contract(address=receipt["contractAddress"], abi=contract_iface["abi"])  # noqa

    assert contract.address == receipt["contractAddress"], "Contract deployment failed"

    balance_after = web3_client.get_balance(account.address)
    estimated_gas = tx_params["gas"]
    block_gas_limit = latest_block["gasLimit"]
    gas_used = receipt["gasUsed"]
    effective_gas_price = receipt["effectiveGasPrice"]
    cumulative_gas_used = receipt["cumulativeGasUsed"]
    total_fee_paid = gas_used * effective_gas_price

    # Validate that sender's balance decreased by at least the gas fee
    assert balance_before - balance_after >= total_fee_paid, "Sender balance did not decrease by gas fee"

    # Verify that the effective gas price does not exceed the max fee per gas
    assert effective_gas_price <= max_fee_per_gas, (
        f"Effective gas price: {effective_gas_price}, Max fee per gas: {max_fee_per_gas}"
    )

    # Validate gas used does not exceed the estimated gas
    assert gas_used <= estimated_gas, (
        f"Gas used: {gas_used}, Estimated gas: {estimated_gas}"
    )

    # Validate cumulative gas used does not exceed block gas limit
    assert cumulative_gas_used <= block_gas_limit, (
        f"Cumulative gas used: {cumulative_gas_used}, Block gas limit: {block_gas_limit}"
    )


@allure.feature("EIP Verifications")
@allure.story("EIP-1559: New Transaction Type Support in Neon")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestSendRawTransaction:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    def test_transfer_positive(self):
        validate_transfer_positive(
            accounts=self.accounts,
            web3_client=self.web3_client,
            access_list=None,
        )

    @pytest.mark.neon_only
    def test_transfer_invalid_chain_id_negative(
            self,
            json_rpc_client: JsonRPCSession,
    ):
        sender = self.accounts[0]
        recipient = self.web3_client.create_account()

        tx_params = self.web3_client.make_raw_tx_eip_1559(
            chain_id=None,
            from_=sender.address,
            to=recipient.address,
            value=10000,
            nonce="auto",
            gas="auto",
            max_priority_fee_per_gas="auto",
            max_fee_per_gas="auto",
            data=None,
            access_list=None,
        )

        # sign_transaction automatically sets chainId to 0
        signed_tx = self.web3_client._web3.eth.account.sign_transaction(tx_params, sender.key)
        response = json_rpc_client.send_rpc(method="eth_sendRawTransaction", params=signed_tx.rawTransaction.hex())
        assert "result" not in response
        assert "error" in response
        assert response["error"]["code"] == -32000

    def test_deploy_positive(self):
        validate_deploy_positive(
            accounts=self.accounts,
            web3_client=self.web3_client,
            access_list=None,
        )

    def test_contract_function_call_positive(
            self,
    ):
        account = self.accounts[0]
        contract_a, _ = self.web3_client.deploy_and_get_contract(
            contract="EIPs/EIP161/contract_a_function.sol",
            version="0.8.12",
            account=account,
            contract_name="ContractA",
        )

        tx_params = contract_a.functions.deploy_contract().build_transaction()
        tx_params["nonce"] = self.web3_client.get_nonce(account)

        tx_receipt = self.web3_client.send_transaction(
            account=account,
            transaction=tx_params,
        )

        assert tx_receipt.type == 2
        assert tx_receipt.status == 1, "ContractB was not deployed"
        assert tx_receipt.logs, "ContractB was not deployed"
        contract_b_address = tx_receipt.logs[0].address

        contract_a_nonce = self.web3_client.get_nonce(contract_a.address)
        assert contract_a_nonce == 2

        contract_b: Contract = self.web3_client.get_deployed_contract(
            address=contract_b_address,
            contract_file="EIPs/EIP161/contract_b.sol",
            contract_name="ContractB",
        )

        data = contract_b.functions.getOne().build_transaction()["data"]
        tx_params = self.web3_client.make_raw_tx_eip_1559(
            chain_id="auto",
            from_=account.address,
            to=contract_b.address,
            value=0,
            nonce="auto",
            gas="auto",
            max_priority_fee_per_gas="auto",
            max_fee_per_gas="auto",
            data=data,
            access_list=None,
        )

        tx_receipt = self.web3_client.send_transaction(account, tx_params)
        assert tx_receipt.type == 2
        result = int(tx_receipt.logs[0].topics[1].hex(), 16)
        assert result == 1

    @pytest.mark.parametrize(*NEGATIVE_PARAMETERS)
    def test_transfer_negative(
            self,
            max_priority_fee_per_gas,
            max_fee_per_gas,
            expected_exception,
            exception_message_regex,
    ):
        sender = self.accounts[0]
        recipient = self.web3_client.create_account()
        value = 1

        tx_params = self.web3_client.make_raw_tx_eip_1559(
            chain_id="auto",
            from_=sender.address,
            to=recipient.address,
            value=value,
            nonce="auto",
            gas="auto",
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            max_fee_per_gas=max_fee_per_gas,
            data=None,
            access_list=None,
        )

        with pytest.raises(expected_exception=expected_exception, match=exception_message_regex):
            self.web3_client.send_transaction(
                account=sender,
                transaction=tx_params,
                timeout=TX_TIMEOUT,
            )

    @pytest.mark.parametrize(*NEGATIVE_PARAMETERS)
    def test_deploy_negative(
            self,
            max_priority_fee_per_gas,
            max_fee_per_gas,
            expected_exception,
            exception_message_regex,
    ):
        account = self.accounts[0]

        contract_iface = helpers.get_contract_interface(
            contract="common/Common.sol",
            version="0.8.12",
            contract_name="Common",
        )

        tx_params = self.web3_client.make_raw_tx_eip_1559(
            chain_id="auto",
            from_=account.address,
            to=None,
            value=0,
            nonce="auto",
            gas="auto",
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            max_fee_per_gas=max_fee_per_gas,
            data=contract_iface["bin"],
            access_list=None,
        )

        with pytest.raises(expected_exception=expected_exception, match=exception_message_regex):
            self.web3_client.send_transaction(
                account=account,
                transaction=tx_params,
                timeout=TX_TIMEOUT,
            )

    def test_insufficient_funds(
            self,
    ):
        sender = self.accounts[0]
        balance = self.web3_client.get_balance(sender.address)
        recipient = self.web3_client.create_account()

        tx_params = self.web3_client.make_raw_tx_eip_1559(
            chain_id="auto",
            from_=sender.address,
            to=recipient.address,
            value=balance,
            nonce="auto",
            gas="auto",
            max_priority_fee_per_gas="auto",
            max_fee_per_gas="auto",
            data=None,
            access_list=None,
        )

        error_msg_regex = r"{'code': -32000, 'message': '.+'}"
        with pytest.raises(expected_exception=ValueError, match=error_msg_regex):
            self.web3_client.send_transaction(account=sender, transaction=tx_params)

    def test_too_low_fee(
            self,
    ):
        sender = self.accounts[0]
        recipient = self.web3_client.create_account()

        base_fee_per_gas = self.web3_client.base_fee_per_gas()

        tx_params = self.web3_client.make_raw_tx_eip_1559(
            chain_id="auto",
            from_=sender.address,
            to=recipient.address,
            value=1000,
            nonce="auto",
            gas="auto",
            max_priority_fee_per_gas=0,
            max_fee_per_gas=base_fee_per_gas - 1,
            data=None,
            access_list=None,
        )

        error_msg_regex = rf".+ not in the chain after {TX_TIMEOUT} seconds"
        with pytest.raises(expected_exception=TimeExhausted, match=error_msg_regex):
            self.web3_client.send_transaction(account=sender, transaction=tx_params, timeout=TX_TIMEOUT)


@allure.feature("EIP Verifications")
@allure.story("EIP-1559: Verify JSON-RPC method eth_maxPriorityFeePerGas")
@pytest.mark.usefixtures("eip1559_setup")
class TestRpcMaxPriorityFeePerGas:

    @pytest.mark.need_eip1559_blocks(10)
    def test_positive(
            self,
            json_rpc_client: JsonRPCSession,
            web3_client: NeonChainWeb3Client,
    ):

        response = json_rpc_client.send_rpc(method="eth_maxPriorityFeePerGas")
        assert "error" not in response, response["error"]
        max_fee_per_gas = int(response["result"], 16)

        fee_history: web3.types.FeeHistory = web3_client._web3.eth.fee_history(10, "pending", [5])
        estimated_max_fee_per_gas = _fee_history_priority_fee_estimate(fee_history=fee_history)
        assert abs(max_fee_per_gas - estimated_max_fee_per_gas) <= 2000000000


@allure.feature("EIP Verifications")
@allure.story("EIP-1559: Verify JSON-RPC method eth_feeHistory")
@pytest.mark.usefixtures("eip1559_setup")
@pytest.mark.neon_only
class TestRpcFeeHistory:
    """
    eth_feeHistory

    parameters:
        - blockCount
        - newestBlock
        - rewardPercentiles

    response:
       - oldestBlock: Lowest number block of the returned range expressed as a hexadecimal number.
       - baseFeePerGas: An array of block base fees per gas, including an extra block value.
         The extra value is the next block after the newest block in the returned range.
         Returns zeroes for blocks created before EIP-1559.
       - gasUsedRatio: An array of block gas used ratios. These are calculated as the ratio of gasUsed and gasLimit.
       - reward: An array of effective priority fee per gas data points from a single block.
         All zeroes are returned if the block is empty.
    """

    @pytest.fixture(scope="class")
    def first_block_number(
            self,
            web3_client: NeonChainWeb3Client,
    ) -> int:
        block = web3_client._web3.eth.get_block(block_identifier="earliest")
        return block.number

    @pytest.mark.need_eip1559_blocks(1)
    def test_positive_first_block(
            self,
            json_rpc_client: JsonRPCSession,
            first_block_number: int,
    ):
        block_count = 20
        newest_block = first_block_number
        reward_percentiles = [10, 50, 90]

        response = json_rpc_client.send_rpc(
            method="eth_feeHistory",
            params=[
                hex(block_count),
                hex(newest_block),
                reward_percentiles
            ]
        )

        assert "error" not in response, response["error"]
        fee_history = EthFeeHistoryResult(**response["result"])

        assert len(fee_history.baseFeePerGas) == 2
        assert len(fee_history.gasUsedRatio) == 1
        assert int(fee_history.oldestBlock, 16) == newest_block
        assert len(fee_history.reward) == 1

        for block in fee_history.reward:
            assert len(block) == len(reward_percentiles)
            for tx_reward in block:
                reward = int(tx_reward, 16)
                assert reward >= 0

    @pytest.mark.neon_only
    def test_positive_zero_block_count(
            self,
            json_rpc_client: JsonRPCSession,
    ):
        block_count = 0
        newest_block = "latest"
        reward_percentiles = [25, 50, 75]

        response = json_rpc_client.send_rpc(
            method="eth_feeHistory",
            params=[
                hex(block_count),
                newest_block,
                reward_percentiles
            ]
        )

        assert "error" not in response, response["error"]
        fee_history = EthFeeHistoryResult(**response["result"])

        assert len(fee_history.baseFeePerGas) == 1
        assert int(fee_history.baseFeePerGas[0], 16) > 0

        assert fee_history.gasUsedRatio == []
        assert int(fee_history.oldestBlock, 16) == 0
        assert fee_history.reward == []

    @pytest.mark.neon_only
    @pytest.mark.need_eip1559_blocks(3)
    @pytest.mark.parametrize("reward_percentiles", ([], [50]))
    def test_positive_fewer_blocks_than_count(
            self,
            json_rpc_client: JsonRPCSession,
            first_block_number: int,
            reward_percentiles: list[int]
    ):
        expected_block_count = 3
        newest_block = first_block_number + expected_block_count - 1
        block_count = first_block_number + expected_block_count - 1 + 10

        response = json_rpc_client.send_rpc(
            method="eth_feeHistory",
            params=[
                hex(block_count),
                hex(newest_block),
                reward_percentiles
            ]
        )

        assert "error" not in response, response["error"]
        fee_history = EthFeeHistoryResult(**response["result"])

        assert len(fee_history.baseFeePerGas) == expected_block_count + 1, fee_history.baseFeePerGas
        assert len(fee_history.gasUsedRatio) == expected_block_count, fee_history.gasUsedRatio

        oldest_block = int(fee_history.oldestBlock, 16)
        assert oldest_block == first_block_number, oldest_block

        if not reward_percentiles:
            assert fee_history.reward is None, fee_history.reward
        else:
            assert len(fee_history.reward) == expected_block_count

    @pytest.mark.need_eip1559_blocks(1)
    def test_positive_earliest_block(
            self,
            json_rpc_client: JsonRPCSession,
            first_block_number: int,
    ):
        block_count = 1
        newest_block = "earliest"
        reward_percentiles = [50]

        response = json_rpc_client.send_rpc(
            method="eth_feeHistory",
            params=[
                hex(block_count),
                newest_block,
                reward_percentiles
            ]
        )

        assert "error" not in response, response["error"]
        fee_history = EthFeeHistoryResult(**response["result"])

        assert len(fee_history.baseFeePerGas) == 2, fee_history.baseFeePerGas
        assert len(fee_history.gasUsedRatio) == 1, fee_history.gasUsedRatio
        oldest_block = int(fee_history.oldestBlock, 16)
        assert oldest_block == first_block_number, oldest_block
        assert len(fee_history.reward) == 1, fee_history.reward

        for block in fee_history.reward:
            assert len(block) == len(reward_percentiles)
            for tx_reward in block:
                reward = int(tx_reward, 16)
                assert reward >= 0

    @pytest.mark.need_eip1559_blocks(10)
    def test_positive_pending_block(
            self,
            json_rpc_client: JsonRPCSession,
            web3_client: NeonChainWeb3Client,
    ):
        block_count = 10
        newest_block = "pending"
        reward_percentiles = [5]

        response = json_rpc_client.send_rpc(
            method="eth_feeHistory",
            params=[
                hex(block_count),
                newest_block,
                reward_percentiles
            ]
        )

        assert "error" not in response, response["error"]
        fee_history = EthFeeHistoryResult(**response["result"])

        assert len(fee_history.baseFeePerGas) <= block_count + 1
        for base_fee_per_gas in fee_history.baseFeePerGas:
            assert int(base_fee_per_gas, 16) > 0

        assert len(fee_history.gasUsedRatio) == block_count
        for gas_used_ratio in fee_history.gasUsedRatio:
            assert gas_used_ratio >= 0

        oldest_block_actual = int(fee_history.oldestBlock, 16)
        oldest_block_expected = web3_client._web3.eth.get_block(block_identifier="pending")["number"] - block_count
        assert oldest_block_actual - oldest_block_expected <= 1  # a new block may be added since feeHistory request

        assert len(fee_history.reward) == block_count
        if fee_history.reward is not None:
            for block in fee_history.reward:
                for tx_reward in block:
                    reward = int(tx_reward, 16)
                    assert reward >= 0

    @pytest.mark.need_eip1559_blocks(10)
    @pytest.mark.parametrize("block_count", [1024, 1025])
    def test_positive_max_blocks(
            self,
            json_rpc_client: JsonRPCSession,
            web3_client: NeonChainWeb3Client,
            first_block_number: int,
            block_count: int,
    ):
        newest_block = "latest"
        reward_percentiles = [5, 25, 50, 75, 90]
        last_block_number = web3_client._web3.eth.get_block(block_identifier="latest")["number"]
        blocks_in_chain = last_block_number - first_block_number + 1
        expected_block_count = min(1024, blocks_in_chain)

        response = json_rpc_client.send_rpc(
            method="eth_feeHistory",
            params=[
                hex(block_count),
                newest_block,
                reward_percentiles
            ]
        )

        assert "error" not in response, response["error"]
        fee_history = EthFeeHistoryResult(**response["result"])

        oldest_block_actual = int(fee_history.oldestBlock, 16)
        oldest_block_expected = last_block_number - expected_block_count
        assert 0 <= oldest_block_actual - oldest_block_expected <= 2  # a few new blocks may be added

        assert 0 <= len(fee_history.baseFeePerGas) - (expected_block_count + 1) <= 2
        for base_fee_per_gas in fee_history.baseFeePerGas:
            assert int(base_fee_per_gas, 16) > 0

        assert len(fee_history.gasUsedRatio) == expected_block_count
        for gas_used_ratio in fee_history.gasUsedRatio:
            assert gas_used_ratio >= 0

        assert fee_history.reward is not None
        assert len(fee_history.reward) == expected_block_count

        for block in fee_history.reward:
            assert len(block) == len(reward_percentiles)
            for tx_reward in block:
                reward = int(tx_reward, 16)
                assert reward >= 0

    @pytest.mark.parametrize(
        argnames=("block_count", "newest_block", "reward_percentiles", "error_code"),
        argvalues=(
                (1, "unknown", [], -32602),  # Invalid newest block
                (100, "latest", [90, 50, 10], -32000),  # Non-monotonic reward percentiles
        ),
    )
    def test_negative_cases(
            self,
            json_rpc_client: JsonRPCSession,
            block_count: int,
            newest_block: str,
            reward_percentiles: list[int],
            error_code: int,
    ):
        response = json_rpc_client.send_rpc(
            method="eth_feeHistory",
            params=[
                hex(block_count),
                newest_block,
                reward_percentiles
            ]
        )
        assert "result" not in response, response["result"]
        assert "error" in response
        assert response["error"]["code"] == error_code


@allure.feature("EIP Verifications")
@allure.story("EIP-1559: Verify new fields in neon_ JSON-RPC methods")
@pytest.mark.neon_only
class TestRpcNeonMethods:

    def test_neon_get_transaction_by_sender_nonce(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,
    ):
        sender = accounts[0]
        recipient = accounts[1]
        nonce = web3_client.get_nonce(address=sender.address)
        base_fee_per_gas = web3_client.base_fee_per_gas()
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa
        max_fee_per_gas = (5 * base_fee_per_gas) + max_priority_fee_per_gas

        web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

        response = json_rpc_client.send_rpc(
            method="neon_getTransactionBySenderNonce", params=[sender.address, nonce]
        )

        assert "error" not in response, response["error"]
        max_priority_fee_per_gas_response = response["result"].get("maxPriorityFeePerGas")
        assert max_priority_fee_per_gas_response is not None
        assert int(max_priority_fee_per_gas_response, 16) == max_priority_fee_per_gas

        max_fee_per_gas_response = response["result"].get("maxFeePerGas")
        assert max_fee_per_gas is not None
        assert int(max_fee_per_gas_response, 16) == max_fee_per_gas

    def test_neon_get_solana_transaction_by_neon_transaction(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,
    ):
        sender = accounts[0]
        recipient = accounts[1]

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
        )
        params = [receipt.transactionHash.hex()]
        response = json_rpc_client.send_rpc(method="neon_getSolanaTransactionByNeonTransaction", params=params)

        assert "error" not in response, response["error"]
        hash_solana = response["result"]
        assert hash_solana

    def test_neon_get_transaction_receipt(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,
    ):
        sender = accounts[0]
        recipient = accounts[1]

        base_fee_per_gas = web3_client.base_fee_per_gas()
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa
        max_fee_per_gas = (5 * base_fee_per_gas) + max_priority_fee_per_gas

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            max_fee_per_gas=max_fee_per_gas,
        )

        params = [receipt.transactionHash.hex()]
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=params)

        assert "error" not in response, response["error"]

        actual_effective_gas_price = int(response["result"].get("effectiveGasPrice"), 16)
        assert actual_effective_gas_price >= base_fee_per_gas
        assert actual_effective_gas_price <= max_fee_per_gas


@allure.feature("EIP Verifications")
@allure.story("EIP-1559: Verify new fields in eth_ JSON-RPC methods")
@pytest.mark.neon_only
class TestRpcEthMethods:
    def test_get_transaction_by_hash(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,

    ):
        sender = accounts[0]
        recipient = web3_client.create_account()

        base_fee_per_gas = web3_client.base_fee_per_gas()
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa
        max_fee_per_gas = (5 * base_fee_per_gas) + max_priority_fee_per_gas

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
        response = json_rpc_client.send_rpc(
            method="eth_getTransactionByHash",
            params=[receipt.transactionHash.hex()],
        )

        assert "error" not in response, response["error"]
        result = response.get("result")
        assert result is not None
        assert int(result['maxFeePerGas'], 16) == max_fee_per_gas
        assert int(result['maxPriorityFeePerGas'], 16) == max_priority_fee_per_gas

    def test_get_transaction_by_block_hash_and_index(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,

    ):
        sender = accounts[0]
        recipient = web3_client.create_account()

        base_fee_per_gas = web3_client.base_fee_per_gas()
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa
        max_fee_per_gas = (5 * base_fee_per_gas) + max_priority_fee_per_gas

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
        transaction_index = hex(receipt.transactionIndex)
        response = json_rpc_client.send_rpc(
            method="eth_getTransactionByBlockHashAndIndex",
            params=[receipt.blockHash.hex(), transaction_index],
        )

        assert "error" not in response, response["error"]
        result = response.get("result")
        assert result is not None
        assert int(result['maxFeePerGas'], 16) == max_fee_per_gas
        assert int(result['maxPriorityFeePerGas'], 16) == max_priority_fee_per_gas

    def test_get_transaction_by_block_number_and_index(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,
    ):
        sender = accounts[0]
        recipient = web3_client.create_account()

        base_fee_per_gas = web3_client.base_fee_per_gas()
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa
        max_fee_per_gas = (5 * base_fee_per_gas) + max_priority_fee_per_gas

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
        block_number = hex(receipt.blockNumber)
        index = hex(receipt.transactionIndex)
        response = json_rpc_client.send_rpc(
            method="eth_getTransactionByBlockNumberAndIndex",
            params=[block_number, index],
        )

        assert "error" not in response, response["error"]
        result = response.get("result")
        assert result is not None
        assert int(result['maxFeePerGas'], 16) == max_fee_per_gas
        assert int(result['maxPriorityFeePerGas'], 16) == max_priority_fee_per_gas

    @pytest.mark.neon_only
    @pytest.mark.parametrize(
        argnames="full_transaction_objects",
        argvalues=(True, False),
    )
    def test_get_block_by_hash(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,
            full_transaction_objects: bool,
    ):
        sender = accounts[0]
        recipient = web3_client.create_account()

        base_fee_from_history = web3_client.base_fee_per_gas()
        base_fee_per_gas = base_fee_from_history * 2
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa
        max_fee_per_gas = base_fee_per_gas + max_priority_fee_per_gas

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
        block_hash = receipt.blockHash.hex()
        response = json_rpc_client.send_rpc(
            method="eth_getBlockByHash",
            params=[block_hash, full_transaction_objects],
        )

        assert "error" not in response, response["error"]
        result = response.get("result")
        assert result is not None

        block_base_fee = int(result['baseFeePerGas'], 16)
        assert block_base_fee == base_fee_per_gas

    @pytest.mark.neon_only
    @pytest.mark.parametrize(
        argnames="full_transaction_objects",
        argvalues=(True, False),
    )
    def test_get_block_by_number(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            json_rpc_client: JsonRPCSession,
            full_transaction_objects: bool,
    ):
        sender = accounts[0]
        recipient = web3_client.create_account()

        base_fee_from_history = web3_client.base_fee_per_gas()
        base_fee_per_gas = base_fee_from_history * 2
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            max_fee_per_gas=base_fee_per_gas + max_priority_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
        block_number = hex(receipt.blockNumber)
        response = json_rpc_client.send_rpc(
            method="eth_getBlockByNumber",
            params=[block_number, full_transaction_objects],
        )

        assert "error" not in response, response["error"]
        result = response.get("result")
        assert result is not None

        block_base_fee = int(result['baseFeePerGas'], 16)

        assert block_base_fee == base_fee_per_gas

    def test_get_transaction_receipt(
            self,
            accounts: EthAccounts,
            web3_client: NeonChainWeb3Client,
            env_name: EnvName,
    ):
        sender = accounts[0]
        recipient = web3_client.create_account()

        base_fee_per_gas = web3_client.base_fee_per_gas()
        max_priority_fee_per_gas = web3_client._web3.eth._max_priority_fee()  # noqa
        max_fee_per_gas = 2 * base_fee_per_gas + max_priority_fee_per_gas

        receipt = web3_client.send_tokens_eip_1559(
            from_=sender,
            to=recipient.address,
            value=100,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

        actual_effective_gas_price = receipt.effectiveGasPrice
        if env_name is EnvName.GETH:
            expected_effective_gas_price = min(max_fee_per_gas, base_fee_per_gas + max_priority_fee_per_gas)
        else:
            expected_effective_gas_price = max_fee_per_gas
        assert actual_effective_gas_price == expected_effective_gas_price


@allure.feature("EIP Verifications")
@allure.story("EIP-1559: Verify accessList does not break transactions")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestAccessList:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.fixture(scope="class")
    def access_list(self) -> list[web3.types.AccessListEntry]:
        return [
            web3.types.AccessListEntry(
                address=web3.types.HexStr("0x0000000000000000000000000000000000000000"),
                storageKeys=[
                    web3.types.HexStr("0x0000000000000000000000000000000000000000000000000000000000000000"),
                    web3.types.HexStr("0x0000000000000000000000000000000000000000000000000000000000000001"),
                    web3.types.HexStr("0x0000000000000000000000000000000000000000000000000000000000000002"),
                ]
            ),
            web3.types.AccessListEntry(
                address=web3.types.HexStr("0x0000000000000000000000000000000000000001"),
                storageKeys=[
                    web3.types.HexStr("0x0000000000000000000000000000000000000000000000000000000000000000"),
                    web3.types.HexStr("0x0000000000000000000000000000000000000000000000000000000000000001"),
                    web3.types.HexStr("0x0000000000000000000000000000000000000000000000000000000000000002"),
                ]
            ),
        ]

    def test_transfer(
            self,
            access_list: list[web3.types.AccessListEntry],
    ):
        validate_transfer_positive(
            accounts=self.accounts,
            web3_client=self.web3_client,
            access_list=access_list,
        )

    def test_deploy(
            self,
            access_list: list[web3.types.AccessListEntry],
    ):
        validate_deploy_positive(
            accounts=self.accounts,
            web3_client=self.web3_client,
            access_list=access_list,
        )


@allure.feature("EIP Verifications")
@allure.story("EIP-1559: multiple tokens")
@pytest.mark.neon_only
class TestMultipleTokens:

    @pytest.mark.multipletokens
    def test_transfer_positive(
            self,
            web3_client: NeonChainWeb3Client,
            web3_client_sol: Web3Client,
            sol_client: SolanaClient,  # noqa
            account_with_all_tokens: LocalAccount,
            class_account_sol_chain: LocalAccount,
    ):
        alice_neon_balance_before = web3_client.get_balance(account_with_all_tokens)
        bob_neon_balance_before = web3_client.get_balance(class_account_sol_chain)
        alice_sol_balance_before = web3_client_sol.get_balance(account_with_all_tokens)
        bob_sol_balance_before = web3_client_sol.get_balance(class_account_sol_chain)

        value = 1000
        receipt = web3_client_sol.send_tokens(
            from_=class_account_sol_chain,
            to=account_with_all_tokens,
            value=value,
            tx_type=TransactionType.EIP_1559,
        )

        assert receipt["status"] == 1

        # Make sure SOL balances changed
        bob_sol_balance_after = web3_client_sol.get_balance(class_account_sol_chain)
        alice_sol_balance_after = web3_client_sol.get_balance(account_with_all_tokens)
        assert alice_sol_balance_after == alice_sol_balance_before + value
        assert bob_sol_balance_after < bob_sol_balance_before - value

        # Make sure NEON balances did not change
        alice_neon_balance_after = web3_client.get_balance(account_with_all_tokens)
        bob_neon_balance_after = web3_client.get_balance(class_account_sol_chain)
        assert alice_neon_balance_after == alice_neon_balance_before
        assert bob_neon_balance_after == bob_neon_balance_before
