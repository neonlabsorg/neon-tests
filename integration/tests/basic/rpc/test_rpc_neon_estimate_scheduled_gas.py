import allure
import pytest
from solana.transaction import Transaction
from solders.pubkey import Pubkey
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address, create_associated_token_account, approve, ApproveParams

from integration.tests.basic.helpers.rpc_checks import assert_fields_are_hex
from utils.helpers import decode_function_signature
from utils.neon_user import NeonUser
from utils.scheduled_trx import ScheduledTrxEstimateRequest


@allure.feature("JSON-RPC validation")
@allure.story("Verify JSON-RPC neon_estimateScheduledGas work")
@pytest.mark.neon_only
class TestNeonRPCEstimateScheduledGas:
    def test_estimate_with_preparatory_solana_transactions(
        self, web3_client_sol, neon_user, erc20_spl_mintable_new, evm_loader, treasury_pool
    ):
        recipient = NeonUser(evm_loader.loader_id)
        ata_amount = 1_000
        erc20_spl_mintable_new.approve(erc20_spl_mintable_new.account, neon_user.checksum_address, ata_amount)

        my_ata = get_associated_token_address(
            neon_user.solana_account.pubkey(), erc20_spl_mintable_new.token_mint_pubkey
        )
        solana_contract_account = Pubkey.from_string(
            evm_loader.ether2program(erc20_spl_mintable_new.contract.address)[0]
        )

        trx = Transaction()
        trx.add(
            create_associated_token_account(
                neon_user.solana_account.pubkey(),
                neon_user.solana_account.pubkey(),
                erc20_spl_mintable_new.token_mint_pubkey,
            )
        )
        trx.add(
            approve(
                ApproveParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=my_ata,
                    delegate=solana_contract_account,
                    owner=neon_user.solana_account.pubkey(),
                    amount=ata_amount,
                )
            )
        )

        data1 = decode_function_signature(
            "transferSolanaFrom(address,bytes32,uint64)",
            [erc20_spl_mintable_new.account.address, bytes(my_ata), ata_amount],
        )
        data2 = decode_function_signature("transfer(address,uint256)", [recipient.checksum_address, ata_amount])

        trx_estimate_obj1 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable_new.address, data1
        )
        trx_estimate_obj2 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable_new.address, data2
        )

        resp = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(),
            [trx_estimate_obj1, trx_estimate_obj2],
            preparatory_solana_trxs=trx.instructions,
        )
        assert len(resp["gasList"]) == 2, f"Amount of transactions must be 1, but actual amount = {2}"

        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        assert resp["nonce"] == hex(nonce)
        assert_fields_are_hex(resp, ["chainId", "maxFeePerGas", "maxPriorityFeePerGas", "nonce", "treasuryIndex"])

    def test_estimate_transfer_trx_without_approval_in_preparatory_sol_trx_list(
        self, web3_client_sol, neon_user, erc20_spl_mintable_new, evm_loader, treasury_pool
    ):
        recipient = NeonUser(evm_loader.loader_id)
        ata_amount = 1_000
        erc20_spl_mintable_new.approve(erc20_spl_mintable_new.account, neon_user.checksum_address, ata_amount)

        my_ata = get_associated_token_address(
            neon_user.solana_account.pubkey(), erc20_spl_mintable_new.token_mint_pubkey
        )

        data1 = decode_function_signature(
            "transferSolanaFrom(address,bytes32,uint64)",
            [erc20_spl_mintable_new.account.address, bytes(my_ata), ata_amount],
        )
        data2 = decode_function_signature("transfer(address,uint256)", [recipient.checksum_address, ata_amount])

        trx_estimate_obj1 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable_new.address, data1
        )
        trx_estimate_obj2 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable_new.address, data2
        )

        with pytest.raises(AssertionError, match="External call fails"):
            web3_client_sol.estimate_scheduled(
                neon_user.solana_account.pubkey(),
                [trx_estimate_obj1, trx_estimate_obj2],
            )
