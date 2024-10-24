
import eth_abi
from eth_utils import abi
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
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(["uint256"], [1])
        tx = encode_scheduled_trx(
            neon_address,
            None,
            nonce,
            0,
            basic_contract.eth_address,
            value=0,
            call_data=data,
        )

        evm_loader.create_tree_account(solana_keypair, neon_address, treasury_pool, tx, SOL_MINT_ID)

        assert len(neon_api_client.get_transaction_tree(neon_address.hex(), nonce)["value"]["transactions"]) == 1

