from .solana_utils import execute_trx_from_account, write_transaction_to_holder_account
from .utils.constants import TAG_HOLDER
from .utils.contract import make_deployment_transaction

from .utils.ethereum import make_eth_transaction, create_contract_address
from .utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT
from .utils.transaction_checks import check_transaction_logs_have_text, check_holder_account_tag
from .types.types import Caller


class TestExecuteTrxFromAccount:
    def test_simple_transfer_transaction(
        self, operator_keypair, treasury_pool, sender_with_tokens: Caller, session_user: Caller, holder_acc, evm_loader
    ):
        amount = 10
        sender_balance_before = evm_loader.get_neon_balance(sender_with_tokens)
        recipient_balance_before = evm_loader.get_neon_balance(session_user)
        signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, amount)
        write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        resp = execute_trx_from_account(
            operator_keypair,
            holder_acc,
            evm_loader,
            treasury_pool.account,
            treasury_pool.buffer,
            [
                sender_with_tokens.balance_account_address,
                session_user.balance_account_address,
                session_user.solana_account_address,
            ],
            operator_keypair,
        )
        sender_balance_after = evm_loader.get_neon_balance(sender_with_tokens)
        recipient_balance_after = evm_loader.get_neon_balance(session_user)
        assert sender_balance_before - amount == sender_balance_after
        assert recipient_balance_before + amount == recipient_balance_after
        check_transaction_logs_have_text(resp.value, "exit_status=0x11")

    def test_deploy_contract(
        self, operator_keypair, new_holder_acc, treasury_pool, evm_loader, sender_with_tokens, neon_api_client
    ):
        contract = create_contract_address(sender_with_tokens, evm_loader)

        signed_tx = make_deployment_transaction(sender_with_tokens, "hello_world")
        write_transaction_to_holder_account(signed_tx, new_holder_acc, operator_keypair)

        resp = execute_trx_from_account(
            operator_keypair,
            new_holder_acc,
            evm_loader,
            treasury_pool.account,
            treasury_pool.buffer,
            [
                contract.solana_address,
                contract.balance_account_address,
                sender_with_tokens.solana_account_address,
                sender_with_tokens.balance_account_address,
            ],
            operator_keypair,
        )
        check_holder_account_tag(new_holder_acc, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_HOLDER)
        check_transaction_logs_have_text(resp.value, "exit_status=0x12")
