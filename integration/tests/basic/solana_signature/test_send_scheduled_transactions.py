import allure
import eth_abi
import pytest
from eth_utils import abi

from utils.consts import wSOL
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData


@allure.feature("Solana native")
@allure.story("Test sending scheduled transaction")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestScheduledTrx:
    def test_send_simple_single_trx(self, web3_client_sol, neon_user, common_contract_sol, evm_loader, treasury_pool):

        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        tx = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            0,
            target=common_contract_sol.address,
            call_data=data,
            max_fee_per_gas=3000000000,
            max_priority_fee_per_gas=15,
            gas_limit=3000000

        )
        evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode(), wSOL["address_spl"])
        web3_client_sol.wait_for_transaction_receipt(tx.hash())
        assert common_contract_sol.functions.getNumber().call() == contract_data

    def test_multiple_scheduled_trx(self, web3_client_sol, neon_user, common_contract_sol, evm_loader, treasury_pool):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        trxs = []
        for i in range(1):#4):
            trxs.append(
                ScheduledTransaction(
                    neon_user.neon_address,
                    None,
                    nonce,
                    index=i,
                    target=common_contract_sol.address,
                    value=0,
                    call_data=data,
                    max_fee_per_gas=3000000000,
                    max_priority_fee_per_gas=15,
                    gas_limit=3000000
                )
            )

        tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
        tree_acc_data.add_trx(trxs[0], 0xFFFF, 0)
       # tree_acc_data.add_trx(trxs[1], 3, 0)
       # tree_acc_data.add_trx(trxs[2], 3, 0)
      #  tree_acc_data.add_trx(trxs[3], 0xFFFF, 3)
        tree_account = evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"]
        )
        print(neon_user.checksum_address)
        print(neon_user.neon_address.hex())
        print("tree_account", tree_account)
        web3_client_sol.send_scheduled_transaction(trxs[0].encode())
        resp = web3_client_sol.wait_for_transaction_receipt(trxs[0].hash())