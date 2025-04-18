from solana.rpc.commitment import Confirmed
from solders.rpc.responses import GetTransactionResp
from solders.signature import Signature
from web3.contract import Contract

from utils.accounts import EthAccounts
from utils.helpers import wait_condition, hasattr_recursive
from utils.solana_client import SolanaClient
from utils.web3client import NeonChainWeb3Client


def get_sol_trx_with_alt(web3_client, sol_client, web3_transaction_receipt):
    solana_trx = web3_client.get_solana_trx_by_neon(web3_transaction_receipt["transactionHash"].hex())
    sol_trx_with_alt = None

    wait_condition(
        lambda: sol_client.get_transaction(
            Signature.from_string(solana_trx["result"][0]), max_supported_transaction_version=0, commitment=Confirmed
        )
        != GetTransactionResp(None)
    )

    for trx in solana_trx["result"]:
        trx_sol = sol_client.get_transaction(
            Signature.from_string(trx), max_supported_transaction_version=0, commitment=Confirmed
        )
        if (
            hasattr_recursive(trx_sol, "value.transaction.transaction.message.address_table_lookups")
            and trx_sol.value.transaction.transaction.message.address_table_lookups
        ):
            sol_trx_with_alt = trx_sol
    if not sol_trx_with_alt:
        print(f"There are no lookup table for {solana_trx}")
        return None

    return sol_trx_with_alt


class TestTrxsWithDifferentAccountsNumber:
    def test_trx_with_many_accounts(
        self,
        sol_client: SolanaClient,
        web3_client: NeonChainWeb3Client,
        accounts: EthAccounts,
        alt_contract: Contract,
    ):
        """Trigger transaction than requires more than 30 accounts"""
        sender_account = accounts[1]
        accounts_quantity = 55
        tx = web3_client.make_raw_tx(from_=sender_account)

        instr = alt_contract.functions.fill(accounts_quantity).build_transaction(tx)
        receipt = web3_client.send_transaction(sender_account, instr)

        sol_trx_with_alt = get_sol_trx_with_alt(web3_client, sol_client, receipt)
        assert sol_trx_with_alt is not None, "There are no lookup table for alt transaction"

        alt_address = sol_trx_with_alt.value.transaction.transaction.message.address_table_lookups[0].account_key
        print(f"alt_address: {alt_address}")
        print("trx hash", receipt["transactionHash"].hex())
        # sol_trx = web3_client.get_solana_trx_by_neon(receipt["transactionHash"].hex())['result'][0]
        # acc_count = len(
        #     sol_client.get_transaction(
        #         Signature.from_string(sol_trx), max_supported_transaction_version=0, commitment=Confirmed
        #     ).value.transaction.transaction.message.account_keys
        # )
        # assert acc_count > 30, "Transaction has less than 30 accounts"

        assert receipt["status"] == 1, "Transaction failed"
