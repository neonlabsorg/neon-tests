import pytest
from solana.transaction import AccountMeta, TransactionInstruction

import allure
from integration.tests.basic.helpers.rpc_checks import assert_instructions
from utils.accounts import EthAccounts
from utils.consts import COUNTER_ID
from utils.helpers import (
    bytes32_to_solana_pubkey,
    gen_hash_of_block,
    generate_text,
    serialize_instruction,
)
from utils.models.result import NeonGetTransactionResult, SolanaByNeonTransaction
from utils.solana_client import SolanaClient
from utils.web3client import NeonChainWeb3Client


@allure.feature("JSON-RPC validation")
@allure.story("Verify events")
@pytest.mark.usefixtures("accounts", "web3_client", "sol_client")
@pytest.mark.neon_only
class TestInstruction:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    sol_client: SolanaClient

    def test_events_for_trx_with_transfer(self, json_rpc_client):
        # TxExecFromData
        sender_account, receiver_account = self.accounts[0], self.accounts[1]
        tx = self.web3_client.make_raw_tx(sender_account, receiver_account, amount=1000000, estimate_gas=True)
        resp = self.web3_client.send_transaction(sender_account, tx)

        response = json_rpc_client.get_solana_trx_by_neon(resp["transactionHash"])
        solana_transactions = SolanaByNeonTransaction(**response)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        solana_trxs_by_neon = [trx.solanaTransactionSignature for trx in validated_response.result.solanaTransactions]
        assert set(solana_transactions.result) == set(solana_trxs_by_neon)
        assert_instructions(validated_response)

    def test_contract_iterative_tx(self, counter_contract, json_rpc_client):
        # TxStepFromData
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, estimate_gas=True)

        instruction_tx = counter_contract.functions.moreInstructionWithLogs(5, 2000).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        response = json_rpc_client.get_solana_trx_by_neon(resp["transactionHash"])
        solana_transactions = SolanaByNeonTransaction(**response)

        solana_trxs_by_neon = [trx.solanaTransactionSignature for trx in validated_response.result.solanaTransactions]
        assert set(solana_transactions.result) == set(solana_trxs_by_neon)
        assert_instructions(validated_response)

    def test_event_cancel(self, json_rpc_client, expected_error_checker):
        # CancelWithHash
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = expected_error_checker.functions.method1().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        validated_response = NeonGetTransactionResult(**response)

        response = json_rpc_client.get_solana_trx_by_neon(resp["transactionHash"])
        solana_transactions = SolanaByNeonTransaction(**response)

        assert_instructions(validated_response)
        solana_trxs_by_neon = [trx.solanaTransactionSignature for trx in validated_response.result.solanaTransactions]
        assert set(solana_transactions.result) == set(solana_trxs_by_neon)

    def test_counter_execute_with_get_return_data(self, call_solana_caller, counter_resource_address, json_rpc_client):
        # TxExecFromDataSolanaCall
        sender = self.accounts[0]
        lamports = 0

        instruction = TransactionInstruction(
            program_id=COUNTER_ID,
            keys=[
                AccountMeta(counter_resource_address, is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.execute_with_get_return_data(
            lamports, serialized
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        event_logs = call_solana_caller.events.LogData().process_receipt(resp)
        assert bytes32_to_solana_pubkey(event_logs[0].args.program.hex()) == COUNTER_ID

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        response = json_rpc_client.get_solana_trx_by_neon(resp["transactionHash"])
        solana_transactions = SolanaByNeonTransaction(**response)

        assert_instructions(validated_response)
        solana_trxs_by_neon = [trx.solanaTransactionSignature for trx in validated_response.result.solanaTransactions]
        assert set(solana_transactions.result) == set(solana_trxs_by_neon)

    def test_contract_tx_no_chain(self, counter_contract, json_rpc_client):
        # HolderWrite, TxStepFromAccountNoChainId
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, estimate_gas=True)
        tx["chainId"] = None

        instruction_tx = counter_contract.functions.moreInstructionWithLogs(0, 3).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        response = json_rpc_client.get_solana_trx_by_neon(resp["transactionHash"])
        solana_transactions = SolanaByNeonTransaction(**response)

        assert_instructions(validated_response)
        solana_trxs_by_neon = [trx.solanaTransactionSignature for trx in validated_response.result.solanaTransactions]
        assert set(solana_transactions.result) == set(solana_trxs_by_neon)

    def test_transfer_mint(self, multiple_actions_erc721, json_rpc_client):
        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc721

        tx = self.web3_client.make_raw_tx(sender_account)
        seed = self.web3_client.text_to_bytes32(gen_hash_of_block(8))
        uri = generate_text(min_len=10, max_len=200)
        instruction_tx = contract.functions.mint(seed, uri).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)
        token_id = contract.functions.lastTokenId().call()

        tx = self.web3_client.make_raw_tx(sender_account)
        seed = self.web3_client.text_to_bytes32(gen_hash_of_block(8))
        uri = generate_text(min_len=10, max_len=200)
        instruction_tx = contract.functions.transferMint(acc.address, seed, token_id, uri).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        response = json_rpc_client.get_solana_trx_by_neon(resp["transactionHash"])
        solana_transactions = SolanaByNeonTransaction(**response)

        assert_instructions(validated_response)
        solana_trxs_by_neon = [trx.solanaTransactionSignature for trx in validated_response.result.solanaTransactions]
        assert set(solana_transactions.result) == set(solana_trxs_by_neon)

    def test_mint_mint_transfer_transfer(self, multiple_actions_erc721, json_rpc_client):
        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc721

        tx = self.web3_client.make_raw_tx(sender_account)
        seed_1 = self.web3_client.text_to_bytes32(gen_hash_of_block(10))
        seed_2 = self.web3_client.text_to_bytes32(gen_hash_of_block(10))
        uri_1 = generate_text(min_len=10, max_len=200)
        uri_2 = generate_text(min_len=10, max_len=200)
        instruction_tx = contract.functions.mintMintTransferTransfer(
            seed_1, uri_1, seed_2, uri_2, acc.address, acc.address
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        response = json_rpc_client.get_solana_trx_by_neon(resp["transactionHash"])
        solana_transactions = SolanaByNeonTransaction(**response)

        assert_instructions(validated_response)
        solana_trxs_by_neon = [trx.solanaTransactionSignature for trx in validated_response.result.solanaTransactions]
        assert set(solana_transactions.result) == set(solana_trxs_by_neon)

    def test_counter_batch_execute(
        self, call_solana_caller, counter_resource_address, get_counter_value, json_rpc_client
    ):
        sender = self.accounts[0]
        call_params = []

        for _ in range(10):
            instruction = TransactionInstruction(
                program_id=COUNTER_ID,
                keys=[
                    AccountMeta(counter_resource_address, is_signer=False, is_writable=True),
                ],
                data=bytes([0x1]),
            )
            serialized = serialize_instruction(COUNTER_ID, instruction)
            call_params.append((0, serialized))
            next(get_counter_value)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.batchExecute(call_params).build_transaction(tx)

        resp = self.web3_client.send_transaction(sender, instruction_tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        response = json_rpc_client.get_solana_trx_by_neon(resp["transactionHash"])
        solana_transactions = SolanaByNeonTransaction(**response)

        assert_instructions(validated_response)
        solana_trxs_by_neon = [trx.solanaTransactionSignature for trx in validated_response.result.solanaTransactions]
        assert set(solana_transactions.result) == set(solana_trxs_by_neon)
