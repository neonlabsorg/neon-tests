import allure
import eth_abi
import pytest
from eth_utils import abi

from integration.tests.basic.helpers.rpc_checks import is_hex

from utils.models.result import (
    EthResult,
    EthGetScheduledTxBlockByHashFullResult,
)
from utils.consts import wSOL
from utils.scheduled_trx import ScheduledTransaction, ScheduledTrxEstimateRequest, CreateTreeAccMultipleData
from utils.models.result import EthGetBlockByHashResult


@allure.feature("JSON-RPC validation")
@allure.story("Verify JSON-RPC neon_sendRawScheduledTransaction work")
class TestNeonRPCGetBlockNumber:

    def test_send_simple_single_trx(self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool):
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )

        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        evm_loader.create_tree_account(
            neon_user, treasury_pool, tx.encode(), wSOL["address_spl"], chain_id=evm_loader.sol_chain_id
        )

        resp = web3_client_sol.send_scheduled_transaction(tx, check_result=True)
        EthResult(**resp)
        assert is_hex(resp["result"])

    @pytest.mark.mainnet
    @pytest.mark.parametrize(
        "params_case, method, full_trx",
        [
            ("blockNumber_case", "eth_getBlockByNumber", True),
            ("blockNumber_case", "eth_getBlockByNumber", False),
            ("blockHash_case", "eth_getBlockByHash", True),
            ("blockHash_case", "eth_getBlockByHash", False),
        ],
    )
    def test_get_block_of_scheduled_transaction(
        self,
        json_rpc_client,
        web3_client_sol,
        neon_user,
        common_contract,
        evm_loader,
        treasury_pool,
        params_case,
        method,
        full_trx,
    ):
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )

        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        evm_loader.create_tree_account(
            neon_user, treasury_pool, tx.encode(), wSOL["address_spl"], chain_id=evm_loader.sol_chain_id
        )

        web3_client_sol.send_scheduled_transaction(tx, check_result=True)
        tx_receipt = web3_client_sol.wait_for_transaction_receipt(tx.hash(), timeout=180)

        params = None
        if params_case == "blockNumber_case":
            params = [hex(tx_receipt.blockNumber), full_trx]
        elif params_case == "blockHash_case":
            params = [tx_receipt.blockHash.hex(), full_trx]

        resp = json_rpc_client.send_rpc(
            method=method,
            params=params,
        )

        if full_trx:
            EthGetScheduledTxBlockByHashFullResult(**resp)
        else:
            EthGetBlockByHashResult(**resp)

    @pytest.mark.mainnet
    @pytest.mark.neon_only
    @pytest.mark.parametrize(
        "params_case, method, full_trx",
        [
            ("blockNumber_case", "eth_getBlockByNumber", True),
            ("blockNumber_case", "eth_getBlockByNumber", False),
            ("blockHash_case", "eth_getBlockByHash", True),
            ("blockHash_case", "eth_getBlockByHash", False),
        ],
    )
    def test_neon_get_block_of_reverted_scheduled_transaction(
        self,
        json_rpc_client,
        web3_client_sol,
        neon_user,
        treasury_pool,
        event_caller_contract,
        evm_loader,
        common_contract,
        revert_contract_caller,
        params_case,
        method,
        full_trx,
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        call_data = abi.function_signature_to_4byte_selector("doAssert()")

        gas_limit = 3000000
        base_fee_per_gas = web3_client_sol.base_fee_per_gas()
        max_priority_fee_per_gas = 2500000000
        max_fee_per_gas = base_fee_per_gas * 2 + max_priority_fee_per_gas

        tx0 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=0,
            target=revert_contract_caller.address,
            call_data=call_data,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit,
        )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
        )
        tree_acc_data.add_trx(tx0, 0xFFFF, 0)
        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"])

        web3_client_sol.send_scheduled_transaction(tx0, check_result=True)
        tx_receipt = web3_client_sol.wait_for_transaction_receipt(tx0.hash(), timeout=180)
        assert tx_receipt["status"] == 0

        params = None
        if params_case == "blockNumber_case":
            params = [hex(tx_receipt.blockNumber), full_trx]
        elif params_case == "blockHash_case":
            params = [tx_receipt.blockHash.hex(), full_trx]

        resp = json_rpc_client.send_rpc(
            method=method,
            params=params,
        )

        if full_trx:
            EthGetScheduledTxBlockByHashFullResult(**resp)
        else:
            EthGetBlockByHashResult(**resp)
