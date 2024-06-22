import allure
import pytest
import spl
from solana.keypair import Keypair
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from spl.token.instructions import create_associated_token_account, TransferParams, transfer
from solana.transaction import TransactionInstruction, AccountMeta
from spl.token.constants import TOKEN_PROGRAM_ID

from utils.accounts import EthAccounts
from utils.consts import COUNTER_ID, TRANSFER_TOKENS_ID
from utils.helpers import serialize_instruction
from utils.web3client import NeonChainWeb3Client


@pytest.mark.proxy_version("v1.12.0")
@allure.feature("EVM tests")
@allure.story("Verify precompiled solana call contract")
@pytest.mark.usefixtures("accounts", "web3_client", "sol_client_session")
class TestSolanaInteroperability:
    accounts: EthAccounts
    web3_client: NeonChainWeb3Client

    @pytest.fixture(scope="class")
    def call_solana_caller(self):
        contract, _ = self.web3_client.deploy_and_get_contract(
            "precompiled/CallSolanaCaller.sol", "0.8.10", self.accounts[0]
        )
        return contract

    def create_resource(self, contract, salt, sender, owner):
        tx = self.web3_client.make_raw_tx(sender.address)
        salt = self.web3_client.text_to_bytes32(salt)
        instruction_tx = contract.functions.createResource(salt, 8, 100000, bytes(owner)).build_transaction(tx)
        self.web3_client.send_transaction(sender, instruction_tx)

        return contract.functions.getResourceAddress(salt).call()

    def test_counter(self, call_solana_caller):
        sender = self.accounts[0]

        resource_addr = self.create_resource(call_solana_caller, "1", sender, COUNTER_ID)
        lamports = 0

        instruction = TransactionInstruction(
            program_id=COUNTER_ID,
            keys=[
                AccountMeta(resource_addr, is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.execute(lamports, serialized).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1

    def test_transfer_with_pda_signature(self, call_solana_caller, sol_client, solana_account, pytestconfig, bank_account):
        sender = self.accounts[0]
        from_wallet = Keypair.generate()
        to_wallet = Keypair.generate()
        amount = 100000
        if pytestconfig.environment.use_bank:
            sol_client.send_sol(bank_account, from_wallet.public_key, int(0.5 * 10**9))
        else:
            sol_client.request_airdrop(from_wallet.public_key, 1000 * 10**9, commitment=Confirmed)

        mint = spl.token.client.Token.create_mint(
            conn=sol_client,
            payer=from_wallet,
            mint_authority=from_wallet.public_key,
            decimals=9,
            program_id=TOKEN_PROGRAM_ID,
        )
        mint.payer = from_wallet
        from_token_account = mint.create_associated_token_account(from_wallet.public_key)
        to_token_account = mint.create_associated_token_account(to_wallet.public_key)
        mint.mint_to(
            dest=from_token_account,
            mint_authority=from_wallet,
            amount=amount,
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        authority_pubkey = call_solana_caller.functions.getSolanaPDA(bytes(TRANSFER_TOKENS_ID), b"authority").call()
        mint.set_authority(
            from_token_account,
            from_wallet,
            spl.token.instructions.AuthorityType.ACCOUNT_OWNER,
            authority_pubkey,
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        instruction = TransactionInstruction(
            program_id=TRANSFER_TOKENS_ID,
            keys=[
                AccountMeta(from_token_account, is_signer=False, is_writable=True),
                AccountMeta(mint.pubkey, is_signer=False, is_writable=True),
                AccountMeta(to_token_account, is_signer=False, is_writable=True),
                AccountMeta(authority_pubkey, is_signer=False, is_writable=True),
                AccountMeta(TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
            ],
            data=bytes([0x0]),
        )
        serialized = serialize_instruction(TRANSFER_TOKENS_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.execute(0, serialized).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1
        assert int(mint.get_balance(to_token_account, commitment=Confirmed).value.amount) == amount

    def test_transfer_tokens_with_ext_authority(self, call_solana_caller, sol_client, pytestconfig, bank_account):
        sender = self.accounts[0]
        from_wallet = Keypair.generate()
        to_wallet = Keypair.generate()
        amount = 100000
        if pytestconfig.environment.use_bank:
            sol_client.send_sol(bank_account, from_wallet.public_key, int(0.5 * 10**9))
        else:
            sol_client.request_airdrop(from_wallet.public_key, 1000 * 10**9, commitment=Confirmed)
        mint = spl.token.client.Token.create_mint(
            conn=sol_client,
            payer=from_wallet,
            mint_authority=from_wallet.public_key,
            decimals=9,
            program_id=TOKEN_PROGRAM_ID,
        )
        mint.payer = from_wallet
        from_token_account = mint.create_associated_token_account(from_wallet.public_key)
        to_token_account = mint.create_associated_token_account(to_wallet.public_key)
        mint.mint_to(
            dest=from_token_account,
            mint_authority=from_wallet,
            amount=amount,
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        seed = self.web3_client.text_to_bytes32("myseed")
        authority = call_solana_caller.functions.getExtAuthority(seed).call({"from": sender.address})

        mint.set_authority(
            from_token_account,
            from_wallet,
            spl.token.instructions.AuthorityType.ACCOUNT_OWNER,
            authority,
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        instruction = transfer(
            TransferParams(TOKEN_PROGRAM_ID, from_token_account, to_token_account, authority, amount)
        )

        serialized = serialize_instruction(TOKEN_PROGRAM_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.executeWithSeed(0, seed, serialized).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1
        assert int(mint.get_balance(to_token_account, commitment=Confirmed).value.amount) == amount
