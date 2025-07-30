import pytest
from solders.pubkey import Pubkey


@pytest.fixture(scope="class")
def alt_contract(accounts, web3_client):
    contract, _ = web3_client.deploy_and_get_contract("common/ALT", "0.8.10", account=accounts[0], constructor_args=[8])
    return contract


@pytest.fixture(scope="class")
def rw_lock_contract_containerized(evm_loader, solana_account, treasury_pool, web3_client, accounts, operator):
    sender = accounts[0]
    contract, _ = web3_client.deploy_and_get_contract("neon_evm/rw_lock", "0.8.10", account=sender)

    tx = web3_client.make_raw_tx(accounts[0].address)
    instruction_tx = contract.functions.update_storage(20).build_transaction(tx)
    signed_tx = web3_client.eth.account.sign_transaction(instruction_tx, sender.key)
    result = web3_client.get_neon_emulate(str(signed_tx.raw_transaction.hex()))
    accounts = [Pubkey.from_string(item["pubkey"]) for item in result["result"]["solanaAccounts"]]

    web3_client.send_transaction(sender, instruction_tx)

    container_address = evm_loader.ether2program(contract.address[2:])
    data_accounts = evm_loader.get_data_accounts(accounts)
    evm_loader.assemble_container(
        operator=operator.operator_keypairs[0],
        treasury=treasury_pool,
        container_address=container_address,
        accounts=data_accounts + [evm_loader.ether2balance(contract.address[2:])],
    )
    return contract


@pytest.fixture(scope="class")
def distributor_contract(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract(
        contract="common/NeonDistributor.sol",
        version="0.8.12",
        account=accounts[0],
    )
    return contract


@pytest.fixture(scope="class")
def alt_contract_containerized(accounts, web3_client, evm_loader, operator, treasury_pool):
    contract, _ = web3_client.deploy_and_get_contract(
        "common/ALT", "0.8.10", account=accounts[0], constructor_args=[50]
    )

    container_address = evm_loader.ether2program(contract.address[2:])
    tx = web3_client.make_raw_tx(accounts[0].address)
    instruction_tx = contract.functions.fill(30).build_transaction(tx)
    signed_tx = web3_client.eth.account.sign_transaction(instruction_tx, accounts[0].key)
    result = web3_client.get_neon_emulate(str(signed_tx.raw_transaction.hex()))
    sol_accounts = [Pubkey.from_string(item["pubkey"]) for item in result["result"]["solanaAccounts"]]
    sol_accounts = list(set(sol_accounts) - {container_address})
    evm_loader.assemble_container(operator.operator_keypairs[0], treasury_pool, container_address, sol_accounts)

    return contract


@pytest.fixture(scope="class")
def storage_resize_checker(web3_client, accounts):
    caller_contract, _ = web3_client.deploy_and_get_contract(
        "common/StorageResizeChecker", "0.8.20", contract_name="Caller", account=accounts[0]
    )
    return caller_contract
