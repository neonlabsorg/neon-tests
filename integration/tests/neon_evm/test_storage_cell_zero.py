import pytest
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from integration.tests.neon_evm.utils.contract import deploy_contract, make_contract_call_trx
from integration.tests.neon_evm.utils.neon_api_client import NeonApiClient
from utils.evm_loader import EvmLoader
from utils.solana_client import SolanaClient
from utils.types import Contract, Caller, TreasuryPool


@pytest.mark.parametrize(
    "function_signature",
    [
        "saveZeroToVar()",
        "saveZeroToMapping()",
        "saveZeroToMappingCycle()",
    ],
)
class TestStorageCells:

    def test_save_zero(
            self,
            operator_keypair: Keypair,
            user_account: Caller,
            evm_loader: EvmLoader,
            treasury_pool: TreasuryPool,
            neon_api_client: NeonApiClient,
            holder_acc: Pubkey,
            sol_client: SolanaClient,
            function_signature: str,
    ):
        # Deploy the contract
        contract: Contract = deploy_contract(
            operator=operator_keypair,
            user=user_account,
            contract_file_name="neon_evm/store_zeros.sol",
            evm_loader=evm_loader,
            treasury_pool=treasury_pool,
            contract_name="saveZeros",
            version="0.8.12",
        )

        # Emulate contract function call transaction
        emulate_result = neon_api_client.emulate_contract_call(
            sender=user_account.eth_address.hex(),
            contract=contract.eth_address.hex(),
            function_signature=function_signature,
        )

        # Define the storage accounts
        emulate_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        non_storage_accounts = (contract.solana_address, user_account.balance_account_address)
        storage_accounts = [acc for acc in emulate_accounts if acc not in non_storage_accounts]

        # Actually execute the transaction
        signed_tx = make_contract_call_trx(
            evm_loader=evm_loader,
            user=user_account,
            contract=contract,
            function_signature=function_signature
        )
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        evm_loader.execute_transaction_steps_from_account(
            operator=operator_keypair,
            treasury=treasury_pool,
            storage_account=holder_acc,
            additional_accounts=emulate_accounts,
        )

        # Make sure the emulated storage accounts were not actually created (have 0 balance)
        for storage_account in storage_accounts:
            balance = evm_loader.get_solana_balance(storage_account)
            assert balance == 0, f"Account {storage_account} was created"
