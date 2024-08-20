import json

import allure
import pytest
from solana.transaction import AccountMeta, Transaction, TransactionInstruction

from utils.consts import TEST_INVOKE_ID
from utils.instructions import make_ExecuteTrxFromInstruction
from utils.solana_client import SolanaClient
from utils.web3client import NeonChainWeb3Client

from .utils.ethereum import make_eth_transaction


@pytest.mark.usefixtures("sol_client", "web3_client")
class TestExternalCall:
    sol_client: SolanaClient
    web3_client: NeonChainWeb3Client

    def test_execute_from_instruction(
        self, operator_keypair, evm_loader, treasury_pool, sender_with_tokens, session_user, holder_acc
    ):
        operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)
        amount = 1

        msg = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, amount)
        json_data = self.sol_client.get_account_whole_info(holder_acc)
        json_str = json.dumps(json_data, indent=4)
        allure.attach(json_str, "holder_acc", allure.attachment_type.JSON)
        accounts = [
            sender_with_tokens.solana_account_address,
            sender_with_tokens.balance_account_address,
            session_user.solana_account_address,
            session_user.balance_account_address,
        ]

        sender_initial_balance = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        receiver_initial_balance = evm_loader.get_neon_balance(session_user.eth_address)

        instruction = make_ExecuteTrxFromInstruction(
            operator_keypair,
            operator_balance,
            holder_acc,
            evm_loader.loader_id,
            treasury_pool.account,
            treasury_pool.buffer,
            msg.rawTransaction,
            accounts,
        )
        upd_instruction = TransactionInstruction(
            keys=[AccountMeta(evm_loader.loader_id, is_signer=False, is_writable=True)] + instruction.keys,
            program_id=TEST_INVOKE_ID,
            data=instruction.data,
        )
        trx = Transaction()

        trx.add(upd_instruction)
        self.sol_client.send_tx(trx, operator_keypair)

        assert sender_initial_balance == evm_loader.get_neon_balance(sender_with_tokens.eth_address) + amount
        assert receiver_initial_balance == evm_loader.get_neon_balance(session_user.eth_address) - amount