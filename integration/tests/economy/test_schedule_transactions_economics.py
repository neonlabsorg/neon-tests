import allure
import pytest
from solana.constants import LAMPORTS_PER_SOL
from utils.helpers import wait_condition, decode_function_signature
from utils.neon_user import NeonUser
from utils.scheduled_trx import CreateTreeAccMultipleData, ScheduledTrxEstimateRequest
from utils.scheduled_trx import ScheduledTransaction
from utils.web3client import BASE_MAX_PRIORITY_FEE
from .const import DEPOSIT_FOR_TREE_ACC_DELETING, TREE_ACC_DELETING_FEE, DEPOSIT_FOR_TRXS_FINISHING
from .steps import (
    assert_profit,
)

from ..basic.helpers.rpc_checks import check_trx_is_success


def sum_balances(w3_client, operator, sender_account, receiver_account=None):
    token_balance = operator.get_token_balance(w3_client)
    if isinstance(sender_account, NeonUser):
        balance_sender = w3_client.get_balance(sender_account.checksum_address)
    else:
        balance_sender = w3_client.get_balance(sender_account)

    if receiver_account is not None:
        return balance_sender + token_balance + w3_client.get_balance(receiver_account)
    else:
        return balance_sender + token_balance


def assert_tokens_volumes_stayed_same(sum_of_tokens_before, sum_of_tokens_after):
    if sum_of_tokens_before > sum_of_tokens_after:
        pytest.fail(f"Tokens volume become LOWER than before, {sum_of_tokens_after - sum_of_tokens_before}")
    elif sum_of_tokens_before < sum_of_tokens_after:
        pytest.fail(f"Tokens volume become MORE than before, {sum_of_tokens_after - sum_of_tokens_before}")
    pass


