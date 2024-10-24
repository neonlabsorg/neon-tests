import typing as tp

import pytest
from web3 import Web3

import allure
from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.basic import Tag
from integration.tests.basic.helpers.errors import Error32602
from utils.accounts import EthAccounts
from utils.helpers import gen_hash_of_block
from utils.models.error import EthError32602
from utils.models.result import EthResult
from utils.web3client import NeonChainWeb3Client


@allure.feature("JSON-RPC validation")
@allure.story("Verify getBlockTransaction methods")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestRpcGetBlockTransaction:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.parametrize("param", [32, 16, None])
    @pytest.mark.bug  # fails on geth (returns a different error message), needs a fix, and refactor of the test
    def test_eth_get_block_transaction_count_by_hash_negative(self, param: tp.Union[int, None], json_rpc_client):
        response = json_rpc_client.send_rpc(
            method="eth_getBlockTransactionCountByHash",
            params=gen_hash_of_block(param) if param else param,
        )

        if param is pow(2, 5):
            assert "error" not in response
            assert "result" in response and response["result"] == "0x0", f"Invalid response: {response['result']}"
            return
        EthError32602(**response)
        assert "error" in response, "error field not in response"
        assert "code" in response["error"]
        assert "message" in response["error"], "message field not in response"
        code = response["error"]["code"]
        message = response["error"]["message"]

        assert code == Error32602.CODE, "wrong code"
        assert Error32602.INVALID_BLOCKHASH in message, "wrong message"

    @pytest.mark.mainnet
    def test_eth_get_block_transaction_count_by_hash(self, json_rpc_client):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, amount=0.001)
        response = json_rpc_client.send_rpc(
            method="eth_getBlockTransactionCountByHash",
            params=receipt["blockHash"].hex(),
        )

        assert "error" not in response
        result = response["result"]
        assert rpc_checks.is_hex(result), f"Invalid response: {result}"
        assert int(response["result"], 16) != 0, "transaction count shouldn't be 0"
        EthResult(**response)

    @pytest.mark.parametrize("param", [32, "param", None])
    def test_eth_get_block_transaction_count_by_number_negative(self, param: tp.Union[int, str, None], json_rpc_client):
        """Verify implemented rpc calls work eth_getBlockTransactionCountByNumber"""
        if isinstance(param, int):
            param = hex(param)
        response = json_rpc_client.send_rpc(method="eth_getBlockTransactionCountByNumber", params=param)
        if not param or param == "param":
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert rpc_checks.is_hex(response["result"]), f"Invalid response: {response['result']}"
        EthResult(**response)

    @pytest.mark.mainnet
    @pytest.mark.parametrize("tag", [Tag.LATEST, Tag.EARLIEST, Tag.PENDING])
    def test_eth_get_block_transaction_count_by_number_tags(self, tag: Tag, json_rpc_client):
        response = json_rpc_client.send_rpc(method="eth_getBlockTransactionCountByNumber", params=tag.value)
        assert "error" not in response
        result = response["result"]
        assert rpc_checks.is_hex(result), f"Invalid response: {result}"
        EthResult(**response)

    @pytest.mark.mainnet
    def test_eth_get_block_transaction_count_by_number(self, json_rpc_client):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, amount=0.001)
        response = json_rpc_client.send_rpc(
            method="eth_getBlockTransactionCountByNumber", params=Web3.to_hex(receipt["blockNumber"])
        )
        assert "error" not in response
        result = response["result"]
        assert rpc_checks.is_hex(result), f"Invalid response: {result}"
        assert int(result, 16) != 0, "transaction count shouldn't be 0"
        EthResult(**response)
