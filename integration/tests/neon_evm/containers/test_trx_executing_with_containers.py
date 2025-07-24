import pytest

from integration.tests.neon_evm.utils.ethereum import make_contract_call_trx
from integration.tests.neon_evm.utils.transaction_checks import check_transaction_logs_have_text
from utils.consts import ExecuteTrxTypes
from utils.neon_layouts.balance_account import BalanceAccount


def test_assemble_and_allocate_container(
    evm_loader,
    operator_keypair,
    treasury_pool,
    sender_with_tokens,
    neon_rpc_client,
    rw_lock_contract_containerized,
    holder_acc,
):
    function_signature = "update_storage(uint256)"
    emulate_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
        sender=sender_with_tokens.eth_address.hex(),
        contract=rw_lock_contract_containerized.eth_address.hex(),
        function_signature=function_signature,
        params=[10],
    )
    signed_tx = make_contract_call_trx(
        evm_loader, sender_with_tokens, rw_lock_contract_containerized, function_signature, [10]
    )
    evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair, treasury_pool, holder_acc, signed_tx, emulate_accounts
    )
    data_accounts = evm_loader.get_data_accounts(emulate_accounts)
    # assemble container and execute transaction with it
    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=rw_lock_contract_containerized.solana_address,
        accounts=data_accounts,
    )
    container_data_len_before = len(evm_loader.get_solana_account_data(rw_lock_contract_containerized.solana_address))

    # allocate container and execute transaction with it
    size = 256
    evm_loader.allocate_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=rw_lock_contract_containerized.solana_address,
        size=size,
    )
    container_data_len_after = len(evm_loader.get_solana_account_data(rw_lock_contract_containerized.solana_address))
    assert (
        container_data_len_after == container_data_len_before + size
    ), "Container data length did not increase after allocation"
    accounts_for_execution_with_container = [
        rw_lock_contract_containerized.solana_address,
        sender_with_tokens.solana_account_address,
        sender_with_tokens.balance_account_address,
    ]
    signed_tx = make_contract_call_trx(
        evm_loader, sender_with_tokens, rw_lock_contract_containerized, function_signature, [10]
    )
    resp = evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair,
        treasury_pool,
        holder_acc,
        signed_tx,
        accounts_for_execution_with_container,
    )
    check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")


def test_execute_trx_step_from_instruction_for_container(
    evm_loader,
    operator_keypair,
    treasury_pool,
    sender_with_tokens,
    neon_rpc_client,
    distributor_caller_containerized,
    holder_acc,
    recipients,
):
    function_signature = "distribute_value()"
    value = len(recipients) * 10
    container_address = distributor_caller_containerized.solana_address
    recipient_balance_acc_data = neon_rpc_client.get_account_data_from_container(
        container_address, recipients[0].balance_account_address
    )
    recipient_balance_before = BalanceAccount(recipient_balance_acc_data).balance

    accounts_for_execution_with_container = [
        container_address,
        sender_with_tokens.solana_account_address,
        sender_with_tokens.balance_account_address,
    ] + [recipient.solana_account_address for recipient in recipients]

    signed_tx = make_contract_call_trx(
        evm_loader, sender_with_tokens, distributor_caller_containerized, function_signature, value=value
    )
    resp = evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair,
        treasury_pool,
        holder_acc,
        signed_tx,
        accounts_for_execution_with_container,
    )
    check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

    recipient_balance_acc_data = neon_rpc_client.get_account_data_from_container(
        container_address, recipients[0].balance_account_address
    )
    recipient_balance_after = BalanceAccount(recipient_balance_acc_data).balance

    assert recipient_balance_after == recipient_balance_before + value / len(recipients)


@pytest.mark.parametrize("execution_type", list(ExecuteTrxTypes))
def test_execute_trx_with_containerized_contract(
    evm_loader,
    operator_keypair,
    treasury_pool,
    sender_with_tokens,
    neon_rpc_client,
    distributor_caller_containerized,
    holder_acc,
    recipients,
    execution_type,
):
    function_signature = "distribute_value()"
    value = len(recipients) * 10
    container_address = distributor_caller_containerized.solana_address
    recipient_balance_acc_data = neon_rpc_client.get_account_data_from_container(
        container_address, recipients[0].balance_account_address
    )
    recipient_balance_before = BalanceAccount(recipient_balance_acc_data).balance

    accounts_for_execution_with_container = [
        container_address,
        sender_with_tokens.solana_account_address,
        sender_with_tokens.balance_account_address,
    ] + [recipient.solana_account_address for recipient in recipients]

    signed_tx = make_contract_call_trx(
        evm_loader, sender_with_tokens, distributor_caller_containerized, function_signature, value=value
    )

    resp = evm_loader.execute_neon_trx(
        execution_type, signed_tx, operator_keypair, holder_acc, treasury_pool, accounts_for_execution_with_container
    )
    check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

    recipient_balance_acc_data = neon_rpc_client.get_account_data_from_container(
        container_address, recipients[0].balance_account_address
    )
    recipient_balance_after = BalanceAccount(recipient_balance_acc_data).balance

    assert recipient_balance_after == recipient_balance_before + value / len(recipients)


