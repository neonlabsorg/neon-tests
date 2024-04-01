from hashlib import sha256
from random import randrange

import pytest
import solana
from solana.publickey import PublicKey
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from solana.transaction import Transaction

from . import solana_utils
from .solana_utils import (
    solana_client,
    write_transaction_to_holder_account,
    send_transaction_step_from_account,
    get_solana_balance,
    execute_transaction_steps_from_account, execute_trx_from_instruction,
)
from .utils.assert_messages import InstructionAsserts
from .utils.constants import EVM_LOADER
from .utils.contract import make_deployment_transaction, make_contract_call_trx
from .utils.ethereum import make_eth_transaction
from .utils.instructions import make_WriteHolder, TransactionWithComputeBudget, make_CreateHolder, \
    make_ExecuteTrxFromInstruction
from .utils.layouts import HOLDER_ACCOUNT_INFO_LAYOUT
from .utils.storage import create_holder, delete_holder
from .utils.transaction_checks import check_transaction_logs_have_text


def transaction_from_holder(key: PublicKey):
    data = solana_client.get_account_info(key, commitment=Confirmed).value.data
    header = HOLDER_ACCOUNT_INFO_LAYOUT.parse(data)

    return data[HOLDER_ACCOUNT_INFO_LAYOUT.sizeof() :][: header.len]


def test_create_holder_account(operator_keypair):
    holder_acc = create_holder(operator_keypair)
    info = solana_client.get_account_info(holder_acc, commitment=Confirmed)
    assert info.value is not None, "Holder account is not created"
    assert info.value.lamports == 1000000000, "Account balance is not correct"


def test_create_the_same_holder_account_by_another_user(operator_keypair, session_user):
    seed = str(randrange(1000000))
    storage = PublicKey(
        sha256(bytes(operator_keypair.public_key) + bytes(seed, "utf8") + bytes(PublicKey(EVM_LOADER))).digest()
    )
    create_holder(operator_keypair, seed=seed, storage=storage)

    trx = Transaction()
    trx.add(
        solana_utils.create_account_with_seed(
            session_user.solana_account.public_key, session_user.solana_account.public_key, seed, 10**9, 128 * 1024
        ),
        solana_utils.create_holder_account(storage, session_user.solana_account.public_key, bytes(seed, "utf8")),
    )

    error = str.format(InstructionAsserts.INVALID_ACCOUNT, storage)
    with pytest.raises(solana.rpc.core.RPCException, match=error):
        solana_utils.send_transaction(solana_client, trx, session_user.solana_account)


def test_write_tx_to_holder(operator_keypair, session_user, second_session_user, evm_loader):
    holder_acc = create_holder(operator_keypair)
    signed_tx = make_eth_transaction(second_session_user.eth_address, None, session_user, 10)
    write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
    assert signed_tx.rawTransaction == transaction_from_holder(holder_acc), "Account data is not correct"


def test_write_tx_to_holder_in_parts(operator_keypair, session_user):
    holder_acc = create_holder(operator_keypair)

    signed_tx = make_deployment_transaction(session_user, "neon-evm/erc20_for_spl_factory", "ERC20ForSplFactory")
    write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
    assert signed_tx.rawTransaction == transaction_from_holder(holder_acc), "Account data is not correct"


def test_write_tx_to_holder_by_no_owner(operator_keypair, session_user, second_session_user, evm_loader):
    holder_acc = create_holder(operator_keypair)

    signed_tx = make_eth_transaction(second_session_user.eth_address, None, session_user, 10)
    with pytest.raises(solana.rpc.core.RPCException, match="invalid owner"):
        write_transaction_to_holder_account(signed_tx, holder_acc, session_user.solana_account)


def test_delete_holder(operator_keypair):
    holder_acc = create_holder(operator_keypair)
    delete_holder(holder_acc, operator_keypair, operator_keypair)
    info = solana_client.get_account_info(holder_acc, commitment=Confirmed)
    assert info.value is None, "Holder account isn't deleted"


def test_success_refund_after_holder_deliting(operator_keypair):
    holder_acc = create_holder(operator_keypair)

    pre_storage = get_solana_balance(holder_acc)
    pre_acc = get_solana_balance(operator_keypair.public_key)

    delete_holder(holder_acc, operator_keypair, operator_keypair)

    post_acc = get_solana_balance(operator_keypair.public_key)

    assert pre_storage + pre_acc, post_acc + 5000


def test_delete_holder_by_no_owner(operator_keypair, user_account):
    holder_acc = create_holder(operator_keypair)
    with pytest.raises(solana.rpc.core.RPCException, match="invalid owner"):
        delete_holder(holder_acc, user_account.solana_account, user_account.solana_account)


