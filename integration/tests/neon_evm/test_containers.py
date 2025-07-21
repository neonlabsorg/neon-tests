import eth_abi
import pytest

from integration.tests.neon_evm.utils.ethereum import make_contract_call_trx
from integration.tests.neon_evm.utils.transaction_checks import check_transaction_logs_have_text
from utils.evm_loader import EvmLoader


@pytest.fixture(scope="class")
def recipients(evm_loader, operator_keypair):
    return [evm_loader.make_new_user(operator_keypair) for _ in range(12)]


@pytest.fixture(scope="class")
def distributor_contract(
    evm_loader, operator_keypair, session_user, neon_api_client, treasury_pool, holder_acc, recipients
):
    contract = evm_loader.deploy_contract(
        operator_keypair, session_user, "common/NeonDistributor", neon_api_client, treasury_pool, version="0.8.12"
    )
    names = [f"Name_{recipient.eth_address[0:4]}" for recipient in recipients]
    addresses = [recipient.eth_address for recipient in recipients]

    function_signature = "set_addresses(string[],address[])"
    emulate_accounts = neon_api_client.get_additional_accounts_by_emulation(
        sender=session_user.eth_address.hex(),
        contract=contract.eth_address.hex(),
        function_signature=function_signature,
        params=[names, addresses],
    )
    signed_tx = make_contract_call_trx(evm_loader, session_user, contract, function_signature, [names, addresses])
    evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
    evm_loader.execute_transaction_steps_from_account(operator_keypair, treasury_pool, holder_acc, emulate_accounts)
    return contract


@pytest.fixture(scope="class")
def distributor_caller_contract(
    evm_loader: EvmLoader, operator_keypair, session_user, neon_api_client, treasury_pool, distributor_contract
):
    constructor_args = eth_abi.encode(["address"], [distributor_contract.eth_address.hex()])

    return evm_loader.deploy_contract(
        operator_keypair,
        session_user,
        "common/NeonDistributor",
        neon_api_client,
        treasury_pool,
        contract_name="NeonDistributorCaller",
        version="0.8.12",
        encoded_args=constructor_args,
    )


def test_assemble_container_with_data_accounts(
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


def test_allocate_container(
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

    # allocate container and execute transaction with it
    evm_loader.allocate_container(
        operator=operator_keypair, treasury=treasury_pool, container_address=rw_lock_contract.solana_address, size=32
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


def test_assemble_container_with_all_types_of_accounts(
    evm_loader,
    operator_keypair,
    treasury_pool,
    sender_with_tokens,
    neon_api_client,
    distributor_caller_contract,
    distributor_contract,
    holder_acc,
    recipients,
):
    function_signature = "distribute_value()"
    value = 12 * 10
    emulate_accounts = neon_api_client.get_additional_accounts_by_emulation(
        sender=sender_with_tokens.eth_address.hex(),
        contract=distributor_caller_contract.eth_address.hex(),
        function_signature=function_signature,
        value=value,
    )

    data_accounts = evm_loader.get_data_accounts(emulate_accounts)
    balance_accounts = [
        distributor_caller_contract.balance_account_address,
        distributor_contract.balance_account_address,
    ] + [recipient.balance_account_address for recipient in recipients]

    contract_accounts = [distributor_contract.solana_address]
    print("data_accounts:", data_accounts)
    print("balance_accounts:", balance_accounts)
    print("contract_accounts:", contract_accounts)

    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=distributor_caller_contract.solana_address,
        accounts=data_accounts + balance_accounts + contract_accounts,
    )

    accounts_for_execution_with_container = [
        distributor_caller_contract.solana_address,
        sender_with_tokens.solana_account_address,
        sender_with_tokens.balance_account_address,
    ] + [recipient.solana_account_address for recipient in recipients]

    signed_tx = make_contract_call_trx(
        evm_loader, sender_with_tokens, distributor_caller_contract, function_signature, value=value
    )
    resp = evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair,
        treasury_pool,
        holder_acc,
        signed_tx,
        accounts_for_execution_with_container,
    )
    check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")
