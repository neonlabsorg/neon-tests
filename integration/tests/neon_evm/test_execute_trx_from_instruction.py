import random
import string

import pytest
import solana
import eth_abi
from eth_account.datastructures import SignedTransaction
from eth_keys import keys as eth_keys
from eth_utils import abi, to_text
from hexbytes import HexBytes
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.commitment import Confirmed
from spl.token.instructions import get_associated_token_address

from .solana_utils import execute_trx_from_instruction
from .utils.assert_messages import InstructionAsserts
from .utils.constants import NEON_TOKEN_MINT_ID
from .utils.contract import make_contract_call_trx
from .utils.ethereum import make_eth_transaction
from .utils.transaction_checks import check_transaction_logs_have_text
from .types.types import Caller, Contract


class TestExecuteTrxFromInstruction:
    def test_simple_transfer_transaction(
        self, operator_keypair, treasury_pool, sender_with_tokens: Caller, session_user: Caller, holder_acc, evm_loader
    ):
        amount = 10
        sender_balance_before = evm_loader.get_neon_balance(sender_with_tokens)
        recipient_balance_before = evm_loader.get_neon_balance(session_user)

        signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, amount)
        resp = execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            evm_loader,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                session_user.balance_account_address,
                session_user.solana_account_address,
            ],
            operator_keypair,
        )
        sender_balance_after = evm_loader.get_neon_balance(sender_with_tokens)
        recipient_balance_after = evm_loader.get_neon_balance(session_user)
        assert sender_balance_before - amount == sender_balance_after
        assert recipient_balance_before + amount == recipient_balance_after
        check_transaction_logs_have_text(resp.value, "exit_status=0x11")

    def test_transfer_transaction_with_non_existing_recipient(
        self, operator_keypair, treasury_pool, holder_acc, sender_with_tokens: Caller, evm_loader
    ):
        # recipient account should be created
        recipient = Keypair.generate()

        recipient_ether = eth_keys.PrivateKey(recipient.secret_key[:32]).public_key.to_canonical_address()
        recipient_solana_address, _ = evm_loader.ether2program(recipient_ether)
        recipient_balance_address = evm_loader.ether2balance(recipient_ether)
        amount = 10
        signed_tx = make_eth_transaction(recipient_ether, None, sender_with_tokens, amount)
        resp = execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            evm_loader,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                recipient_balance_address,
                PublicKey(recipient_solana_address),
            ],
            operator_keypair,
        )

        recipient_balance_after = evm_loader.get_neon_balance(recipient_ether)
        check_transaction_logs_have_text(resp.value, "exit_status=0x11")

        assert recipient_balance_after == amount

    def test_call_contract_function_without_neon_transfer(
        self,
        operator_keypair,
        treasury_pool,
        holder_acc,
        sender_with_tokens: Caller,
        string_setter_contract: Contract,
        evm_loader,
        neon_api_client,
    ):
        text = "".join(random.choice(string.ascii_letters) for _ in range(10))
        signed_tx = make_contract_call_trx(sender_with_tokens, string_setter_contract, "set(string)", [text])

        resp = execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            evm_loader,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [sender_with_tokens.balance_account_address, string_setter_contract.solana_address],
            operator_keypair,
        )

        check_transaction_logs_have_text(resp.value, "exit_status=0x11")
        assert text in to_text(
            neon_api_client.call_contract_get_function(sender_with_tokens, string_setter_contract, "get()")
        )

    def test_call_contract_function_with_neon_transfer(
        self,
        operator_keypair,
        treasury_pool,
        holder_acc,
        sender_with_tokens: Caller,
        evm_loader,
        neon_api_client,
        string_setter_contract,
    ):
        transfer_amount = random.randint(1, 1000)

        sender_balance_before = evm_loader.get_neon_balance(sender_with_tokens)
        contract_balance_before = evm_loader.get_neon_balance(string_setter_contract.eth_address)

        text = "".join(random.choice(string.ascii_letters) for i in range(10))
        func_name = abi.function_signature_to_4byte_selector("set(string)")
        data = func_name + eth_abi.encode(["string"], [text])
        signed_tx = make_eth_transaction(string_setter_contract.eth_address, data, sender_with_tokens, transfer_amount)
        resp = execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            evm_loader,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                string_setter_contract.balance_account_address,
                string_setter_contract.solana_address,
            ],
            operator_keypair,
        )

        check_transaction_logs_have_text(resp.value, "exit_status=0x11")

        assert text in to_text(
            neon_api_client.call_contract_get_function(sender_with_tokens, string_setter_contract, "get()")
        )

        sender_balance_after = evm_loader.get_neon_balance(sender_with_tokens)
        contract_balance_after = evm_loader.get_neon_balance(string_setter_contract.eth_address)
        assert sender_balance_before - transfer_amount == sender_balance_after
        assert contract_balance_before + transfer_amount == contract_balance_after

    def test_incorrect_chain_id(
        self, operator_keypair, treasury_pool, holder_acc, sender_with_tokens: Caller, session_user: Caller, evm_loader
    ):
        amount = 1
        signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, amount, chain_id=1)
        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.INVALID_CHAIN_ID):
            execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                evm_loader,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [
                    sender_with_tokens.balance_account_address,
                    session_user.balance_account_address,
                    session_user.solana_account_address,
                ],
                operator_keypair,
            )

    def test_incorrect_nonce(
        self, operator_keypair, treasury_pool, holder_acc, sender_with_tokens: Caller, session_user: Caller, evm_loader
    ):
        signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, 1)

        execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            evm_loader,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                session_user.balance_account_address,
                session_user.solana_account_address,
            ],
            operator_keypair,
        )
        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.INVALID_NONCE):
            execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                evm_loader,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [
                    sender_with_tokens.balance_account_address,
                    session_user.balance_account_address,
                    session_user.solana_account_address,
                ],
                operator_keypair,
            )

    def test_insufficient_funds(
        self, operator_keypair, treasury_pool, evm_loader, holder_acc, sender_with_tokens: Caller, session_user: Caller
    ):
        user_balance = evm_loader.get_neon_balance(session_user)

        signed_tx = make_eth_transaction(sender_with_tokens.eth_address, None, session_user, user_balance + 1)

        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.INSUFFICIENT_FUNDS):
            execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                evm_loader,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [
                    sender_with_tokens.balance_account_address,
                    session_user.balance_account_address,
                    session_user.solana_account_address,
                ],
                operator_keypair,
            )

    def test_gas_limit_reached(
        self, operator_keypair, treasury_pool, holder_acc, session_user: Caller, sender_with_tokens: Caller, evm_loader
    ):
        amount = 10
        signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, amount, gas=1)

        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.OUT_OF_GAS):
            execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                evm_loader,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [
                    sender_with_tokens.balance_account_address,
                    session_user.balance_account_address,
                    session_user.solana_account_address,
                ],
                operator_keypair,
            )

    def test_sender_missed_in_remaining_accounts(
        self, operator_keypair, holder_acc, treasury_pool, session_user: Caller, sender_with_tokens: Caller, evm_loader
    ):
        signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, 1)
        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.ADDRESS_MUST_BE_PRESENT):
            execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                evm_loader,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [session_user.balance_account_address, session_user.solana_account_address],
                operator_keypair,
            )

    def test_recipient_missed_in_remaining_accounts(
        self, operator_keypair, holder_acc, treasury_pool, sender_with_tokens: Caller, session_user: Caller, evm_loader
    ):
        signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, 1)
        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.ADDRESS_MUST_BE_PRESENT):
            execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                evm_loader,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [sender_with_tokens.balance_account_address],
                operator_keypair,
            )

    def test_incorrect_treasure_pool(
        self, operator_keypair, holder_acc, sender_with_tokens: Caller, session_user: Caller, evm_loader
    ):
        signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, 1)

        treasury_buffer = b"\x02\x00\x00\x00"
        treasury_pool = Keypair().public_key

        error = str.format(InstructionAsserts.INVALID_ACCOUNT, treasury_pool)
        with pytest.raises(solana.rpc.core.RPCException, match=error):
            execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                evm_loader,
                treasury_pool,
                treasury_buffer,
                signed_tx,
                [],
                operator_keypair,
            )

    def test_incorrect_treasure_index(
        self, operator_keypair, holder_acc, treasury_pool, sender_with_tokens: Caller, session_user: Caller, evm_loader
    ):
        signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, 1)
        treasury_buffer = b"\x03\x00\x00\x00"

        error = str.format(InstructionAsserts.INVALID_ACCOUNT, treasury_pool.account)
        with pytest.raises(solana.rpc.core.RPCException, match=error):
            execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                evm_loader,
                treasury_pool.account,
                treasury_buffer,
                signed_tx,
                [],
                operator_keypair,
            )

    def test_incorrect_operator_account(
        self, evm_loader, treasury_pool, holder_acc, session_user: Caller, sender_with_tokens: Caller
    ):
        signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, 1)
        fake_operator = Keypair()
        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.ACC_NOT_FOUND):
            execute_trx_from_instruction(
                fake_operator,
                holder_acc,
                evm_loader,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [
                    sender_with_tokens.balance_account_address,
                    session_user.balance_account_address,
                    session_user.solana_account_address,
                ],
                fake_operator,
            )

    def test_operator_is_not_in_white_list(
        self, sender_with_tokens, evm_loader, treasury_pool, session_user, holder_acc
    ):
        # now any user can send transactions through "execute transaction from instruction" instruction

        signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, 1)
        resp = execute_trx_from_instruction(
            sender_with_tokens.solana_account,
            holder_acc,
            evm_loader,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                session_user.balance_account_address,
                session_user.solana_account_address,
            ],
            sender_with_tokens.solana_account,
        )
        check_transaction_logs_have_text(resp.value, "exit_status=0x11")

    def test_incorrect_system_program(
        self, sender_with_tokens, operator_keypair, evm_loader, treasury_pool, session_user, holder_acc
    ):
        signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, 1)
        fake_sys_program_id = Keypair().public_key
        with pytest.raises(
            solana.rpc.core.RPCException, match=str.format(InstructionAsserts.NOT_SYSTEM_PROGRAM, fake_sys_program_id)
        ):
            execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                evm_loader,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [],
                operator_keypair,
                system_program=fake_sys_program_id,
            )

    def test_operator_does_not_have_enough_founds(
        self, evm_loader, treasury_pool, holder_acc, session_user: Caller, sender_with_tokens: Caller
    ):
        key = Keypair.generate()
        caller_ether = eth_keys.PrivateKey(key.secret_key[:32]).public_key.to_canonical_address()
        caller, caller_nonce = evm_loader.ether2program(caller_ether)
        caller_token = get_associated_token_address(PublicKey(caller), NEON_TOKEN_MINT_ID)
        evm_loader.create_balance_account(caller_ether)

        operator_without_money = Caller(key, PublicKey(caller), caller_ether, caller_nonce, caller_token)

        signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, 1)
        with pytest.raises(
            solana.rpc.core.RPCException, match="Attempt to debit an account but found no record of a prior credit"
        ):
            execute_trx_from_instruction(
                operator_without_money.solana_account,
                holder_acc,
                evm_loader,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [
                    sender_with_tokens.balance_account_address,
                    session_user.balance_account_address,
                    session_user.solana_account_address,
                ],
                operator_without_money.solana_account,
            )

    def test_transaction_with_access_list(
        self,
        operator_keypair,
        treasury_pool,
        sender_with_tokens,
        evm_loader,
        calculator_contract,
        calculator_caller_contract,
        holder_acc,
    ):
        access_list = (
            {
                "address": "0x" + calculator_contract.eth_address.hex(),
                "storageKeys": (
                    "0x0000000000000000000000000000000000000000000000000000000000000000",
                    "0x0000000000000000000000000000000000000000000000000000000000000001",
                ),
            },
        )
        signed_tx = make_contract_call_trx(
            sender_with_tokens, calculator_caller_contract, "callCalculator()", access_list=access_list
        )

        resp = execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            evm_loader,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                calculator_caller_contract.solana_address,
                calculator_contract.solana_address,
            ],
            operator_keypair,
        )

        check_transaction_logs_have_text(resp.value, "exit_status=0x12")

    def test_old_trx_type_with_leading_zeros(
        self,
        sender_with_tokens,
        operator_keypair,
        evm_loader,
        holder_acc,
        calculator_caller_contract,
        calculator_contract,
        treasury_pool,
    ):
        signed_tx = make_contract_call_trx(sender_with_tokens, calculator_caller_contract, "callCalculator()")
        new_raw_trx = HexBytes(bytes([0]) + signed_tx.rawTransaction)

        signed_tx_new = SignedTransaction(
            rawTransaction=new_raw_trx,
            hash=signed_tx.hash,
            r=signed_tx.r,
            s=signed_tx.s,
            v=signed_tx.v,
        )

        resp = execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            evm_loader,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx_new,
            [
                sender_with_tokens.balance_account_address,
                calculator_caller_contract.solana_address,
                calculator_contract.solana_address,
            ],
            operator_keypair,
        )
        check_transaction_logs_have_text(resp.value, "exit_status=0x12")

    def test_neon_pass_with_temp_holder(
        self, treasury_pool, sender_with_tokens: Caller, holder_acc, evm_loader, operator_keypair
    ):
        '''
        The context behind the test. In Neon Pass, the user submits Neon Transaction themself, 
        bypassing Operators. The transaction consists of TransactionExecFromInstruction instruction.
        
        Given that, as of now, TransactionExecFromInstruction requires Holder Account, the user has
        to provide it. Although, this Holder is temporary (and funds for the rent-exemption are returned),
        user still have to have SOLs to fund the Holder which is quite restrictive. 

        The basic idea of the test is to check the following Neon Pass scenario:
        - Neon Pass can append instructions for the generation of temporary Holder Account for the user
            (create_account_with_seed + create_holder).
        - Neon Pass includes usual instructions related to the Neon Transaction.
        - Neon Pass also includes instruction to delete the temporary Holder Account.

        Expected result:
        Solana DOES NOT charge any additional fees (besides gas fee charged as for the usual case 
        through the Operator).
        
        N.B. Solana Runtime checks rent-exemption and balances after the transaction is committed. Given that
        the temporary Holder is deleted in the last instruction, Solana's runtime should be fine with it.  
        '''

        from .solana_utils import get_solana_balance, solana_client, create_account_with_seed, create_holder_account
        from .utils.instructions import TransactionWithComputeBudget, make_ExecuteTrxFromInstruction
        import solana.system_program as sp
        from solana.rpc.types import TxOpts
        from solana.rpc.commitment import Confirmed
        from random import randrange
        from .utils.constants import EVM_LOADER
        from hashlib import sha256
        from solana.transaction import TransactionInstruction, AccountMeta

        def _add_create_holder(trx: TransactionWithComputeBudget, operator_pubkey: PublicKey) -> PublicKey:
            size = 128 * 1024
            # Non rent-exempt.
            fund = 0
            seed = str(randrange(1000000))
            
            # Generate new pubkey for the future holder.
            holder_pubkey = PublicKey(
                sha256(bytes(operator_pubkey) + bytes(seed, 'utf8') + bytes(PublicKey(EVM_LOADER))).digest())
            # Add holder creation instruction into the transaction.
            trx.add(create_account_with_seed(operator_pubkey, operator_pubkey, seed, fund, size))
            trx.add(create_holder_account(holder_pubkey, operator_pubkey, bytes(seed, 'utf8')))
            return holder_pubkey

        def _add_delete_holder(trx: TransactionWithComputeBudget, operator_pubkey: PublicKey, holder_pubkey: PublicKey):
            trx.add(TransactionInstruction(
                program_id=PublicKey(EVM_LOADER),
                data=bytes.fromhex("25"),
                keys=[
                    AccountMeta(pubkey=holder_pubkey, is_signer=False, is_writable=True),
                    AccountMeta(pubkey=operator_pubkey, is_signer=True, is_writable=True),
                ]))

        # Case#1 starts here.
        # Sender with tokens plays as an Operator here.
        user_as_operator = sender_with_tokens.solana_account
        amount = 10
        user_as_operator_balance_before = get_solana_balance(user_as_operator.public_key)
        signed_tx = make_eth_transaction(sender_with_tokens.eth_address, None, sender_with_tokens, amount)

        # Creating NeonPass-like transaction and wrapping it with create and delete holder instructions. 
        trx = TransactionWithComputeBudget(user_as_operator)
        holder_pubkey: PublicKey = _add_create_holder(trx, user_as_operator.public_key)
        trx.add(make_ExecuteTrxFromInstruction(user_as_operator, holder_pubkey, evm_loader, treasury_pool.account,
                                                treasury_pool.buffer, signed_tx.rawTransaction,
                                                [
                                                    sender_with_tokens.balance_account_address,
                                                    sender_with_tokens.solana_account_address,
                                                ], sp.SYS_PROGRAM_ID))
        _add_delete_holder(trx, user_as_operator.public_key, holder_pubkey)

        resp = solana_client.send_transaction(trx, user_as_operator, opts=TxOpts(skip_preflight=False,
                                                                   skip_confirmation=False,
                                                                   preflight_commitment=Confirmed))
        check_transaction_logs_have_text(resp.value, "exit_status=0x11")
        
        user_as_operator_balance_after = get_solana_balance(user_as_operator.public_key)
        user_as_operator_gas_paid = user_as_operator_balance_before - user_as_operator_balance_after


        # Case#2 starts here.
        # Usual operator with owned holder account.
        operator_balance_before = get_solana_balance(operator_keypair.public_key)
        signed_tx = make_eth_transaction(sender_with_tokens.eth_address, None, sender_with_tokens, amount)
        resp = execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            evm_loader,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                sender_with_tokens.balance_account_address,
                sender_with_tokens.solana_account_address,
            ],
            operator_keypair,
        )
        check_transaction_logs_have_text(resp.value, "exit_status=0x11")
        operator_balance_after = get_solana_balance(operator_keypair.public_key)
        operator_gas_paid = operator_balance_before - operator_balance_after

        assert operator_gas_paid == user_as_operator_gas_paid, "Gas paid differs!"
        print(f"Gas paid: {user_as_operator_gas_paid} Lamports")


        