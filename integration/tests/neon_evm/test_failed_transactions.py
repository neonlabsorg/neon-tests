from integration.tests.neon_evm.utils.ethereum import make_contract_call_trx
from integration.tests.neon_evm.utils.transaction_checks import check_transaction_logs_have_text
from utils.evm_loader import EVM_STEPS


class TestFailedTransactions:
    def test_refund_sent_tokens_if_trx_was_failed(
        self,
        operator_keypair,
        treasury_pool,
        neon_api_client,
        session_user,
        evm_loader,
        holder_acc,
    ):
        sender = evm_loader.make_new_user(operator_keypair)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)

        recipient = session_user

        evm_loader.deposit_neon(operator_keypair, sender.eth_address, 1000000)
        contract = evm_loader.deploy_contract(
            operator_keypair, session_user, "transfers", neon_api_client, treasury_pool
        )

        amount = evm_loader.get_neon_balance(sender.eth_address)

        signed_tx = make_contract_call_trx(
            evm_loader,
            sender,
            contract,
            "transferNeonAndRaiseError(uint256,address[])",
            [amount // 2, [recipient.eth_address]],
            value=amount // 2,
        )
        accounts = [
            sender.balance_account_address,
            sender.solana_account_address,
            contract.balance_account_address,
            contract.solana_address,
            recipient.balance_account_address,
            recipient.solana_account_address,
        ]

        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            accounts,
            EVM_STEPS,
            operator_keypair,
        )
        # check balance changed after first iteration
        assert evm_loader.get_neon_balance(sender.eth_address) == amount // 2

        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair,
            treasury_pool,
            holder_acc,
            accounts,
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0xD0")
        # balance should be refunded
        assert evm_loader.get_neon_balance(sender.eth_address) == amount
