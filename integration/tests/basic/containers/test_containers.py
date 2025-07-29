import allure
import pytest
from solders.pubkey import Pubkey

from integration.tests.basic.helpers.rpc_checks import check_trx_is_success
from utils.accounts import EthAccounts
from utils.consts import AccountType
from utils.helpers import decode_function_signature, wait_condition
from utils.scheduled_trx import ScheduledTrxEstimateRequest, CreateTreeAccMultipleData, ScheduledTransaction
from utils.web3client import NeonChainWeb3Client


@allure.feature("Containers")
@allure.story("Send trxs with containers")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestContainers:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    def test_change_data_accounts_in_container(self, rw_lock_contract_containerized):
        sender = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender)
        instruction_tx = rw_lock_contract_containerized.functions.update_storage(20).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender, instruction_tx)
        assert receipt["status"] == 1, "Transaction should be successful"

    def test_use_acc_after_adding_it_to_container(
        self, accounts, distributor_contract, evm_loader, treasury_pool, operator
    ):
        acc_in_container = accounts[1]
        balance_before = self.web3_client.get_balance(acc_in_container.address)

        sender = accounts[0]
        tx = self.web3_client.make_raw_tx(sender)
        instruction_tx = distributor_contract.functions.set_address(
            "alice", bytes.fromhex(acc_in_container.address[2:])
        ).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender, instruction_tx)
        assert receipt["status"] == 1, "Transaction should be successful"

        container_address = Pubkey.from_string(evm_loader.ether2program(distributor_contract.address[2:])[0])
        evm_loader.assemble_container(
            operator=operator.operator_keypairs[0],
            treasury=treasury_pool,
            container_address=container_address,
            accounts=[evm_loader.ether2balance(acc_in_container.address[2:])],
        )
        amount = 300
        tx = self.web3_client.make_raw_tx(sender, amount=amount)
        instruction_tx = distributor_contract.functions.distribute_value().build_transaction(tx)

        receipt = self.web3_client.send_transaction(sender, instruction_tx)
        assert receipt["status"] == 1, "Transaction should be successful"
        balance_after = self.web3_client.get_balance(acc_in_container.address)
        assert balance_after == balance_before + amount, "Balance should be updated correctly"

        # sign trx by account added to container
        tx = self.web3_client.make_raw_tx(acc_in_container, amount=amount)
        instruction_tx = distributor_contract.functions.distribute_value().build_transaction(tx)

        receipt = self.web3_client.send_transaction(acc_in_container, instruction_tx)
        assert receipt["status"] == 1, "Transaction should be successful"

    def test_big_count_of_accounts_in_container(
        self, accounts, alt_contract_containerized, evm_loader, treasury_pool, operator
    ):
        container_address = Pubkey.from_string(evm_loader.ether2program(alt_contract_containerized.address[2:])[0])

        for n in [50, 75, 100, 125, 150]:
            tx = self.web3_client.make_raw_tx(accounts[0].address)
            instruction_tx = alt_contract_containerized.functions.fill(n).build_transaction(tx)
            signed_tx = self.web3_client.eth.account.sign_transaction(instruction_tx, accounts[0].key)
            result = self.web3_client.get_neon_emulate(str(signed_tx.raw_transaction.hex()))
            sol_accounts = [Pubkey.from_string(item["pubkey"]) for item in result["result"]["solanaAccounts"]]
            ref_acc = evm_loader.filter_neon_accounts_by_type(sol_accounts, AccountType.REFERENCE)
            sol_accounts = list(set(sol_accounts) - set(ref_acc) - {container_address})
            self.web3_client.send_transaction(accounts[0], instruction_tx)
            evm_loader.assemble_container(operator.operator_keypairs[0], treasury_pool, container_address, sol_accounts)

        tx = self.web3_client.make_raw_tx(accounts[0].address)
        instruction_tx = alt_contract_containerized.functions.fill(175).build_transaction(tx)
        self.web3_client.send_transaction(accounts[0], instruction_tx)

    def test_scheduled_trx_with_container(
        self, neon_user, alt_contract_containerized, treasury_pool, web3_client_sol, evm_loader, operator
    ):
        func_name = "fill(uint256)"
        data1 = decode_function_signature(func_name, [14])
        data2 = decode_function_signature(func_name, [30])
        data3 = decode_function_signature(func_name, [20])
        data4 = decode_function_signature(func_name, [20])

        trx_estimate_obj_list = []
        for data in [data1, data2, data3]:
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(
                    neon_user.checksum_address, alt_contract_containerized.address, data, child_transaction=hex(3)
                )
            )
        trx_estimate_obj_list.append(
            ScheduledTrxEstimateRequest(
                neon_user.checksum_address, alt_contract_containerized.address, data4, child_transaction="0xFFFF"
            )
        )
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)
        trxs = []
        for i in range(4):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )

        tree_acc_data.add_trx(trxs[0], 3, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 3, 0)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 3)

        tree_account = evm_loader.create_tree_account_multiple(
            neon_user,
            treasury_pool,
            tree_acc_data.data,
        )

        # evm_loader.assemble_container(
        #     operator.operator_keypairs[0],
        #     treasury_pool,
        #     Pubkey.from_string(evm_loader.ether2program(alt_contract_containerized.address[2:])[0]),
        #     [evm_loader.ether2balance(neon_user.neon_address, web3_client_sol.chain_id)],
        # )

        web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            check_trx_is_success(web3_client_sol, evm_loader, trx.hash().hex(), timeout=120)

        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=2)

    def test_erc20_for_spl_containerized(self, accounts, evm_loader, multiple_actions_erc20, treasury_pool, operator):

        acc_1, contract = multiple_actions_erc20
        acc_2 = accounts[2]
        mint_amount = 1000
        transfer_amount_1 = 300
        transfer_amount_2 = 200

        container_address = Pubkey.from_string(evm_loader.ether2program(contract.address[2:])[0])
        erc20_address = contract.functions.getErc20Address().call()
        erc20_sol_address = Pubkey.from_string(evm_loader.ether2program(erc20_address[2:])[0])
        print("multiple_actions_erc20 address:", container_address)
        print("erc20 address:", erc20_sol_address)

        tx = self.web3_client.make_raw_tx(acc_1)
        instruction_tx = contract.functions.mintTransferTransfer(
            mint_amount,
            acc_1.address,
            transfer_amount_1,
            acc_2.address,
            transfer_amount_2,
        ).build_transaction(tx)

        signed_tx = self.web3_client.eth.account.sign_transaction(instruction_tx, acc_1.key)
        result = self.web3_client.get_neon_emulate(str(signed_tx.raw_transaction.hex()))
        sol_accounts = [Pubkey.from_string(item["pubkey"]) for item in result["result"]["solanaAccounts"]]
        data_accounts = evm_loader.filter_neon_accounts_by_type(sol_accounts, AccountType.STORAGE)
        balance_acc = evm_loader.filter_neon_accounts_by_type(sol_accounts, AccountType.USER_BALANCE)
        contract_accounts = evm_loader.filter_neon_accounts_by_type(sol_accounts, AccountType.CONTRACT)
        print("data accounts:", len(data_accounts))
        print("balance accounts:", len(balance_acc))
        print("contract accounts:", len(contract_accounts))

        evm_loader.assemble_container(
            operator.operator_keypairs[0],
            treasury_pool,
            container_address,
            [erc20_sol_address],
        )

        receipt = self.web3_client.send_transaction(acc_1, instruction_tx)
        assert receipt["status"] == 1, "Transaction should be successful"
