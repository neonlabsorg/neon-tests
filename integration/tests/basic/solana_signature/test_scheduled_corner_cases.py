import time
import copy

import allure
import operator
import pytest

from spl.token.instructions import (
    get_associated_token_address,
    MintToParams,
    ApproveParams,
    approve,
)
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.rpc.responses import GetTransactionResp
from spl.token.constants import TOKEN_PROGRAM_ID, WRAPPED_SOL_MINT

from integration.tests.basic.helpers.errors import Error32602, Error32000
from utils.helpers import decode_function_signature, wait_condition
from utils.scheduled_trx import ScheduledTransaction, ScheduledTrxEstimateRequest, CreateTreeAccMultipleData
from utils.instructions import (
    make_scheduled_transaction_create,
    make_scheduled_transaction_create_multiple,
    make_scheduled_transaction_destroy,
    make_scheduled_transaction_finish
)


@allure.feature("JSON-RPC validation")
@allure.story("Verify proxy work with consequent calls")
class TestScheduledCornerCases:
    def wait_for_tree_removal(self, sol_client, start_slot):
        while True:
            cur_slot = sol_client.get_slot().value
            if cur_slot >= start_slot + 750:
                return

    def test_create_destroy_create(self, json_sol_rpc_client, web3_client_sol, neon_user, common_contract, evm_loader,
                               treasury_pool, operator, sol_client):
        """
        Create scheduled tx (only tree) and remove it
        1. Create tree and save user nonce
        2. Destroy tree
        3. Check tree is removed and check user nonce is not changed
        """
        chain_id = evm_loader.sol_chain_id
        mint = WRAPPED_SOL_MINT
        payer_nonce = evm_loader.get_neon_nonce(neon_user.neon_address, chain_id).to_bytes(8, "little")
        authority_pool = evm_loader.create_get_authority_address()
        tree_account = evm_loader.create_tree_account_address(neon_user.neon_address, payer_nonce, chain_id)
        pool = get_associated_token_address(authority_pool, mint)
        balance_account = evm_loader.create_balance_account(neon_user.neon_address, neon_user.solana_account, chain_id)

        data = decode_function_signature("setNumber(uint256)", [18])
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])
        orig_tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        tx = copy.copy(orig_tx)
        tx.max_fee_per_gas = 1_100_000_000
        tx.max_priority_fee_per_gas = 1000

        trx = Transaction()
        trx.add(
            make_scheduled_transaction_create(
                neon_user.solana_account, balance_account, treasury_pool, tree_account, pool,
                tx.encode(),  evm_loader.loader_id
            )
        )
        # sender_neon_nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        destroy_trx = Transaction()
        destroy_trx.add(
            make_scheduled_transaction_destroy(
                operator.operator_keypairs[0].pubkey(), balance_account, treasury_pool, tree_account,
                evm_loader.loader_id
            )
        )

        create_tree_res = evm_loader.send_tx(trx, neon_user.solana_account)

        start_block = create_tree_res.value.slot
        self.wait_for_tree_removal(sol_client, start_block)

        evm_loader.send_tx(destroy_trx, operator.operator_keypairs[0])
        rich_tx = copy.copy(orig_tx)
        rich_tx.max_fee_per_gas *= 10

        evm_loader.send_tx(trx, neon_user.solana_account)
        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=800*0.4, delay=2)


    def test_create_tx_without_destroy(self, json_sol_rpc_client, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool):
        pass

    def test_several_trees_one_tx(self, json_sol_rpc_client, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool):
        """
        Create several trees in one transaction, check user nonce
        """