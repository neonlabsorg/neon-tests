from solders.pubkey import Pubkey

from integration.tests.neon_evm.utils.ethereum import make_contract_call_trx
from integration.tests.neon_evm.utils.transaction_checks import (
    check_transaction_logs_not_have_text,
)

from utils.types import Contract


class TestAccountListWithBlockhash:

    def test_account_list_with_blockhash(
        self, evm_loader, user_account, operator_keypair, treasury_pool, holder_acc, neon_api_client, sol_client
    ):
        contract: Contract = evm_loader.deploy_contract(
            operator=operator_keypair,
            user=user_account,
            contract_file_name="opcodes/BlockHash.sol",
            neon_api_client=neon_api_client,
            treasury_pool=treasury_pool,
            contract_name="BlockHashTest",
            version="0.8.10",
        )

        signed_tx = make_contract_call_trx(evm_loader, user_account, contract, "getValues(uint256)", params=[10])
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        emulate_result = neon_api_client.emulate_contract_call(
            user_account.eth_address.hex(), contract.eth_address.hex(), "getValues(uint256)", params=[10]
        )

        acc_from_emulation = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        for account in acc_from_emulation:
            assert "SysvarS1otHashes111111111111111111111111111account" not in str(account)
        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, holder_acc, acc_from_emulation
        )
        check_transaction_logs_not_have_text(
            solana_client=evm_loader, trx=resp, text="SysvarS1otHashes111111111111111111111111111account"
        )