@allure.story("Operator economy")
class TestScheduledTransactionEconomics:
    @pytest.mark.parametrize("is_dependent", [True, False])
    def test_multiple_scheduled_trx_sols_outside_neon(
        self,
        operator,
        web3_client_sol,
        neon_user,
        increase_storage_contract,
        evm_loader,
        treasury_pool,
        sol_price,
        sol_client,
        is_dependent,
    ):
        evm_loader.create_balance_account(neon_user.neon_address, neon_user.solana_account, evm_loader.sol_chain_id)

        trx_count = 4
        data = decode_function_signature("incWithoutALT()")

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client_sol)

        user_inner_sol_balance_before = web3_client_sol.get_balance(neon_user.checksum_address)
        user_outer_sol_balance_before = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())

        full_volume_before = (
            token_balance_before + user_inner_sol_balance_before + (user_outer_sol_balance_before * LAMPORTS_PER_SOL)
        )

        trx_estimate_obj_list = []
        for i in range(trx_count):
            child_transaction = None if is_dependent else "0xFFFF"
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(
                    neon_user.checksum_address,
                    increase_storage_contract.address,
                    data,
                    child_transaction=child_transaction,
                )
            )

        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)
        trxs = []
        for i in range(trx_count):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )
        for i in range(trx_count):
            child_transaction = i + 1 if is_dependent and i != trx_count - 1 else 0xFFFF
            success_limit = 1 if is_dependent and i != 0 else 0
            tree_acc_data.add_trx(trxs[i], child_transaction, success_limit)

        tree_acc = evm_loader.create_tree_account_multiple(
            neon_user,
            treasury_pool,
            tree_acc_data.data,
        )

        web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            check_trx_is_success(web3_client_sol, evm_loader, trx.hash().hex(), timeout=180)
        wait_condition(lambda: not evm_loader.account_exists(tree_acc), timeout_sec=120, delay=2)

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client_sol)

        user_inner_sol_balance_after = web3_client_sol.get_balance(neon_user.checksum_address)
        user_outer_sol_balance_after = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())

        full_volume_after = (
            token_balance_after + user_inner_sol_balance_after + (user_outer_sol_balance_after * LAMPORTS_PER_SOL)
        )

        additional_expected_spending = (
            (DEPOSIT_FOR_TREE_ACC_DELETING + TREE_ACC_DELETING_FEE) * LAMPORTS_PER_SOL
        ) - DEPOSIT_FOR_TRXS_FINISHING

        diff_volume = full_volume_before - full_volume_after - additional_expected_spending
        assert diff_volume == 0, f"tokens volume not same, diff={diff_volume}"

        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = sol_balance_before - sol_balance_after
        token_diff = web3_client_sol.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)

    def test_multiple_scheduled_trx_sols_inside_neon(
        self,
        operator,
        web3_client_sol,
        increase_storage_contract,
        evm_loader,
        treasury_pool,
        sol_price,
        sol_client,
        neon_user_with_sols_inside_neon,
    ):
        trx_count = 4
        data = decode_function_signature("incWithoutALT()")

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client_sol)

        summ_before = sum_balances(web3_client_sol, operator, neon_user_with_sols_inside_neon)

        trx_estimate_obj_list = []
        for i in range(trx_count):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(
                    neon_user_with_sols_inside_neon.checksum_address,
                    increase_storage_contract.address,
                    data,
                    child_transaction=True,
                )
            )
        estimate_result = web3_client_sol.estimate_scheduled(
            neon_user_with_sols_inside_neon.solana_account.pubkey(), trx_estimate_obj_list
        )
        trxs = []
        for i in range(trx_count):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )
        for i in range(trx_count):
            child_transaction = i + 1
            success_limit = 1
            tree_acc_data.add_trx(trxs[i], child_transaction, success_limit)

        evm_loader.create_tree_account_multiple(
            neon_user_with_sols_inside_neon,
            treasury_pool,
            tree_acc_data.data,
        )
        web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            check_trx_is_success(web3_client_sol, evm_loader, trx.hash().hex(), timeout=180)

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client_sol)

        summ_after = sum_balances(web3_client_sol, operator, neon_user_with_sols_inside_neon)
        diff_volume = summ_before - summ_after + DEPOSIT_FOR_TRXS_FINISHING * trx_count
        assert diff_volume == 0, f"tokens volume not same, diff={diff_volume}"

        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = sol_balance_before - sol_balance_after
        token_diff = web3_client_sol.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)

    def test_multiple_scheduled_trx_with_failed_trx(
        self,
        web3_client_sol,
        neon_user,
        treasury_pool,
        revert_contract_caller,
        event_caller_contract,
        evm_loader,
        operator,
        sol_price,
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        max_priority_fee_per_gas = BASE_MAX_PRIORITY_FEE
        max_fee_per_gas = web3_client_sol.get_max_fee_per_gas()
        gas_limit = 30000000

        call_data_trx0 = decode_function_signature("doAssert()")
        call_data_trx1 = decode_function_signature("indexedArgs()")

        trxs = []
        for i, call_data in enumerate([call_data_trx0, call_data_trx1]):
            trxs.append(
                ScheduledTransaction(
                    neon_user.neon_address,
                    None,
                    nonce,
                    index=i,
                    target=revert_contract_caller.address,
                    call_data=call_data,
                    max_fee_per_gas=max_fee_per_gas,
                    max_priority_fee_per_gas=max_priority_fee_per_gas,
                    gas_limit=gas_limit,
                    chain_id=web3_client_sol.chain_id,
                )
            )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
        )
        tree_acc_data.add_trx(trxs[0], 1, 0)
        tree_acc_data.add_trx(trxs[1], 0xFFFF, 1)

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client_sol)
        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)

        web3_client_sol.send_all_scheduled_transactions(trxs)
        resp2 = web3_client_sol.wait_for_transaction_receipt(trxs[1].hash(), timeout=180)
        assert resp2["status"] == 0

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client_sol)

        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = sol_balance_before - sol_balance_after
        token_diff = web3_client_sol.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)

    def test_scheduled_trx_for_erc20_for_spl_inside_sols(
        self,
        web3_client_sol,
        neon_user_with_sols_inside_neon,
        erc20_spl_mintable,
        evm_loader,
        treasury_pool,
        operator,
        sol_price,
    ):
        operator_inner_balance_before = operator.get_token_balance(web3_client_sol)
        operator_sol_balance_before = operator.get_solana_balance()
        user_inner_sol_balance_b = web3_client_sol.get_balance(neon_user_with_sols_inside_neon.checksum_address)
        full_volume_before = operator_inner_balance_before + user_inner_sol_balance_b

        recipient = NeonUser(evm_loader.loader_id)
        erc20_spl_mintable.approve(erc20_spl_mintable.owner, neon_user_with_sols_inside_neon.checksum_address, 800)

        top_up_in_trx = 400
        amount_to_recipient = 400
        data_0 = data_1 = decode_function_signature(
            "transferFrom(address,address,uint256)",
            [erc20_spl_mintable.owner.address, neon_user_with_sols_inside_neon.checksum_address, top_up_in_trx],
        )
        data_2 = data_3 = decode_function_signature(
            "transfer(address,uint256)", [recipient.checksum_address, amount_to_recipient]
        )

        trx_estimate_0 = ScheduledTrxEstimateRequest(
            neon_user_with_sols_inside_neon.checksum_address,
            erc20_spl_mintable.address,
            data_0,
            child_transaction=hex(2),
        )
        trx_estimate_1 = ScheduledTrxEstimateRequest(
            neon_user_with_sols_inside_neon.checksum_address,
            erc20_spl_mintable.address,
            data_1,
            child_transaction=hex(3),
        )
        trx_estimate_2 = ScheduledTrxEstimateRequest(
            neon_user_with_sols_inside_neon.checksum_address,
            erc20_spl_mintable.address,
            data_2,
            child_transaction="0xFFFF",
        )
        trx_estimate_3 = ScheduledTrxEstimateRequest(
            neon_user_with_sols_inside_neon.checksum_address,
            erc20_spl_mintable.address,
            data_3,
            child_transaction="0xFFFF",
        )
        trx_estimate_obj_list = [trx_estimate_0, trx_estimate_1, trx_estimate_2, trx_estimate_3]

        estimate_result = web3_client_sol.estimate_scheduled(
            neon_user_with_sols_inside_neon.solana_account.pubkey(), trx_estimate_obj_list
        )

        trxs = []
        for i in range(len(trx_estimate_obj_list)):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )

        tree_acc_data.add_trx(trxs[0], 2, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 0xFFFF, 1)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 1)

        evm_loader.create_tree_account_multiple(neon_user_with_sols_inside_neon, treasury_pool, tree_acc_data.data)
        web3_client_sol.send_all_scheduled_transactions(trxs)

        for trx in trxs:
            check_trx_is_success(web3_client_sol, evm_loader, trx.hash().hex(), timeout=180)

        operator_inner_balance_after = operator.get_token_balance(web3_client_sol)
        operator_sol_balance_after = operator.get_solana_balance()

        user_inner_sol_balance_after = web3_client_sol.get_balance(neon_user_with_sols_inside_neon.checksum_address)
        full_volume_after = operator_inner_balance_after + user_inner_sol_balance_after
        diff_volume = full_volume_before - full_volume_after + DEPOSIT_FOR_TRXS_FINISHING * 4
        assert diff_volume == 0, f"tokens volume not same, diff={diff_volume}"

        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = operator_sol_balance_before - operator_sol_balance_after
        token_diff = web3_client_sol.to_main_currency(operator_inner_balance_after - operator_inner_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)

    def test_scheduled_trx_for_erc20_for_spl_outside_sols(
        self,
        web3_client_sol,
        neon_user,
        erc20_spl_mintable,
        evm_loader,
        treasury_pool,
        operator,
        sol_price,
    ):
        operator_inner_balance_before = operator.get_token_balance(web3_client_sol)
        operator_sol_balance_before = operator.get_solana_balance()
        user_inner_sol_balance_b = web3_client_sol.get_balance(neon_user.checksum_address)
        full_volume_before = operator_inner_balance_before + user_inner_sol_balance_b

        recipient = NeonUser(evm_loader.loader_id)
        erc20_spl_mintable.approve(erc20_spl_mintable.owner, neon_user.checksum_address, 800)

        top_up_in_trx = 400
        amount_to_recipient = 400
        data_0 = data_1 = decode_function_signature(
            "transferFrom(address,address,uint256)",
            [erc20_spl_mintable.owner.address, neon_user.checksum_address, top_up_in_trx],
        )
        data_2 = data_3 = decode_function_signature(
            "transfer(address,uint256)", [recipient.checksum_address, amount_to_recipient]
        )

        trx_estimate_0 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable.address, data_0, child_transaction=hex(2)
        )
        trx_estimate_1 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable.address, data_1, child_transaction=hex(3)
        )
        trx_estimate_2 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable.address, data_2, child_transaction="0xFFFF"
        )
        trx_estimate_3 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable.address, data_3, child_transaction="0xFFFF"
        )
        trx_estimate_obj_list = [trx_estimate_0, trx_estimate_1, trx_estimate_2, trx_estimate_3]

        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)

        trxs = []
        for i in range(len(trx_estimate_obj_list)):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )

        tree_acc_data.add_trx(trxs[0], 2, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 0xFFFF, 1)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 1)

        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)
        web3_client_sol.send_all_scheduled_transactions(trxs)

        for trx in trxs:
            check_trx_is_success(web3_client_sol, evm_loader, trx.hash().hex(), timeout=180)

        operator_inner_balance_after = operator.get_token_balance(web3_client_sol)
        operator_sol_balance_after = operator.get_solana_balance()

        user_inner_sol_balance_after = web3_client_sol.get_balance(neon_user.checksum_address)
        full_volume_after = operator_inner_balance_after + user_inner_sol_balance_after
        diff_volume = full_volume_before - full_volume_after + DEPOSIT_FOR_TRXS_FINISHING * 4
        assert diff_volume == 0, f"tokens volume not same, diff={diff_volume}"

        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = operator_sol_balance_before - operator_sol_balance_after
        token_diff = web3_client_sol.to_main_currency(operator_inner_balance_after - operator_inner_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)

    def test_scheduled_trx_send_value(
        self,
        web3_client_sol,
        evm_loader,
        treasury_pool,
        operator,
        sol_price,
        event_caller_sol_chain,
        neon_user_with_sols_inside_neon,
    ):
        sum_of_tokens_before = sum_balances(web3_client_sol, operator, neon_user_with_sols_inside_neon)
        call_data = decode_function_signature("indexedArgs()")
        value = 100000

        trx_estimate_obj = ScheduledTrxEstimateRequest(
            neon_user_with_sols_inside_neon.checksum_address, event_caller_sol_chain.address, call_data, value=value
        )
        estimate_result = web3_client_sol.estimate_scheduled(
            neon_user_with_sols_inside_neon.solana_account.pubkey(), [trx_estimate_obj]
        )

        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )
        tree_acc_data.add_trx(tx, 0xFFFF, 0)
        evm_loader.create_tree_account_multiple(neon_user_with_sols_inside_neon, treasury_pool, tree_acc_data.data)
        web3_client_sol.send_scheduled_transaction(tx)
        check_trx_is_success(web3_client_sol, evm_loader, tx.hash().hex())
        web3_client_sol.wait_for_transaction_receipt(tx.hash(), timeout=180)

        sum_of_tokens_after = sum_balances(web3_client_sol, operator, neon_user_with_sols_inside_neon)

        diff = sum_of_tokens_before - sum_of_tokens_after + DEPOSIT_FOR_TRXS_FINISHING - value
        assert diff == 0, f"tokens volume not same, diff={diff}"
