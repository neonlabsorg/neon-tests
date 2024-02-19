import random

import pytest

from eth_utils import abi
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.commitment import Confirmed
from solana.rpc.core import RPCException
from solana.rpc.types import TxOpts
import spl.token.client
from solana.transaction import TransactionInstruction, AccountMeta
from spl.token.instructions import create_associated_token_account, TransferParams, transfer

from integration.tests.neon_evm.solana_utils import (
    EvmLoader,
    execute_trx_from_instruction_with_solana_call,
    solana_client, get_solana_account_data, create_account, wait_for_account_to_exists,
)
from integration.tests.neon_evm.types.types import Caller
from integration.tests.neon_evm.utils.call_solana import SolanaCaller
from integration.tests.neon_evm.utils.constants import (
    COMPUTE_BUDGET_ID,
    MEMO_PROGRAM_ID,
    SOLANA_CALL_PRECOMPILED_ID,
    NEON_TOKEN_MINT_ID,
    COUNTER_ID, SYSTEM_ADDRESS, TRANSFER_SOL_ID, TRANSFER_TOKENS_ID,
)
from integration.tests.neon_evm.utils.contract import deploy_contract
from integration.tests.neon_evm.utils.ethereum import make_eth_transaction
from integration.tests.neon_evm.utils.instructions import make_CreateAssociatedTokenIdempotent
from integration.tests.neon_evm.utils.layouts import COUNTER_ACCOUNT_LAYOUT
from integration.tests.neon_evm.utils.transaction_checks import check_transaction_logs_have_text

from utils.instructions import DEFAULT_UNITS
from utils.metaplex import ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID, TOKEN_PROGRAM_ID