def test_write_to_not_finalized_holder(
    rw_lock_contract, user_account, evm_loader, operator_keypair, treasury_pool, new_holder_acc
):
    signed_tx = make_contract_call_trx(user_account, rw_lock_contract, "unchange_storage(uint8,uint8)", [1, 1])
    write_transaction_to_holder_account(signed_tx, new_holder_acc, operator_keypair)

    send_transaction_step_from_account(
        operator_keypair,
        evm_loader,
        treasury_pool,
        new_holder_acc,
        [user_account.solana_account_address, user_account.balance_account_address, rw_lock_contract.solana_address],
        1,
        operator_keypair,
    )

    signed_tx2 = make_contract_call_trx(user_account, rw_lock_contract, "unchange_storage(uint8,uint8)", [1, 1])

    with pytest.raises(solana.rpc.core.RPCException, match="invalid tag"):
        write_transaction_to_holder_account(signed_tx2, new_holder_acc, operator_keypair)


def test_write_to_finalized_holder(
    rw_lock_contract, session_user, evm_loader, operator_keypair, treasury_pool, new_holder_acc
):
    signed_tx = make_contract_call_trx(session_user, rw_lock_contract, "unchange_storage(uint8,uint8)", [1, 1])
    write_transaction_to_holder_account(signed_tx, new_holder_acc, operator_keypair)

    execute_transaction_steps_from_account(
        operator_keypair,
        evm_loader,
        treasury_pool,
        new_holder_acc,
        [session_user.solana_account_address, session_user.balance_account_address, rw_lock_contract.solana_address],
    )
    signed_tx2 = make_contract_call_trx(session_user, rw_lock_contract, "unchange_storage(uint8,uint8)", [1, 1])

    write_transaction_to_holder_account(signed_tx2, new_holder_acc, operator_keypair)
    assert signed_tx2.rawTransaction == transaction_from_holder(new_holder_acc), "Account data is not correct"


def test_holder_write_integer_overflow(operator_keypair, holder_acc):
    overflow_offset = int(0xFFFFFFFFFFFFFFFF)

    trx = Transaction()
    trx.add(make_WriteHolder(operator_keypair.public_key, holder_acc, b"\x00" * 32, overflow_offset, b"\x00" * 1))
    with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.HOLDER_OVERFLOW):
        solana_client.send_transaction(
            trx,
            operator_keypair,
            opts=TxOpts(skip_confirmation=True, preflight_commitment=Confirmed),
        )


def test_holder_write_account_size_overflow(operator_keypair, holder_acc):
    overflow_offset = int(0xFFFFFFFF)

    trx = Transaction()
    trx.add(make_WriteHolder(operator_keypair.public_key, holder_acc, b"\x00" * 32, overflow_offset, b"\x00" * 1))
    with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.HOLDER_INSUFFICIENT_SIZE):
        solana_client.send_transaction(
            trx,
            operator_keypair,
            opts=TxOpts(skip_confirmation=True, preflight_commitment=Confirmed),
        )

def test_temporary_holder_acc_is_free(
    treasury_pool, sender_with_tokens, evm_loader
):
    # Check that Solana DOES NOT charge any additional fees for the temporary holder account
    # This case is used by neonpass
    user_as_operator = sender_with_tokens.solana_account
    amount = 10
    operator_balance_before = get_solana_balance(user_as_operator.public_key)

    trx = TransactionWithComputeBudget(user_as_operator)
    holder_pubkey, create_holder_instruction = make_CreateHolder(user_as_operator, fund=0)
    trx.add(create_holder_instruction)
    signed_tx = make_eth_transaction(sender_with_tokens.eth_address, None, sender_with_tokens, amount)

    trx.add(
        make_ExecuteTrxFromInstruction(
            user_as_operator,
            holder_pubkey,
            evm_loader,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx.rawTransaction,
            [
                sender_with_tokens.balance_account_address,
                sender_with_tokens.solana_account_address,
            ],
        )
    )
    resp = solana_client.send_transaction(
        trx,
        user_as_operator,
        opts=TxOpts(skip_preflight=False, skip_confirmation=False, preflight_commitment=Confirmed),
    )
    check_transaction_logs_have_text(resp.value, "exit_status=0x11")
    operator_balance_after = get_solana_balance(user_as_operator.public_key)
    operator_gas_paid_with_holder = operator_balance_before - operator_balance_after

    signed_tx = make_eth_transaction(sender_with_tokens.eth_address, None, sender_with_tokens, amount)
    holder_acc = create_holder(sender_with_tokens.solana_account)
    operator_balance_before = get_solana_balance(user_as_operator.public_key)

    resp = execute_trx_from_instruction(
        user_as_operator,
        holder_acc,
        evm_loader,
        treasury_pool.account,
        treasury_pool.buffer,
        signed_tx,
        [
            sender_with_tokens.balance_account_address,
            sender_with_tokens.solana_account_address,
        ],
        user_as_operator,
    )
    check_transaction_logs_have_text(resp.value, "exit_status=0x11")
    operator_balance_after = get_solana_balance(user_as_operator.public_key)
    operator_gas_paid_without_holder = operator_balance_before - operator_balance_after

    assert operator_gas_paid_without_holder == operator_gas_paid_with_holder, "Gas paid differs!"
