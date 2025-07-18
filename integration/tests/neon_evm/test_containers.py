from integration.tests.neon_evm.utils.ethereum import make_contract_call_trx


def test_assemble_container(
    evm_loader, operator_keypair, treasury_pool, sender_with_tokens, neon_api_client, rw_lock_contract, holder_acc
):
    function_signature = "update_storage(uint256)"
    contract_accounts = neon_api_client.get_additional_accounts_by_emulation(
        sender=sender_with_tokens.eth_address.hex(),
        contract=rw_lock_contract.eth_address.hex(),
        function_signature=function_signature,
        params=[3],
    )
    signed_tx = make_contract_call_trx(evm_loader, sender_with_tokens, rw_lock_contract, function_signature, [3])
    evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair, treasury_pool, holder_acc, signed_tx, contract_accounts
    )

    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=rw_lock_contract.solana_address,
        accounts=contract_accounts,
    )
