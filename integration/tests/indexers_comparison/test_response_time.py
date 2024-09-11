import time

from utils import helpers
from utils.helpers import wait_condition

REPEAT_COUNT = 10

def test_erc20_simple_trx(erc20_spl_mintable, endpoints, accounts, web3_client):
    def sent_erc20_simple_trx():
        signer = accounts[0]
        address_to = web3_client.create_account().address
        amount = 1
        tx = web3_client.make_raw_tx(signer.address)
        instruction_tx = erc20_spl_mintable.contract.functions.transfer(address_to, amount).build_transaction(tx)
        signed_tx = web3_client._web3.eth.account.sign_transaction(instruction_tx, signer.key)
        return web3_client._web3.eth.send_raw_transaction(signed_tx.rawTransaction).hex()

    trx_hash = sent_erc20_simple_trx()
    print(trx_hash)
    response_time_ba = get_time_to_get_receipt(endpoints[1], trx_hash)
    print(f"BA response time: {response_time_ba}")

    trx_hash = sent_erc20_simple_trx()
    response_time_neon = get_time_to_get_receipt(endpoints[0], trx_hash)
    print(f"Neon response time: {response_time_neon}")
    assert response_time_ba <= response_time_neon


def test_iterative_trx_contract_deploy(endpoints, web3_client, accounts):
    def sent_iterative_trx_contract_deploy():
        signer = accounts[0]
        contract_interface = helpers.get_contract_interface(
            "EIPs/ERC3475",
            "0.8.10"
        )
        contract = web3_client._web3.eth.contract(abi=contract_interface["abi"],
                                                  bytecode=contract_interface["bin"])
        tx = web3_client.make_raw_tx(signer.address)
        transaction = contract.constructor().build_transaction(tx)
        signed_tx = web3_client._web3.eth.account.sign_transaction(transaction, signer.key)
        return web3_client._web3.eth.send_raw_transaction(signed_tx.rawTransaction).hex()

    trx_hash = sent_iterative_trx_contract_deploy()
    print(trx_hash)
    response_time_ba = get_time_to_get_receipt(endpoints[1], trx_hash)
    print(f"BA response time: {response_time_ba}")

    trx_hash = sent_iterative_trx_contract_deploy()
    response_time_neon = get_time_to_get_receipt(endpoints[0], trx_hash)
    print(f"Neon response time: {response_time_neon}")
    assert response_time_ba <= response_time_neon


def test_big_iterative_trx(endpoints, web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract(
        contract="common/Common", version="0.8.12", contract_name="MappingActions", account=accounts[1]
    )

    def sent_big_iterative_trx():
        signer = accounts[0]
        value = 25
        tx = web3_client.make_raw_tx(signer.address)
        instruction_tx = contract.functions.replaceValues(value).build_transaction(tx)
        signed_tx = web3_client.eth.account.sign_transaction(instruction_tx, signer.key)
        return web3_client.eth.send_raw_transaction(signed_tx.rawTransaction).hex()

    trx_hash = sent_big_iterative_trx()
    print(trx_hash)
    response_time_ba = get_time_to_get_receipt(endpoints[1], trx_hash)
    print(f"BA response time: {response_time_ba}")

    trx_hash = sent_big_iterative_trx()

    response_time_neon = get_time_to_get_receipt(endpoints[0], trx_hash)
    print(f"Neon response time: {response_time_neon}")
    assert response_time_ba <= response_time_neon


def get_time_to_get_receipt(endpoint, trx_hash):
    time_before = time.time()
    wait_condition(lambda: endpoint["client"].send_rpc("eth_getTransactionReceipt",
                                                       params=trx_hash)["result"] is not None, delay=0.1)
    time_after = time.time()
    return time_after - time_before
