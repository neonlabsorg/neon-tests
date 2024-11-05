from dataclasses import dataclass

import eth_abi
from eth_utils import abi

from integration.tests.neon_evm.utils.storage import create_holder
from integration.tests.neon_evm.utils.constants import SOL_CHAIN_ID, SOL_MINT_ID
from integration.tests.neon_evm.utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData


class TestMultipleScheduledTrx:

    # ┌───────┐  ┌──────┐
    # │ t1 ✓  ├─>┤ t0 ✓ │
    # │ s=1   │  │ s=0  │
    # └───────┘  └──────┘
    def test_2_depended_transactions(self, neon_user, basic_contract, evm_loader, treasury_pool, holder_acc, operator_keypair,
                                     neon_api_client):
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address, SOL_CHAIN_ID)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        tx0 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=0,
            target=basic_contract.eth_address,
            value=0,
            call_data=data
        )
        tx1 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=1,
            target=basic_contract.eth_address,
            value=0,
            call_data=data

        )
        tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
        tree_acc_data.add_trx(tx0, 0xffff, 1)
        tree_acc_data.add_trx(tx1, 0, 0)

        tree_account = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data, SOL_MINT_ID)
        additional_accounts = [basic_contract.solana_address, neon_user.get_balance_account(SOL_CHAIN_ID)]
        print("tree after creating", neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce))
        evm_loader.execute_scheduled_trx_from_instruction(
            tx1, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts
        )
        evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc)

        print("neon user", neon_user.neon_address.hex())
        holder_acc2 = create_holder(operator_keypair, evm_loader)
        evm_loader.execute_scheduled_trx_from_instruction(
            tx0, operator_keypair, holder_acc2, tree_account, treasury_pool, additional_accounts
        )
        evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc2)

    # ┌───────┐  ┌──────┐
    # │ t1 x  ├─>┤ t0 ✓ │
    # │ s=1   │  │ s=0  │
    # └───────┘  └──────┘
    def test_2_depended_transactions_one_failed(self, neon_user, basic_contract, evm_loader, treasury_pool, holder_acc, operator_keypair,
                                     neon_api_client):
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address, SOL_CHAIN_ID)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        tx0 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=0,
            target=basic_contract.eth_address,
            value=0
        )
        tx1 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=1,
            target=basic_contract.eth_address,
            value=0,
            call_data=data

        )
        tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
        tree_acc_data.add_trx(tx0, 0xffff, 1)
        tree_acc_data.add_trx(tx1, 0, 0)

        tree_account = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data, SOL_MINT_ID)
        additional_accounts = [basic_contract.solana_address, neon_user.get_balance_account(SOL_CHAIN_ID)]
        print("tree after creating", neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce))
        evm_loader.execute_scheduled_trx_from_instruction(
            tx1, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts
        )
        evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc)

        print("neon user", neon_user.neon_address.hex())
        holder_acc2 = create_holder(operator_keypair, evm_loader)
        evm_loader.execute_scheduled_trx_from_instruction(
            tx0, operator_keypair, holder_acc2, tree_account, treasury_pool, additional_accounts
        )
        evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc2)

    #  ┌──────┐
    #  │ t0 ✓ │
    # ─┤ s=1  ├─┐
    #  └──────┘ │
    #  ┌──────┐ │ ┌──────┐
    # ─┤ t1 ✓ ├─┼>┤ t3 ✓ │
    #  │ s=1  │ │ │ s=0  │
    #  └──────┘ │ └──────┘
    #  ┌──────┐ │
    # ─┤ t2 ✓ ├─┘
    #  │ s=1  │
    #  └──────┘
    def test_tree_with_parallel_trx(self, evm_loader, neon_user, basic_contract, treasury_pool, holder_acc, operator_keypair,):
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address, SOL_CHAIN_ID)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        trxs = []
        for i in range(4):
            trxs.append(ScheduledTransaction(
                neon_user.neon_address,
                None,
                nonce,
                index=i,
                target=basic_contract.eth_address,
                value=0,
                call_data=data
            ))

        tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
        tree_acc_data.add_trx(trxs[0], 3, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 3, 0)
        tree_acc_data.add_trx(trxs[3], 0xffff, 3)
        tree_account = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data, SOL_MINT_ID)

        additional_accounts = [basic_contract.solana_address, neon_user.get_balance_account(SOL_CHAIN_ID)]
        for trx in trxs:
            evm_loader.execute_scheduled_trx_from_instruction(
                trx, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts
            )
            evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc)

