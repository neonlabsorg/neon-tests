import pytest


@pytest.fixture(scope="class")
def nested_call_contracts(accounts, web3_client):
    contract_a, _ = web3_client.deploy_and_get_contract(
        "common/NestedCallsChecker", "0.8.12", accounts[0], contract_name="A"
    )
    contract_b, _ = web3_client.deploy_and_get_contract(
        "common/NestedCallsChecker", "0.8.12", accounts[0], contract_name="B"
    )
    contract_c, _ = web3_client.deploy_and_get_contract(
        "common/NestedCallsChecker", "0.8.12", accounts[0], contract_name="C"
    )
    yield contract_a, contract_b, contract_c


@pytest.fixture(scope="function")
def recursion_factory(accounts, web3_client):
    sender_account = accounts[0]
    contract, _ = web3_client.deploy_and_get_contract(
        "common/Recursion",
        "0.8.10",
        sender_account,
        contract_name="DeployRecursionFactory",
        constructor_args=[3],
    )
    yield contract


@pytest.fixture(scope="function")
def destroyable_contract(accounts, web3_client):
    sender_account = accounts[0]
    contract, _ = web3_client.deploy_and_get_contract(
        "opcodes/SelfDestroyable", "0.8.10", sender_account, "SelfDestroyable"
    )
    yield contract


@pytest.fixture(scope="class")
def expected_error_checker(accounts, web3_client):
    contract, _ = web3_client.deploy_and_get_contract(
        "common/ExpectedErrorsChecker", "0.8.12", accounts[0], contract_name="A"
    )
    yield contract
