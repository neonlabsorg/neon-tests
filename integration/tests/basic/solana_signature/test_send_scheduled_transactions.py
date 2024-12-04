import time

import allure
import eth_abi
import pytest
import requests
from eth_utils import abi

from utils.consts import wSOL
from utils.models.tree_account import TreeAccount
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData


@allure.feature("Solana native")
@allure.story("Test sending scheduled transaction")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestScheduledTrx:
    def test_send_simple_single_trx(self, web3_client_sol, neon_user, common_contract_sol, evm_loader, treasury_pool):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        tx = ScheduledTransaction(
            neon_user.neon_address, None, nonce, 0, target=common_contract_sol.address, call_data=data
        )
        evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode(), wSOL["address_spl"])
        web3_client_sol.wait_for_transaction_receipt(tx.hash())
        assert common_contract_sol.functions.getNumber().call() == contract_data

    def test_multiple_scheduled_trx(self, web3_client_sol, neon_user, common_contract_sol, evm_loader, treasury_pool):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        trxs = []
        max_fee_per_gas = 3000000000
        max_priority_fee_per_gas = 15
        for i in range(4):
            trxs.append(
                ScheduledTransaction(
                    neon_user.neon_address,
                    None,
                    nonce,
                    index=i,
                    target=common_contract_sol.address,
                    call_data=data,
                    max_fee_per_gas=max_fee_per_gas,
                    max_priority_fee_per_gas=max_priority_fee_per_gas,
                )
            )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
        )
        tree_acc_data.add_trx(trxs[0], 3, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 3, 0)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 3)
        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"])

        web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            resp = web3_client_sol.wait_for_transaction_receipt(trx.hash())
            assert resp["status"] == 1

    def test_multiple_scheduled_trx_with_failed_trx(
        self, web3_client_sol, neon_user, treasury_pool, revert_contract_caller, event_caller_contract, evm_loader
    ):
        revert_contract_caller = web3_client_sol.get_deployed_contract(
            revert_contract_caller.address, "common/Revert", contract_name="Caller"
        )
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        call_data = abi.function_signature_to_4byte_selector("doAssert()")
        max_fee_per_gas = 3000000000
        max_priority_fee_per_gas = 15

        tx0 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=1,
            target=revert_contract_caller.address,
            call_data=call_data,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
        call_data = abi.function_signature_to_4byte_selector("indexedArgs()")
        tx1 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=0,
            target=revert_contract_caller.address,
            call_data=call_data,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
        )
        tree_acc_data.add_trx(tx1, 1, 0)
        tree_acc_data.add_trx(tx0, 0xFFFF, 1)
        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"])

        web3_client_sol.send_all_scheduled_transactions([tx0, tx1])
        print(neon_user.checksum_address)
        resp1 = web3_client_sol.wait_for_transaction_receipt(tx0.hash())
        assert resp1["status"] == 0
        resp2 = web3_client_sol.wait_for_transaction_receipt(tx1.hash())
        assert resp2["status"] == 1
