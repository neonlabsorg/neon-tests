import json

import pytest
import allure
import web3
from _pytest.config import Config
from solana.keypair import Keypair
from solana.rpc.commitment import Commitment
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solana.publickey import PublicKey
from spl.token.client import Token as SplToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (
    create_associated_token_account,
    get_associated_token_address,
)
from web3 import exceptions as web3_exceptions

from utils.consts import LAMPORT_PER_SOL, wSOL, MULTITOKEN_MINTS
from utils.transfers_inter_networks import neon_transfer_tx, wSOL_tx, token_from_solana_to_neon_tx
from utils.helpers import wait_condition
from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts
from utils.solana_client import SolanaClient


@allure.feature("Transfer NEON <-> Solana")
@allure.story("Deposit from Solana to NEON")
@pytest.mark.usefixtures("accounts", "web3_client", "sol_client")
class TestDeposit:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    sol_client: SolanaClient

    def withdraw_neon(self, sender_account, dest_acc, move_amount):
        contract, _ = self.web3_client.deploy_and_get_contract(
            "precompiled/NeonToken", "0.8.10", account=sender_account
        )
        tx = self.web3_client.make_raw_tx(sender_account, amount=web3.Web3.to_wei(move_amount, "ether"))
        instruction_tx = contract.functions.withdraw(bytes(dest_acc.public_key)).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1

    def test_transfer_neon_from_solana_to_neon(self, new_account, solana_account, pytestconfig: Config, neon_mint):
        """Transfer Neon from Solana -> Neon"""
        amount = 0.1
        sender_account = self.accounts[0]
        full_amount = int(amount * LAMPORT_PER_SOL)
        evm_loader_id = pytestconfig.environment.evm_loader

        neon_balance_before = self.web3_client.get_balance(new_account.address)

        self.sol_client.create_ata(solana_account, neon_mint)
        self.withdraw_neon(sender_account, solana_account, amount)
        tx = token_from_solana_to_neon_tx(
            self.sol_client,
            solana_account,
            neon_mint,
            new_account,
            full_amount,
            evm_loader_id,
            self.web3_client.eth.chain_id,
        )
        self.sol_client.send_tx_and_check_status_ok(tx, solana_account)

        neon_balance_after = self.web3_client.get_balance(new_account.address)
        assert neon_balance_after == neon_balance_before + web3.Web3.to_wei(amount, "ether")

    @pytest.mark.multipletokens
    def test_create_and_transfer_new_token_from_solana_to_neon(
        self,
        new_account,
        solana_account,
        pytestconfig: Config,
        neon_mint,
        web3_client_usdt,
        operator_keypair,
        evm_loader_keypair,
    ):
        amount = 5000
        new_sol_account = Keypair.generate()
        token_mint = PublicKey(MULTITOKEN_MINTS["USDT"])
        self.sol_client.request_airdrop(new_sol_account.public_key, 1 * LAMPORT_PER_SOL)
        self.sol_client.mint_spl_to(token_mint, new_sol_account, 1000000000000000)

        # self.sol_client.deposit_neon_like_tokens_from_solana_to_neon(
        #     neon_mint,
        #     new_sol_account,
        #     new_account,
        #     web3_client_usdt.eth.chain_id,
        #     operator_keypair,
        #     evm_loader_keypair,
        #     evm_loader_id,
        #     amount,
        # )
        tx = token_from_solana_to_neon_tx(
            self.sol_client,
            new_sol_account,
            token_mint,
            new_account,
            amount,
            pytestconfig.environment.evm_loader,
            web3_client_usdt.eth.chain_id,
        )
        self.sol_client.send_tx_and_check_status_ok(tx, new_sol_account)

        usdt_balance_after = web3_client_usdt.get_balance(new_account)
        assert usdt_balance_after == amount * 1000000000000

    def test_transfer_spl_token_from_solana_to_neon(self, solana_account, new_account, pytestconfig: Config, erc20_spl):
        evm_loader_id = pytestconfig.environment.evm_loader
        amount = 0.1
        full_amount = int(amount * LAMPORT_PER_SOL)

        mint_pubkey = wSOL["address_spl"]
        ata_address = get_associated_token_address(solana_account.public_key, mint_pubkey)

        self.sol_client.create_ata(solana_account, mint_pubkey)

        spl_neon_token = SplToken(self.sol_client, mint_pubkey, TOKEN_PROGRAM_ID, solana_account)
        ata_balance_before = spl_neon_token.get_balance(ata_address, commitment=Commitment("confirmed"))

        # wrap SOL
        wSOL_account = self.sol_client.get_account_info(ata_address).value
        wrap_sol_tx = wSOL_tx(wSOL_account, wSOL, full_amount, solana_account.public_key, ata_address)
        self.sol_client.send_tx_and_check_status_ok(wrap_sol_tx, solana_account)

        # transfer wSOL
        transfer_tx = neon_transfer_tx(
            self.web3_client, self.sol_client, full_amount, wSOL, solana_account, new_account, erc20_spl, evm_loader_id
        )
        self.sol_client.send_tx_and_check_status_ok(transfer_tx, solana_account)

        ata_balance_after = spl_neon_token.get_balance(ata_address, commitment=Commitment("confirmed"))

        assert int(ata_balance_after.value.amount) == int(ata_balance_before.value.amount) + full_amount

    @pytest.mark.multipletokens
    def test_transfer_wrapped_sol_token_from_solana_to_neon(
        self, solana_account, pytestconfig: Config, web3_client_sol
    ):
        new_account = self.web3_client.create_account()

        evm_loader_id = pytestconfig.environment.evm_loader
        amount = 0.1
        full_amount = int(amount * LAMPORT_PER_SOL)

        mint_pubkey = wSOL["address_spl"]
        ata_address = get_associated_token_address(solana_account.public_key, mint_pubkey)

        self.sol_client.create_ata(solana_account, mint_pubkey)

        # wrap SOL
        wSOL_account = self.sol_client.get_account_info(ata_address).value
        wrap_sol_tx = wSOL_tx(wSOL_account, wSOL, full_amount, solana_account.public_key, ata_address)
        self.sol_client.send_tx_and_check_status_ok(wrap_sol_tx, solana_account)

        tx = token_from_solana_to_neon_tx(
            self.sol_client,
            solana_account,
            wSOL["address_spl"],
            new_account,
            full_amount,
            evm_loader_id,
            web3_client_sol.eth.chain_id,
        )

        self.sol_client.send_tx_and_check_status_ok(tx, solana_account)

        assert web3_client_sol.get_balance(new_account) / LAMPORT_PER_SOL == full_amount


