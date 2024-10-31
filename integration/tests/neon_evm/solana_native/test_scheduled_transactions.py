import eth_abi
import pytest
import solana
from eth_utils import abi, to_int
from solana.rpc.core import RPCException

from integration.tests.neon_evm.utils.assert_messages import InstructionAsserts
from integration.tests.neon_evm.utils.storage import create_holder
from utils.neon_user import NeonUser
from integration.tests.neon_evm.utils.constants import SOL_CHAIN_ID, SOL_MINT_ID
from integration.tests.neon_evm.utils.scheduled_trx import ScheduledTransaction


class TestScheduledTrx:
    def test_execute_scheduled_trx_from_account(
        self,
        evm_loader,
        neon_user: NeonUser,
        treasury_pool,
        basic_contract,
        neon_api_client,
        operator_keypair,
        #holder_acc,
    ):
        holder_acc = create_holder(operator_keypair, evm_loader)
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address, SOL_CHAIN_ID)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        tx = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            0,
            target=basic_contract.eth_address,
            value=0,
            call_data=data,
        )

        tree_account = evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode(), SOL_MINT_ID)

        assert (
            len(neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce)["value"]["transactions"]) == 1
        )

        evm_loader.write_transaction_to_holder_account(tx.encode(), holder_acc, operator_keypair)
        additional_accounts = [basic_contract.solana_address, neon_user.get_balance_account(SOL_CHAIN_ID)]
        evm_loader.execute_scheduled_trx_from_account(
            0, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts
        )

    def test_execute_scheduled_trx_from_instruction(
        self,
        evm_loader,
        neon_user: NeonUser,
        treasury_pool,
        basic_contract,
        neon_api_client,
        operator_keypair,
    ):
        holder_acc = create_holder(operator_keypair, evm_loader)
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address, SOL_CHAIN_ID)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        tx = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            0,
            target=basic_contract.eth_address,
            value=0,
            call_data=data,
        )

        tree_account = evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode(), SOL_MINT_ID)
        assert (
            len(neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce)["value"]["transactions"]) == 1
        )

        additional_accounts = [basic_contract.solana_address, neon_user.get_balance_account(SOL_CHAIN_ID)]
        evm_loader.execute_scheduled_trx_from_instruction(
            tx, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts
        )

        data = abi.function_signature_to_4byte_selector("getNumber()")
        result = neon_api_client.emulate(
            neon_user.neon_address.hex(), contract=basic_contract.eth_address.hex(), data=data
        )
        assert to_int(hexstr=result["result"]) == contract_data

        evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc)
        evm_loader.destroy_tree_account(neon_user, treasury_pool, tree_account)


    def test_scheduled_trx_wrong_index(
        self,
        evm_loader,
        neon_user: NeonUser,
        treasury_pool,
        basic_contract,
        neon_api_client,
        operator_keypair,
        holder_acc,
    ):
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address, SOL_CHAIN_ID)

        index = 1
        tx = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index,
            target=basic_contract.eth_address,
            value=0,
        )

        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.TRANSACTION_TREE_INVALID_DATA):
            evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode(), SOL_MINT_ID)