def _create_mint_and_accounts(from_wallet, to_wallet, amount):
    mint = spl.token.client.Token.create_mint(
        conn=solana_client,
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
    return mint, from_token_account, to_token_account


class TestInteroperability:
    @pytest.fixture(scope="function")
    def solana_caller(
            self, evm_loader: EvmLoader, operator_keypair: Keypair, session_user: Caller, treasury_pool, holder_acc
    ) -> SolanaCaller:
        return SolanaCaller(operator_keypair, session_user, evm_loader, treasury_pool, holder_acc)

    def test_get_solana_address_by_neon_address(self, sender_with_tokens, solana_caller):
        sol_addr = solana_caller.get_solana_address_by_neon_address(sender_with_tokens.eth_address.hex())
        assert sol_addr == sender_with_tokens.solana_account_address

    def test_get_payer(self, solana_caller):
        assert solana_caller.get_payer() != ""

    def test_get_solana_PDA(self, solana_caller):
        addr = solana_caller.get_solana_PDA(COUNTER_ID, b"123")
        assert addr == (PublicKey.find_program_address([b"123"], COUNTER_ID))[0]

    def test_get_eth_ext_authority(self, solana_caller, sender_with_tokens):
        addr = solana_caller.get_eth_ext_authority(b"123", sender_with_tokens)
        assert addr != ""

    def test_create_resource(self, sender_with_tokens, solana_caller):
        salt = b"123"
        resource_address = solana_caller.create_resource(sender_with_tokens, salt, 8, 1000000000, MEMO_PROGRAM_ID)
        acc_info = solana_client.get_account_info(resource_address, commitment=Confirmed)
        assert acc_info.value is not None

    def test_execute_from_instruction_for_compute_budget(self, sender_with_tokens, solana_caller):
        instruction = TransactionInstruction(
            program_id=COMPUTE_BUDGET_ID,
            keys=[AccountMeta(sender_with_tokens.solana_account_address, is_signer=False, is_writable=False)],
            data=bytes.fromhex("02") + DEFAULT_UNITS.to_bytes(4, "little"),
        )
        resp = solana_caller.execute(COMPUTE_BUDGET_ID, instruction, sender=sender_with_tokens)
        check_transaction_logs_have_text(resp.value, "exit_status=0x11")

    def test_execute_from_instruction_for_call_memo(
            self, sender_with_tokens, neon_api_client, operator_keypair, evm_loader, treasury_pool, sol_client
    ):
        contract = deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "precompiled/call_solana_test",
            evm_loader,
            treasury_pool,
            contract_name="Test",
        )

        data = abi.function_signature_to_4byte_selector("call_memo()")
        signed_tx = make_eth_transaction(contract.eth_address, data, sender_with_tokens)

        resp = execute_trx_from_instruction_with_solana_call(
            operator_keypair,
            evm_loader,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                SOLANA_CALL_PRECOMPILED_ID,
                MEMO_PROGRAM_ID,
                contract.balance_account_address,
                contract.solana_address,
            ],
            operator_keypair,
        )
        check_transaction_logs_have_text(resp.value, "exit_status=0x11")

    def test_execute_from_account_create_acc(self, sender_with_tokens, solana_caller):
        payer = solana_caller.get_payer()
        instruction = make_CreateAssociatedTokenIdempotent(
            payer, sender_with_tokens.solana_account_address, NEON_TOKEN_MINT_ID
        )
        resp = solana_caller.batch_execute(
            [(ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID, 2039280, instruction)], sender_with_tokens
        )
        check_transaction_logs_have_text(resp.value, "exit_status=0x11")

    def test_execute_several_instr_in_one_trx(self, sender_with_tokens, solana_caller):
        instruction_count = 10
        resource_addr = solana_caller.create_resource(sender_with_tokens, b"123", 8, 1000000000, COUNTER_ID)

        instruction = TransactionInstruction(
            program_id=COUNTER_ID,
            keys=[AccountMeta(resource_addr, is_signer=False, is_writable=True), ],
            data=bytes([0x1])
        )
        call_params = []
        for i in range(instruction_count):
            call_params.append((COUNTER_ID, 0, instruction))

        resp = solana_caller.batch_execute(call_params, sender_with_tokens)

        check_transaction_logs_have_text(resp.value, "exit_status=0x11")
        info: bytes = get_solana_account_data(solana_client, resource_addr, COUNTER_ACCOUNT_LAYOUT.sizeof())
        layout = COUNTER_ACCOUNT_LAYOUT.parse(info)
        assert layout.count == instruction_count

    def test_limit_of_simple_instr_in_one_trx(self, sender_with_tokens, solana_caller):
        instruction_count = 24
        resource_addr = solana_caller.create_resource(sender_with_tokens, b"123", 8, 1000000000, COUNTER_ID)

        instruction = TransactionInstruction(
            program_id=COUNTER_ID,
            keys=[AccountMeta(resource_addr, is_signer=False, is_writable=True), ],
            data=bytes([0x1])
        )
        call_params = []
        for i in range(instruction_count):
            call_params.append((COUNTER_ID, 0, instruction))

        with pytest.raises(RPCException, match="failed: exceeded CUs meter at BPF instruction"):
            solana_caller.batch_execute(call_params, sender_with_tokens)

    def test_transfer_sol_with_cpi(self, solana_caller, sender_with_tokens):
        recipient = create_account(sender_with_tokens.solana_account, 0, TRANSFER_SOL_ID)
        amount = random.randint(1, 1000000)
        instruction = TransactionInstruction(
            program_id=TRANSFER_SOL_ID,
            keys=[AccountMeta(sender_with_tokens.solana_account.public_key, is_signer=True, is_writable=True),
                  AccountMeta(recipient.public_key, is_signer=False, is_writable=True),
                  AccountMeta(PublicKey(SYSTEM_ADDRESS), is_signer=False, is_writable=False),
                  ],
            data=bytes([0x0]) + amount.to_bytes(8, "little")
        )
        call_params = [(TRANSFER_SOL_ID, 0, instruction)]
        balance_before = solana_client.get_balance(recipient.public_key).value
        resp = solana_caller.batch_execute(call_params, sender_with_tokens,
                                           additional_signers=[sender_with_tokens.solana_account])
        check_transaction_logs_have_text(resp.value, "exit_status=0x11")
        balance_after = solana_client.get_balance(recipient.public_key).value
        assert balance_after == balance_before + amount

    def test_transfer_sol_without_cpi(self, solana_caller, sender_with_tokens):
        amount = random.randint(1, 1000000)
        sender = create_account(sender_with_tokens.solana_account, 0, TRANSFER_SOL_ID, lamports=100 * 10 ** 9)
        recipient = create_account(sender_with_tokens.solana_account, 0, TRANSFER_SOL_ID)

        instruction = TransactionInstruction(
            program_id=TRANSFER_SOL_ID,
            keys=[AccountMeta(sender.public_key, is_signer=True, is_writable=True),
                  AccountMeta(recipient.public_key, is_signer=False, is_writable=True),
                  ],
            data=bytes([0x1]) + amount.to_bytes(8, "little")
        )
        call_params = [(TRANSFER_SOL_ID, 0, instruction)]
        balance_before = solana_client.get_balance(recipient.public_key).value
        resp = solana_caller.batch_execute(call_params, sender_with_tokens, additional_signers=[sender])
        balance_after = solana_client.get_balance(recipient.public_key).value
        check_transaction_logs_have_text(resp.value, "exit_status=0x11")
        assert balance_after == balance_before + amount

    def test_transfer_with_PDA_signature(self, solana_caller, sender_with_tokens):
        from_wallet = Keypair.generate()
        to_wallet = Keypair.generate()
        amount = 100000
        solana_client.request_airdrop(from_wallet.public_key, 1000 * 10 ** 9, commitment=Confirmed)
        wait_for_account_to_exists(solana_client, from_wallet.public_key)

        mint, from_token_account, to_token_account = _create_mint_and_accounts(from_wallet, to_wallet, amount)

        authority_pubkey = solana_caller.get_solana_PDA(TRANSFER_TOKENS_ID, b"authority")
        mint.set_authority(from_token_account,
                           from_wallet,
                           spl.token.instructions.AuthorityType.ACCOUNT_OWNER,
                           authority_pubkey,
                           opts=TxOpts(skip_confirmation=False, skip_preflight=True))

        instruction = TransactionInstruction(
            program_id=TRANSFER_TOKENS_ID,
            keys=[AccountMeta(from_token_account, is_signer=False, is_writable=True),
                  AccountMeta(mint.pubkey, is_signer=False, is_writable=True),
                  AccountMeta(to_token_account, is_signer=False, is_writable=True),
                  AccountMeta(authority_pubkey, is_signer=False, is_writable=True),
                  AccountMeta(PublicKey(TOKEN_PROGRAM_ID), is_signer=False, is_writable=True),

                  ],
            data=bytes([0x0])
        )

        resp = solana_caller.execute(TRANSFER_TOKENS_ID, instruction, sender=sender_with_tokens)
        check_transaction_logs_have_text(resp.value, "exit_status=0x11")
        assert int(mint.get_balance(to_token_account, commitment=Confirmed).value.amount) == amount

    def test_transfer_tokens_with_ext_authority(self, solana_caller, sender_with_tokens):
        from_wallet = sender_with_tokens
        to_wallet = Keypair.generate()
        amount = 100000
        mint, from_token_account, to_token_account = _create_mint_and_accounts(from_wallet.solana_account,
                                                                                    to_wallet, amount)
        seed = b'myseed'
        authority = solana_caller.get_eth_ext_authority(seed, from_wallet)

        mint.set_authority(from_token_account,
                           from_wallet.solana_account,
                           spl.token.instructions.AuthorityType.ACCOUNT_OWNER,
                           authority,
                           opts=TxOpts(skip_confirmation=False, skip_preflight=True))

        instruction = transfer(
            TransferParams(TOKEN_PROGRAM_ID, from_token_account, to_token_account, authority, amount))

        resp = solana_caller.execute_with_seed(TOKEN_PROGRAM_ID, instruction, seed, sender=from_wallet)
        check_transaction_logs_have_text(resp.value, "exit_status=0x11")

        assert int(mint.get_balance(to_token_account, commitment=Confirmed).value.amount) == amount

    def test_transfer_tokens_with_unauthorized_signer(self, solana_caller, sender_with_tokens):
        from_wallet = sender_with_tokens
        to_wallet = Keypair.generate()
        amount = 100000
        mint, from_token_account, to_token_account = _create_mint_and_accounts(from_wallet.solana_account,
                                                                                    to_wallet, amount)

        authority = solana_caller.get_eth_ext_authority(b'myseed', from_wallet)

        mint.set_authority(from_token_account,
                           from_wallet.solana_account,
                           spl.token.instructions.AuthorityType.ACCOUNT_OWNER,
                           authority,
                           opts=TxOpts(skip_confirmation=False, skip_preflight=True))

        instruction = transfer(
            TransferParams(TOKEN_PROGRAM_ID, from_token_account, to_token_account, authority, amount))
        with pytest.raises(RPCException, match="Cross-program invocation with unauthorized signer or writable account"):
            solana_caller.execute(TOKEN_PROGRAM_ID, instruction, sender=from_wallet)