@allure.feature("Transfer NEON <-> Solana")
@allure.story("Withdraw from NEON to Solana")
@pytest.mark.usefixtures("accounts", "web3_client", "sol_client")
class TestWithdraw:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    sol_client: SolanaClient

    def withdraw(self, sender_acc, dest_acc, move_amount, withdraw_contract):
        instruction_tx = withdraw_contract.functions.withdraw(bytes(dest_acc.public_key)).build_transaction(
            {
                "from": sender_acc.address,
                "nonce": self.web3_client.eth.get_transaction_count(sender_acc.address),
                "gasPrice": self.web3_client.gas_price(),
                "value": move_amount,
            }
        )
        receipt = self.web3_client.send_transaction(sender_acc, instruction_tx)
        assert receipt["status"] == 1

    @pytest.mark.parametrize("move_amount, error", [(11000, web3.exceptions.ContractLogicError), (10000, ValueError)])
    def test_failed_withdraw_insufficient_balance(
        self, pytestconfig: Config, move_amount, error, withdraw_contract, neon_mint, solana_account, prepare_account
    ):
        # FIXME: NDEV-2496 Don't work if run all tests (because dest_acc already exist)
        dest_acc = solana_account

        spl_neon_token = SplToken(self.sol_client, neon_mint, TOKEN_PROGRAM_ID, dest_acc.public_key)

        amount = move_amount * pow(10, 18)
        dest_token_acc = get_associated_token_address(dest_acc.public_key, neon_mint)

        response = spl_neon_token.get_balance(dest_token_acc, commitment=Commitment("confirmed"))

        # assert json.loads(response.to_json())["message"] == "Invalid param: could not find account"

        with pytest.raises(error):
            self.withdraw(prepare_account, dest_acc, amount, withdraw_contract)

        response = spl_neon_token.get_balance(dest_token_acc, commitment=Commitment("confirmed"))
        # assert json.loads(response.to_json())["message"] == "Invalid param: could not find account"

    @pytest.mark.only_stands
    def test_success_withdraw_to_non_existing_account(
        self, pytestconfig: Config, withdraw_contract, neon_mint, solana_account
    ):
        """Should successfully withdraw NEON tokens to previously non-existing Associated Token Account"""
        sender_account = self.accounts[0]
        dest_acc = Keypair.generate()
        self.sol_client.request_airdrop(dest_acc.public_key, 1_000_000_000)

        spl_neon_token = SplToken(self.sol_client, neon_mint, TOKEN_PROGRAM_ID, dest_acc)

        dest_token_acc = get_associated_token_address(dest_acc.public_key, neon_mint)

        move_amount = self.web3_client._web3.to_wei(5, "ether")

        destination_balance_before = spl_neon_token.get_balance(dest_acc.public_key, commitment=Commitment("confirmed"))
        with pytest.raises(AttributeError):
            # FIXME: Why this raise error?
            _ = destination_balance_before.value

        self.withdraw(sender_account, dest_acc, move_amount, withdraw_contract)

        destination_balance_after = spl_neon_token.get_balance(dest_token_acc, commitment=Commitment("confirmed"))

        assert int(destination_balance_after.value.amount) == int(move_amount / 1_000_000_000)

    def test_success_withdraw_to_existing_account(
        self, pytestconfig: Config, withdraw_contract, neon_mint, solana_account
    ):
        """Should successfully withdraw NEON tokens to existing Associated Token Account"""
        dest_acc = solana_account
        sender_account = self.accounts[0]

        wait_condition(lambda: self.sol_client.get_balance(dest_acc.public_key) != 0)

        trx = Transaction()
        trx.add(create_associated_token_account(dest_acc.public_key, dest_acc.public_key, neon_mint))
        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        self.sol_client.send_transaction(trx, dest_acc, opts=opts)

        dest_token_acc = get_associated_token_address(dest_acc.public_key, neon_mint)

        move_amount_alan = 2_123_000_321_000_000_000
        move_amount_galan = int(move_amount_alan / 1_000_000_000)

        spl_neon_token = SplToken(self.sol_client, neon_mint, TOKEN_PROGRAM_ID, dest_acc)

        destination_balance_before = spl_neon_token.get_balance(dest_token_acc, commitment=Commitment("confirmed"))

        self.withdraw(sender_account, dest_acc, move_amount_alan, withdraw_contract)

        destination_balance_after = spl_neon_token.get_balance(dest_token_acc, commitment=Commitment("confirmed"))
        assert int(destination_balance_after.value.amount) == move_amount_galan + int(
            destination_balance_before.value.amount
        )

    def test_failed_withdraw_non_divisible_amount(
        self, pytestconfig: Config, withdraw_contract, neon_mint, solana_account
    ):
        sender_account = self.accounts[0]
        dest_acc = solana_account

        spl_neon_token = SplToken(self.sol_client, neon_mint, TOKEN_PROGRAM_ID, dest_acc.public_key)

        move_amount = pow(10, 18) + 123

        destination_balance_before = spl_neon_token.get_balance(dest_acc.public_key, commitment=Commitment("confirmed"))
        with pytest.raises(AttributeError):
            _ = destination_balance_before.value

        with pytest.raises(web3_exceptions.ContractLogicError):
            self.withdraw(sender_account, dest_acc, move_amount, withdraw_contract)

        destination_balance_after = spl_neon_token.get_balance(dest_acc.public_key, commitment=Commitment("confirmed"))
        with pytest.raises(AttributeError):
            _ = destination_balance_after.value
