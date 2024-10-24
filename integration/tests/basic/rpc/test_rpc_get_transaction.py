import typing as tp

import pytest
import web3

import allure
from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import Tag
from integration.tests.basic.helpers.errors import Error32602
from integration.tests.basic.helpers.rpc_checks import (
    assert_equal_fields,
    assert_fields_are_hex,
)
from utils.accounts import EthAccounts
from utils.consts import Unit
from utils.helpers import gen_hash_of_block
from utils.models.error import EthError, EthError32602
from utils.models.result import (
    EthGetBlockByNumberAndIndexNoneResult,
    EthGetBlockByNumberAndIndexResult,
    EthGetTransactionByHashResult,
    EthGetTransactionReceiptResult,
    EthResult,
)
from utils.web3client import NeonChainWeb3Client


@allure.feature("JSON-RPC validation")
@allure.story("Verify getTransaction methods")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestRpcGetTransaction:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @staticmethod
    def validate_response(result, tx_receipt: tp.Union[web3.types.TxReceipt, None]):
        expected_hex_fields = [
            "blockHash",
            "blockNumber",
            "hash",
            "transactionIndex",
            "type",
            "from",
            "nonce",
            "gasPrice",
            "gas",
            "to",
            "value",
            "v",
            "s",
            "r",
        ]
        for field in expected_hex_fields:
            assert rpc_checks.is_hex(result[field])
        assert result["blockHash"] == tx_receipt.blockHash.hex()
        assert result["from"].upper() == tx_receipt["from"].upper()
        assert result["to"].upper() == tx_receipt["to"].upper()

    @pytest.mark.parametrize("valid_index", [True, False])
    @pytest.mark.mainnet
    def test_eth_get_transaction_by_block_number_and_index(self, valid_index: bool, json_rpc_client):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        amount = 1
        """Verify implemented rpc calls work eth_getTransactionByBlockNumberAndIndex"""
        tx_receipt = self.web3_client.send_neon(sender_account, recipient_account, amount=amount)
        transaction_index = hex(tx_receipt.transactionIndex) if valid_index else hex(999)
        response = json_rpc_client.send_rpc(
            method="eth_getTransactionByBlockNumberAndIndex",
            params=[hex(tx_receipt.blockNumber), transaction_index],
        )
        assert "result" in response
        if not valid_index:
            assert response["result"] is None, "Result should be None"
            EthGetBlockByNumberAndIndexNoneResult(**response)
        else:
            assert "error" not in response
            result = response["result"]
            self.validate_response(result, tx_receipt)
            assert result["value"] == hex(self.web3_client.to_wei(amount, Unit.ETHER))
            EthGetBlockByNumberAndIndexResult(**response)

    @pytest.mark.parametrize("valid_index", [True, False])
    @pytest.mark.mainnet
    def test_eth_get_transaction_by_block_hash_and_index(self, valid_index: bool, json_rpc_client):
        """Verify implemented rpc calls work eth_getTransactionByBlockHashAndIndex"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        tx_receipt = self.web3_client.send_neon(sender_account, recipient_account, 1)
        transaction_index = hex(tx_receipt.transactionIndex) if valid_index else hex(999)
        response = json_rpc_client.send_rpc(
            method="eth_getTransactionByBlockHashAndIndex",
            params=[tx_receipt.blockHash.hex(), transaction_index],
        )
        assert "result" in response
        if not valid_index:
            assert response["result"] is None, "Result should be None"
            EthGetBlockByNumberAndIndexNoneResult(**response)
        else:
            assert "error" not in response
            result = response["result"]
            self.validate_response(result, tx_receipt)
            EthGetBlockByNumberAndIndexResult(**response)

    @pytest.mark.parametrize("tag", [Tag.LATEST.value, Tag.EARLIEST.value, "param"])
    @pytest.mark.mainnet
    def test_eth_get_transaction_by_block_number_and_index_by_tag(self, tag: str, json_rpc_client):
        """Verify implemented rpc calls work eth_getTransactionByBlockNumberAndIndex"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]

        tx_receipt = self.web3_client.send_neon(sender_account, recipient_account, 1)
        response = json_rpc_client.send_rpc(
            method="eth_getTransactionByBlockNumberAndIndex",
            params=[tag, hex(tx_receipt.transactionIndex)],
        )
        if tag == "param":
            assert "error" in response, "Error not in response"
            EthError(**response)
        else:
            assert "error" not in response
            result = response["result"]
            if result:
                expected_hex_fields = [
                    "blockHash",
                    "blockNumber",
                    "hash",
                    "transactionIndex",
                    "type",
                    "from",
                    "nonce",
                    "gasPrice",
                    "gas",
                    "value",
                    "v",
                    "s",
                    "r",
                ]
                for field in expected_hex_fields:
                    assert rpc_checks.is_hex(result[field]), f"Field {field} must be hex but '{result[field]}'"
                EthGetBlockByNumberAndIndexResult(**response)
            else:
                EthGetBlockByNumberAndIndexNoneResult(**response)

    # Geth returns invalid argument 0: hex string has length 62, want 64 for common.Hash
    @pytest.mark.parametrize("method", ["neon_getTransactionReceipt", "eth_getTransactionReceipt"])
    @pytest.mark.neon_only
    def test_get_transaction_receipt_with_incorrect_hash(self, method, json_rpc_client):
        """Verify implemented rpc calls work with neon_getTransactionReceipt and eth_getTransactionReceipt
        when transaction hash is not correct"""

        response = json_rpc_client.send_rpc(method=method, params=gen_hash_of_block(31))
        assert "error" in response
        assert response["error"]["message"] == Error32602.INVALID_TRANSACTIONID
        EthError32602(**response)

    @pytest.mark.parametrize("param", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST, None])
    @pytest.mark.mainnet
    def test_eth_get_transaction_count(self, param: tp.Union[Tag, None], json_rpc_client):
        """Verify implemented rpc calls work eth_getTransactionCount"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        if param:
            self.web3_client.send_neon(sender_account, recipient_account, 1)
            param = [sender_account.address, param.value]
        response = json_rpc_client.send_rpc("eth_getTransactionCount", params=param)
        if not param:
            assert "error" in response, "Error not in response"
            EthError32602(**response)
        else:
            assert "error" not in response
            assert rpc_checks.is_hex(response["result"]), AssertMessage.DOES_NOT_START_WITH_0X.value
            EthResult(**response)

    @pytest.mark.parametrize("param", [32, 16, None])
    @pytest.mark.bug  # fails on geth (returns a different error message), needs a fix, and refactor of Error32602
    def test_eth_get_transaction_by_hash_negative(self, param: tp.Union[int, None], json_rpc_client):
        response = json_rpc_client.send_rpc(
            method="eth_getTransactionByHash",
            params=gen_hash_of_block(param) if param else param,
        )

        if param is pow(2, 5):
            assert "error" not in response
            assert "result" in response and response["result"] is None, f"Invalid response: {response['result']}"
            return

        assert "error" in response, "error field not in response"
        assert "code" in response["error"]
        assert "message" in response["error"], "message field not in response"
        code = response["error"]["code"]
        message = response["error"]["message"]

        assert code == Error32602.CODE, "wrong code"
        assert message == Error32602.INVALID_TRANSACTIONID, "wrong message"
        EthError32602(**response)

    @pytest.mark.mainnet
    def test_eth_get_transaction_by_hash(self, json_rpc_client):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, amount=0.001)
        response = json_rpc_client.send_rpc(
            method="eth_getTransactionByHash",
            params=receipt["transactionHash"].hex(),
        )
        assert "error" not in response
        result = response["result"]
        assert_fields_are_hex(
            result,
            ["blockHash", "blockNumber", "hash", "transactionIndex", "type", "from", "nonce", "gasPrice", "gas", "to"],
        )
        assert_equal_fields(
            result,
            receipt,
            ["blockHash", "blockNumber", "hash", "transactionIndex", "type", "from", "to"],
            {"hash": "transactionHash"},
        )
        EthGetTransactionByHashResult(**response)

    @pytest.mark.mainnet
    @pytest.mark.parametrize("method", ["neon_getTransactionReceipt", "eth_getTransactionReceipt"])
    @pytest.mark.neon_only
    def test_get_transaction_receipt(self, method, json_rpc_client):
        """Verify implemented rpc calls work with neon_getTransactionReceipt and eth_getTransactionReceipt"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        tx_receipt = self.web3_client.send_neon(sender_account, recipient_account, 1)
        transaction_hash = tx_receipt.transactionHash.hex()
        params = [transaction_hash]
        if method.startswith("neon_"):
            params.append("ethereum")
        response = json_rpc_client.send_rpc(method=method, params=params)
        #        response = self.proxy_api.send_rpc(method=method, params=transaction_hash)
        assert "error" not in response
        assert "result" in response, AssertMessage.DOES_NOT_CONTAIN_RESULT
        result = response["result"]
        assert_fields_are_hex(
            result,
            [
                "transactionHash",
                "transactionIndex",
                "blockNumber",
                "blockHash",
                "cumulativeGasUsed",
                "gasUsed",
                "logsBloom",
                "status",
            ],
        )
        assert result["status"] == "0x1", "Transaction status must be 0x1"
        assert result["transactionHash"] == transaction_hash
        assert result["blockHash"] == tx_receipt.blockHash.hex()
        assert result["from"].upper() == tx_receipt["from"].upper()
        assert result["to"].upper() == tx_receipt["to"].upper()
        assert result["contractAddress"] is None
        assert result["logs"] == []
        EthGetTransactionReceiptResult(**response)

    @pytest.mark.parametrize("method", ["neon_getTransactionReceipt", "eth_getTransactionReceipt"])
    @pytest.mark.neon_only
    def test_eth_get_transaction_receipt_when_hash_doesnt_exist(self, method, json_rpc_client):
        """Verify implemented rpc calls work eth_getTransactionReceipt when transaction hash doesn't exist"""
        response = json_rpc_client.send_rpc(method=method, params=gen_hash_of_block(32))
        assert "result" in response and response["result"] is None, "Result should be None"

    @pytest.mark.parametrize(
        "params, error_code, error_message",
        [
            ([], Error32602.CODE, Error32602.INVALID_PARAMETERS),
            (["0x874E87B5ccb467f07Ca42cF82e11aD44c7be159F"], Error32602.CODE, Error32602.INVALID_NONCE),
            ([None, 10], Error32602.CODE, Error32602.INVALID_SENDER),
            (["123345", 10], Error32602.CODE, Error32602.INVALID_SENDER),
            (["0x874E87B5ccb467f07Ca42cF82e11aD44c7be159F", None], Error32602.CODE, Error32602.INVALID_NONCE),
        ],
    )
    @pytest.mark.bug  # Geth returns code 32601
    def test_neon_get_transaction_by_sender_nonce_negative(self, params, error_code, error_message, json_rpc_client):
        response = json_rpc_client.send_rpc(method="neon_getTransactionBySenderNonce", params=params)
        assert "error" in response, "error field not in response"
        assert "code" in response["error"]
        assert "message" in response["error"], "message field not in response"
        assert error_code == response["error"]["code"]
        assert error_message == response["error"]["message"]

    @pytest.mark.neon_only
    def test_neon_get_transaction_by_sender_nonce_plus_one(self, json_rpc_client):
        """Request nonce+1, which is not exist"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        nonce = self.web3_client.get_nonce(sender_account)
        self.web3_client.send_neon(sender_account, recipient_account, amount=0.1)
        response = json_rpc_client.send_rpc(
            method="neon_getTransactionBySenderNonce", params=[sender_account.address, nonce + 1]
        )
        assert "result" in response
        assert "error" not in response
        assert response["result"] is None

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    def test_neon_get_transaction_by_sender_nonce(self, json_rpc_client):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        nonce = self.web3_client.get_nonce(sender_account)
        receipt = self.web3_client.send_neon(sender_account, recipient_account, amount=0.1)
        response = json_rpc_client.send_rpc(
            method="neon_getTransactionBySenderNonce", params=[sender_account.address, nonce]
        )
        assert "error" not in response
        result = response["result"]

        assert_fields_are_hex(
            result,
            ["blockHash", "blockNumber", "hash", "transactionIndex", "type", "from", "nonce", "gasPrice", "gas", "to"],
        )
        assert_equal_fields(
            result,
            receipt,
            ["blockHash", "blockNumber", "hash", "transactionIndex", "type", "from", "to"],
            {"hash": "transactionHash"},
        )
