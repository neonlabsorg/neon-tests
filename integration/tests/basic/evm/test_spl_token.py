import pytest
import web3
from eth_utils import is_hex
from solana.keypair import Keypair
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from solana.transaction import Transaction

from integration.tests.basic.helpers.basic import BaseMixin
from utils.consts import ZERO_HASH, ZERO_ADDRESS
from utils.helpers import gen_hash_of_block
from utils.metaplex import create_metadata_instruction_data, create_metadata_instruction

DECIMALS = 9
NAME = "SPL Token"
SYMBOL = "SPL"


class Mint:
    def __init__(self, data):
        self.supply = data[0]
        self.decimals = data[1]
        self.is_initialized = data[2]
        self.freeze_authority = data[3].hex()
        self.mint_authority = data[4].hex()

    def __str__(self):
        return {"supply": self.supply, "decimal": self.decimals, "is_initialized": self.is_initialized,
                "freeze_authority": self.freeze_authority, "mint_authority": self.mint_authority}.__str__()


class Account:
    def __init__(self, data):
        self.mint = data[0].hex()
        self.owner = data[1].hex()
        self.amount = data[2]
        self.delegate = data[3].hex()
        self.delegated_amount = data[4]
        self.close_authority = data[5].hex()
        self.state = data[6]


class TestPrecompiledSplToken(BaseMixin):

    def get_account(self, contract, account):
        mint_acc = contract.functions.findAccount(account.address).call()
        account_info = Account(contract.functions.getAccount(mint_acc).call())
        return account_info

    @pytest.fixture(scope="class")
    def token_mint(self, solana_account, sol_client, spl_token_caller, class_account, web3_client):
        token_mint, _ = sol_client.create_spl(solana_account, DECIMALS)
        metadata = create_metadata_instruction_data(NAME, SYMBOL)
        txn = Transaction()
        txn.add(
            create_metadata_instruction(
                metadata,
                solana_account.public_key,
                token_mint.pubkey,
                solana_account.public_key,
                solana_account.public_key,
            )
        )
        sol_client.send_transaction(
            txn, solana_account, opts=TxOpts(preflight_commitment=Confirmed, skip_confirmation=False)
        )
        tx = {
            "from": class_account.address,
            "nonce": web3_client.eth.get_transaction_count(
                class_account.address
            ),
            "gasPrice": web3_client.gas_price(),
        }
        instruction_tx = spl_token_caller.functions.initializeMint(DECIMALS).build_transaction(tx)
        receipt = web3_client.send_transaction(class_account, instruction_tx)
        assert receipt["status"] == 1
        log = spl_token_caller.events.LogBytes().process_receipt(receipt)[0]
        mint = log["args"]["value"]
        return mint

    @pytest.fixture(scope="class")
    def non_initialized_token_mint(self, solana_account, sol_client, spl_token_caller, class_account, web3_client):
        token_mint, _ = sol_client.create_spl(solana_account, DECIMALS)
        metadata = create_metadata_instruction_data(NAME, SYMBOL)
        txn = Transaction()
        txn.add(
            create_metadata_instruction(
                metadata,
                solana_account.public_key,
                token_mint.pubkey,
                solana_account.public_key,
                solana_account.public_key,
            )
        )
        sol_client.send_transaction(
            txn, solana_account, opts=TxOpts(preflight_commitment=Confirmed, skip_confirmation=False)
        )

        return bytes(token_mint.pubkey)

    @pytest.fixture(scope="class")
    def bob(self, spl_token_caller, token_mint, class_account, web3_client):
        tx = {
            "from": class_account.address,
            "nonce": web3_client.eth.get_transaction_count(
                class_account.address
            ),
            "gasPrice": web3_client.gas_price(),
        }
        instruction_tx = spl_token_caller.functions.initializeAccount(class_account.address,
                                                                      token_mint).build_transaction(tx)
        web3_client.send_transaction(class_account, instruction_tx)
        return class_account

    @pytest.fixture(scope="class")
    def alice(self, spl_token_caller, token_mint, web3_client, faucet, eth_bank_account):
        account = web3_client.create_account_with_balance(faucet, bank_account=eth_bank_account)
        tx = {
            "from": account.address,
            "nonce": web3_client.eth.get_transaction_count(
                account.address
            ),
            "gasPrice": web3_client.gas_price(),
        }
        instruction_tx = spl_token_caller.functions.initializeAccount(account.address,
                                                                      token_mint).build_transaction(tx)
        web3_client.send_transaction(account, instruction_tx)
        return account

    @pytest.fixture(scope="class")
    def non_initialized_acc(self, web3_client, faucet, eth_bank_account):
        yield web3_client.create_account_with_balance(faucet, bank_account=eth_bank_account)

    def test_get_mint_for_non_initialized_acc(self, spl_token_caller):
        acc = Keypair.generate()
        mint = Mint(spl_token_caller.functions.getMint(bytes(acc.public_key)).call())
        assert mint.supply == 0
        assert mint.decimals == 0
        assert mint.is_initialized == False
        assert mint.freeze_authority == ZERO_HASH
        assert mint.mint_authority == ZERO_HASH

    def test_get_mint(self, spl_token_caller, token_mint):
        mint = Mint(spl_token_caller.functions.getMint(token_mint).call())
        assert is_hex(mint.mint_authority)
        assert mint.decimals == DECIMALS
        assert mint.supply == 0
        assert mint.is_initialized == True
        assert mint.freeze_authority != ZERO_HASH

    def test_get_account(self, spl_token_caller, token_mint, solana_account):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = spl_token_caller.functions.initializeAccount(self.sender_account.address,
                                                                      token_mint).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        mint_acc = spl_token_caller.functions.findAccount(self.sender_account.address).call()
        account_info = Account(spl_token_caller.functions.getAccount(mint_acc).call())
        assert account_info.mint != ZERO_HASH
        assert account_info.owner != ZERO_HASH
        assert account_info.close_authority == ZERO_HASH
        assert account_info.delegate == ZERO_HASH
        assert account_info.state == 1
        assert account_info.amount == 0
        assert account_info.delegated_amount == 0

    def test_get_account_non_initialized_acc(self, spl_token_caller, non_initialized_acc):
        mint_acc = spl_token_caller.functions.findAccount(non_initialized_acc.address).call()
        account_info = Account(spl_token_caller.functions.getAccount(mint_acc).call())
        assert account_info.owner == ZERO_HASH
        assert account_info.mint == ZERO_HASH

    def test_get_account_invalid_account(self, spl_token_caller, token_mint):
        with pytest.raises(web3.exceptions.ContractLogicError,
                           match="Solana Program Error: An account's data contents was invalid"):
            spl_token_caller.functions.getAccount(token_mint).call()

    def test_initialize_mint(self, spl_token_caller):
        tx = self.create_contract_call_tx_object(self.sender_account)

        instruction_tx = spl_token_caller.functions.initializeMint(
            self.web3_client.text_to_bytes32(gen_hash_of_block(8)), DECIMALS).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        log = spl_token_caller.events.LogBytes().process_receipt(receipt)[0]
        mint = log["args"]["value"]
        assert Mint(spl_token_caller.functions.getMint(mint).call()).is_initialized == True

    def test_initialize_acc_incorrect_mint(self, spl_token_caller):
        tx = self.create_contract_call_tx_object(self.sender_account)
        acc = Keypair.generate()

        instruction_tx = spl_token_caller.functions.initializeAccount(self.sender_account.address,
                                                                      bytes(acc.public_key)).build_transaction(tx)
        with pytest.raises(ValueError, match="incorrect program id for instruction"):
            self.web3_client.send_transaction(self.sender_account, instruction_tx)

    def test_is_system_account(self, spl_token_caller, token_mint):
        assert spl_token_caller.functions.isSystemAccount(self.sender_account.address).call() == True
        assert spl_token_caller.functions.isSystemAccount(token_mint).call() == False

    def test_find_account(self, spl_token_caller, token_mint):
        assert spl_token_caller.functions.findAccount(self.sender_account.address).call() != ZERO_HASH
        assert spl_token_caller.functions.findAccount(token_mint).call() != ZERO_HASH

    def test_close_account(self, spl_token_caller, token_mint):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = spl_token_caller.functions.initializeAccount(self.sender_account.address,
                                                                      token_mint).build_transaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = spl_token_caller.functions.closeAccount(self.sender_account.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1

        mint_acc = spl_token_caller.functions.findAccount(self.sender_account.address).call()
        account_info = Account(spl_token_caller.functions.getAccount(mint_acc).call())
        assert account_info.mint == ZERO_HASH
        assert account_info.owner == ZERO_HASH
        assert account_info.state == 0

    def test_close_non_initialized_acc(self, non_initialized_acc, spl_token_caller):
        tx = self.create_contract_call_tx_object(non_initialized_acc)
        instruction_tx = spl_token_caller.functions.closeAccount(non_initialized_acc.address).build_transaction(tx)
        with pytest.raises(ValueError,
                           match="invalid account data for instruction"):
            self.web3_client.send_transaction(non_initialized_acc, instruction_tx)

    def test_freeze_and_thaw(self, spl_token_caller, token_mint, bob):
        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.freeze(token_mint, bob.address).build_transaction(tx)
        self.web3_client.send_transaction(bob, instruction_tx)
        assert self.get_account(spl_token_caller, bob).state == 2

        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.thaw(token_mint, bob.address).build_transaction(tx)
        self.web3_client.send_transaction(bob, instruction_tx)

        assert self.get_account(spl_token_caller, bob).state == 1

    def test_freeze_non_initialized_account(self, spl_token_caller, non_initialized_acc, token_mint):
        tx = self.create_contract_call_tx_object(non_initialized_acc)
        instruction_tx = spl_token_caller.functions.freeze(token_mint, non_initialized_acc.address).build_transaction(
            tx)
        with pytest.raises(ValueError,
                           match="invalid account data for instruction"):
            self.web3_client.send_transaction(non_initialized_acc, instruction_tx)

    def test_freeze_non_initialized_token(self, spl_token_caller, new_account, non_initialized_token_mint):
        tx = self.create_contract_call_tx_object(new_account)
        instruction_tx = spl_token_caller.functions.initializeAccount(new_account.address,
                                                                      non_initialized_token_mint).build_transaction(tx)
        self.web3_client.send_transaction(new_account, instruction_tx)

        tx = self.create_contract_call_tx_object(new_account)
        instruction_tx = spl_token_caller.functions.freeze(non_initialized_token_mint,
                                                           new_account.address).build_transaction(tx)
        with pytest.raises(ValueError,
                           match="This token mint cannot freeze accounts"):
            self.web3_client.send_transaction(new_account, instruction_tx)

    def test_freeze_with_not_associated_mint(self, spl_token_caller, bob, non_initialized_token_mint):
        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.freeze(non_initialized_token_mint,
                                                           bob.address).build_transaction(tx)
        with pytest.raises(ValueError,
                           match="Error: Account not associated with this Mint"):
            self.web3_client.send_transaction(bob, instruction_tx)

    def test_thaw_non_initialized_account(self, spl_token_caller, non_initialized_acc, token_mint):
        tx = self.create_contract_call_tx_object(non_initialized_acc)
        instruction_tx = spl_token_caller.functions.thaw(token_mint, non_initialized_acc.address).build_transaction(tx)
        with pytest.raises(ValueError,
                           match="invalid account data for instruction"):
            self.web3_client.send_transaction(non_initialized_acc, instruction_tx)

    def test_thaw_non_freezed_account(self, spl_token_caller, bob, token_mint):
        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.thaw(token_mint, bob.address).build_transaction(tx)
        with pytest.raises(ValueError,
                           match="Error: Invalid account state for operation"):
            self.web3_client.send_transaction(bob, instruction_tx)

    def test_mint_to(self, spl_token_caller, token_mint, bob):
        amount = 100
        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.mintTo(bob.address, amount,
                                                           token_mint).build_transaction(tx)
        receipt = self.web3_client.send_transaction(bob, instruction_tx)
        assert receipt["status"] == 1
        assert self.get_account(spl_token_caller, bob).amount == amount

    def test_mint_to_non_initialized_acc(self, spl_token_caller, token_mint, non_initialized_acc):
        tx = self.create_contract_call_tx_object(non_initialized_acc)
        instruction_tx = spl_token_caller.functions.mintTo(non_initialized_acc.address, 100,
                                                           token_mint).build_transaction(tx)

        with pytest.raises(ValueError,
                           match="invalid account data for instruction"):
            self.web3_client.send_transaction(non_initialized_acc, instruction_tx)

    def test_mint_to_non_initialized_token(self, spl_token_caller, non_initialized_token_mint, new_account):
        tx = self.create_contract_call_tx_object(new_account)
        instruction_tx = spl_token_caller.functions.initializeAccount(new_account.address,
                                                                      non_initialized_token_mint).build_transaction(tx)
        self.web3_client.send_transaction(new_account, instruction_tx)

        tx = self.create_contract_call_tx_object(new_account)
        instruction_tx = spl_token_caller.functions.mintTo(new_account.address, 100,
                                                           non_initialized_token_mint).build_transaction(tx)
        with pytest.raises(ValueError,
                           match="owner does not match"):
            self.web3_client.send_transaction(new_account, instruction_tx)

    def test_transfer(self, spl_token_caller, token_mint, bob, alice):
        amount = 100

        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.mintTo(bob.address, amount,
                                                           token_mint).build_transaction(tx)

        self.web3_client.send_transaction(bob, instruction_tx)

        b1_before = self.get_account(spl_token_caller, bob).amount
        b2_before = self.get_account(spl_token_caller, alice).amount

        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.transfer(bob.address, alice.address,
                                                             amount).build_transaction(tx)
        self.web3_client.send_transaction(bob, instruction_tx)

        b1_after = self.get_account(spl_token_caller, bob).amount
        b2_after = self.get_account(spl_token_caller, alice).amount
        assert b2_after - b2_before == amount
        assert b1_before - b1_after == amount

    def test_transfer_to_non_initialized_acc(self, spl_token_caller, token_mint, bob, non_initialized_acc):
        amount = 100
        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.mintTo(bob.address, amount,
                                                           token_mint).build_transaction(tx)
        self.web3_client.send_transaction(bob, instruction_tx)

        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.transfer(bob.address, non_initialized_acc.address,
                                                             amount).build_transaction(tx)
        with pytest.raises(ValueError, match="invalid account data for instruction"):
            self.web3_client.send_transaction(bob, instruction_tx)

    def test_transfer_with_incorrect_signer(self, spl_token_caller, token_mint, bob, alice):
        amount = 100

        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.mintTo(bob.address, amount,
                                                           token_mint).build_transaction(tx)

        self.web3_client.send_transaction(bob, instruction_tx)

        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.transfer(bob.address, alice.address,
                                                             amount).build_transaction(tx)
        with pytest.raises(TypeError, match=r"from field must match key's .*, but it was "):
            self.web3_client.send_transaction(alice, instruction_tx)

    def test_transfer_more_than_balance(self, spl_token_caller, token_mint, bob, alice):
        transfer_amount = self.get_account(spl_token_caller, bob).amount + 1

        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.transfer(bob.address, alice.address,
                                                             transfer_amount).build_transaction(tx)
        with pytest.raises(ValueError, match="Error: insufficient funds"):
            self.web3_client.send_transaction(bob, instruction_tx)

    def test_burn(self, spl_token_caller, token_mint, bob):
        amount = 100

        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.mintTo(bob.address, amount,
                                                           token_mint).build_transaction(tx)

        self.web3_client.send_transaction(bob, instruction_tx)

        balance_before = self.get_account(spl_token_caller, bob).amount
        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.burn(token_mint, bob.address,
                                                         amount).build_transaction(tx)
        self.web3_client.send_transaction(bob, instruction_tx)

        balance_after = self.get_account(spl_token_caller, bob).amount
        assert balance_before - balance_after == amount

    def test_burn_non_initialized_acc(self, spl_token_caller, token_mint, non_initialized_acc):
        tx = self.create_contract_call_tx_object(non_initialized_acc)
        instruction_tx = spl_token_caller.functions.burn(token_mint, non_initialized_acc.address,
                                                         10).build_transaction(tx)
        with pytest.raises(ValueError, match="invalid account data for instruction"):
            self.web3_client.send_transaction(non_initialized_acc, instruction_tx)

    def test_burn_more_then_balance(self, spl_token_caller, token_mint, bob):
        amount = self.get_account(spl_token_caller, bob).amount + 1

        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.burn(token_mint, bob.address,
                                                         amount).build_transaction(tx)
        with pytest.raises(ValueError, match="Error: insufficient funds"):
            self.web3_client.send_transaction(bob, instruction_tx)

    def test_approve_and_revoke(self, spl_token_caller, token_mint, bob, alice):
        amount = 100

        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.mintTo(bob.address, amount,
                                                           token_mint).build_transaction(tx)
        self.web3_client.send_transaction(bob, instruction_tx)

        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.approve(bob.address, alice.address,
                                                            amount).build_transaction(tx)
        self.web3_client.send_transaction(bob, instruction_tx)

        assert self.get_account(spl_token_caller, bob).delegated_amount == amount

        tx = self.create_contract_call_tx_object(bob)
        instruction_tx = spl_token_caller.functions.revoke(bob.address).build_transaction(tx)
        self.web3_client.send_transaction(bob, instruction_tx)

        assert self.get_account(spl_token_caller, bob).delegated_amount == 0