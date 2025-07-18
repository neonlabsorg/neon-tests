from integration.tests.neon_evm.utils.ethereum import make_contract_call_trx
from integration.tests.neon_evm.utils.transaction_checks import check_transaction_logs_have_text


def test_assemble_container(
    evm_loader, operator_keypair, treasury_pool, sender_with_tokens, neon_api_client, rw_lock_contract, holder_acc
):
    function_signature = "update_storage(uint256)"
    emulate_accounts = neon_api_client.get_additional_accounts_by_emulation(
        sender=sender_with_tokens.eth_address.hex(),
        contract=rw_lock_contract.eth_address.hex(),
        function_signature=function_signature,
        params=[10],
    )
    signed_tx = make_contract_call_trx(evm_loader, sender_with_tokens, rw_lock_contract, function_signature, [10])
    evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair, treasury_pool, holder_acc, signed_tx, emulate_accounts
    )
    data_accounts = evm_loader.get_data_accounts(emulate_accounts)
    # assemble container and execute transaction with it
    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=rw_lock_contract.solana_address,
        accounts=data_accounts,
    )

    accounts_for_execution_with_container = [
        rw_lock_contract.solana_address,
        sender_with_tokens.solana_account_address,
        sender_with_tokens.balance_account_address,
    ]

    signed_tx = make_contract_call_trx(evm_loader, sender_with_tokens, rw_lock_contract, function_signature, [10])
    resp = evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair,
        treasury_pool,
        holder_acc,
        signed_tx,
        accounts_for_execution_with_container,
    )
    check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

    # allocate container and execute transaction with it
    evm_loader.allocate_container(
        operator=operator_keypair, treasury=treasury_pool, container_address=rw_lock_contract.solana_address, size=32
    )

    signed_tx = make_contract_call_trx(evm_loader, sender_with_tokens, rw_lock_contract, function_signature, [10])
    resp = evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair,
        treasury_pool,
        holder_acc,
        signed_tx,
        accounts_for_execution_with_container,
    )
    check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")
