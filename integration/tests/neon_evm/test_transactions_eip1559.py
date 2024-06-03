from integration.tests.neon_evm.utils.constants import TAG_FINALIZED_STATE
from integration.tests.neon_evm.utils.contract import make_contract_call_trx
from integration.tests.neon_evm.utils.transaction_checks import (
    check_holder_account_tag,
    check_transaction_logs_have_text,
)
from utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT


class TestEIP1559Transactions:
    def test_contract_interaction_transaction(
        self,
        operator_keypair,
        holder_acc,
        treasury_pool,
        sender_with_tokens,
        evm_loader,
        calculator_contract,
        calculator_caller_contract,
    ):
        signed_tx = make_contract_call_trx(
            evm_loader,
            sender_with_tokens,
            calculator_caller_contract,
            "callCalculator()",
            maxFeePerGas=10000,
            maxPriorityFeePerGas=10,
        )
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair,
            treasury_pool,
            holder_acc,
            [
                calculator_caller_contract.solana_address,
                calculator_contract.solana_address,
                sender_with_tokens.solana_account_address,
                sender_with_tokens.balance_account_address,
            ],
            compute_unit_price=3929
        )

        check_holder_account_tag(holder_acc, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        check_transaction_logs_have_text(resp, "exit_status=0x12")
