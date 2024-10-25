import eth_abi
from eth_utils import abi, to_int
from solders.keypair import Keypair

from integration.tests.neon_evm.utils.constants import SOL_CHAIN_ID, SOL_MINT_ID
from integration.tests.neon_evm.utils.scheduled_trx import encode_scheduled_trx
from utils.helpers import pubkey2neon_address


class TestScheduledTrx:
    def test_create_tree_account(
        self,
        evm_loader,
        solana_keypair: Keypair,
        treasury_pool,
        basic_contract,
        neon_api_client,
        operator_keypair,
        holder_acc,
    ):
        neon_address = pubkey2neon_address(solana_keypair.pubkey())
        nonce = evm_loader.get_neon_nonce(neon_address, SOL_CHAIN_ID)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(["uint256"], [contract_data])
        tx = encode_scheduled_trx(
            neon_address,
            None,
            nonce,
            0,
            basic_contract.eth_address,
            value=0,
            call_data=data,
        )

        tree_account = evm_loader.create_tree_account(solana_keypair, neon_address, treasury_pool, tx, SOL_MINT_ID)

        assert len(neon_api_client.get_transaction_tree(neon_address.hex(), nonce)["value"]["transactions"]) == 1

        evm_loader.write_transaction_to_holder_account(tx, holder_acc, operator_keypair)
        additional_accounts = [basic_contract.solana_address, evm_loader.ether2balance(neon_address, SOL_CHAIN_ID)]
        evm_loader.execute_scheduled_trx_from_account(
            0, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts
        )
        evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc)
        #evm_loader.destroy_tree_account(solana_keypair, neon_address, treasury_pool, tree_account)

        data = abi.function_signature_to_4byte_selector('getNumber()')
        result = neon_api_client.emulate(neon_address.hex(),
                                         contract=basic_contract.eth_address.hex(), data=data)
        assert to_int(hexstr=result["result"]) == contract_data