def test_assemble_new_additional_accounts_from_emulation_many_times(
    evm_loader,
    operator_keypair,
    treasury_pool,
    sender_with_tokens,
    neon_rpc_client,
    rw_lock_contract_containerized,
    holder_acc,
):
    function_signature = "update_storage(uint256)"
    for acc_count in [20, 40, 60, 80]:
        emulate_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
            sender=sender_with_tokens.eth_address.hex(),
            contract=rw_lock_contract_containerized.eth_address.hex(),
            function_signature=function_signature,
            params=[acc_count],
        )

        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, rw_lock_contract_containerized, function_signature, [acc_count]
        )
        evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair, treasury_pool, holder_acc, signed_tx, emulate_accounts
        )

        data_accounts = evm_loader.get_data_accounts(emulate_accounts)
        evm_loader.assemble_container(
            operator=operator_keypair,
            treasury=treasury_pool,
            container_address=rw_lock_contract_containerized.solana_address,
            accounts=data_accounts,
        )

        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, rw_lock_contract_containerized, function_signature, [acc_count]
        )
        resp = evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            holder_acc,
            signed_tx,
            [
                rw_lock_contract_containerized.solana_address,
                sender_with_tokens.solana_account_address,
                sender_with_tokens.balance_account_address,
            ],
        )

        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")


def test_2_parallel_trx_with_container(
    evm_loader,
    operator_keypair,
    treasury_pool,
    holder_acc,
    second_holder_acc,
    rw_lock_contract_containerized,
    sender_with_tokens,
    session_user,
    neon_rpc_client,
):
    acc_count = 15
    function_signature = "update_storage(uint256)"
    emulate_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
        sender=sender_with_tokens.eth_address.hex(),
        contract=rw_lock_contract_containerized.eth_address.hex(),
        function_signature=function_signature,
        params=[acc_count],
    )
    signed_tx = make_contract_call_trx(
        evm_loader, sender_with_tokens, rw_lock_contract_containerized, function_signature, [acc_count]
    )
    evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair, treasury_pool, holder_acc, signed_tx, emulate_accounts
    )
    data_accounts = evm_loader.get_data_accounts(emulate_accounts)
    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=rw_lock_contract_containerized.solana_address,
        accounts=data_accounts
        + [rw_lock_contract_containerized.balance_account_address],  # , sender_with_tokens.balance_account_address],
    )
    signed_tx = make_contract_call_trx(
        evm_loader, sender_with_tokens, rw_lock_contract_containerized, function_signature, [acc_count]
    )
    emulate_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
        sender=sender_with_tokens.eth_address.hex(),
        contract=rw_lock_contract_containerized.eth_address.hex(),
        function_signature=function_signature,
        params=[acc_count],
    )
    account_list_for_execution_with_container = [
        rw_lock_contract_containerized.solana_address,
        sender_with_tokens.balance_account_address,
    ]
    assert set(emulate_accounts) == set(account_list_for_execution_with_container)

    operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)
    evm_loader.send_transaction_step_from_instruction(
        operator_keypair,
        operator_balance,
        treasury_pool,
        holder_acc,
        signed_tx,
        account_list_for_execution_with_container,
        500,
        operator_keypair,
    )
    signed_tx2 = make_contract_call_trx(
        evm_loader, sender_with_tokens, rw_lock_contract_containerized, function_signature, [acc_count]
    )
    evm_loader.send_transaction_step_from_instruction(
        operator_keypair,
        operator_balance,
        treasury_pool,
        second_holder_acc,
        signed_tx2,
        account_list_for_execution_with_container,
        500,
        operator_keypair,
    )

    resp1 = evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair,
        treasury_pool,
        holder_acc,
        signed_tx,
        account_list_for_execution_with_container,
    )
    resp2 = evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair,
        treasury_pool,
        second_holder_acc,
        signed_tx2,
        account_list_for_execution_with_container,
    )
    check_transaction_logs_have_text(solana_client=evm_loader, trx=resp1, text="exit_status=0x11")
    check_transaction_logs_have_text(solana_client=evm_loader, trx=resp2, text="exit_status=0x11")
