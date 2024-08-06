from hashlib import sha256
from random import randrange

import pytest
import solana
from solana.publickey import PublicKey
from solana.rpc.commitment import Confirmed
from solana.transaction import Transaction

from utils.evm_loader import EvmLoader
from utils.instructions import make_WriteHolder, make_CreateAccountWithSeed, make_CreateHolderAccount
from utils.layouts import HOLDER_ACCOUNT_INFO_LAYOUT

from .utils.assert_messages import InstructionAsserts
from .utils.contract import make_deployment_transaction, make_contract_call_trx
from .utils.ethereum import make_eth_transaction
from .utils.storage import create_holder, delete_holder


def transaction_from_holder(evm_loader:EvmLoader, key: PublicKey):
    data = evm_loader.get_account_info(key, commitment=Confirmed).value.data
    header = HOLDER_ACCOUNT_INFO_LAYOUT.parse(data)

    return data[HOLDER_ACCOUNT_INFO_LAYOUT.sizeof() :][: header.len]


def test_create_holder_account(operator_keypair, evm_loader):
    holder_acc = create_holder(operator_keypair, evm_loader)
    info = evm_loader.get_account_info(holder_acc, commitment=Confirmed)
    assert info.value is not None, "Holder account is not created"
    assert info.value.lamports == 1000000000, "Account balance is not correct"


def test_create_the_same_holder_account_by_another_user(operator_keypair, session_user, evm_loader):
    seed = str(randrange(1000000))
    storage = PublicKey(
        sha256(bytes(operator_keypair.public_key) + bytes(seed, "utf8") + bytes(evm_loader.loader_id)).digest()
    )
    create_holder(operator_keypair, evm_loader, seed=seed, storage=storage)

    trx = Transaction()
    trx.add(
        make_CreateAccountWithSeed(
            session_user.solana_account.public_key,
            session_user.solana_account.public_key,
            seed, 10**9, 128 * 1024, evm_loader.loader_id
        ),
        make_CreateHolderAccount(storage, session_user.solana_account.public_key, bytes(seed, "utf8"), evm_loader.loader_id)
    )

    error = str.format(InstructionAsserts.INVALID_ACCOUNT, storage)
    with pytest.raises(solana.rpc.core.RPCException, match=error):
        evm_loader.send_tx(trx, session_user.solana_account)


def test_write_tx_to_holder(operator_keypair, session_user, second_session_user, evm_loader):
    holder_acc = create_holder(operator_keypair, evm_loader)
    signed_tx = make_eth_transaction(evm_loader, second_session_user.eth_address, None, session_user, 10)
    evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
    assert signed_tx.rawTransaction == transaction_from_holder(evm_loader, holder_acc), "Account data is not correct"


def test_write_tx_to_holder_in_parts(operator_keypair, session_user, evm_loader):
    holder_acc = create_holder(operator_keypair, evm_loader)

    signed_tx = make_deployment_transaction(
        evm_loader, session_user, "external/neon-evm/erc20_for_spl_factory", "ERC20ForSplFactory"
    )
    evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
    assert signed_tx.rawTransaction == transaction_from_holder(evm_loader, holder_acc), "Account data is not correct"


def test_write_tx_to_holder_by_no_owner(operator_keypair, session_user, second_session_user, evm_loader):
    holder_acc = create_holder(operator_keypair, evm_loader)

    signed_tx = make_eth_transaction(evm_loader, second_session_user.eth_address, None, session_user, 10)
    with pytest.raises(solana.rpc.core.RPCException, match="invalid owner"):
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, session_user.solana_account)


def test_delete_holder(operator_keypair, evm_loader):
    holder_acc = create_holder(operator_keypair, evm_loader)
    delete_holder(holder_acc, operator_keypair, operator_keypair, evm_loader)
    info = evm_loader.get_account_info(holder_acc, commitment=Confirmed)
    assert info.value is None, "Holder account isn't deleted"


def test_success_refund_after_holder_deleting(operator_keypair, evm_loader):
    holder_acc = create_holder(operator_keypair, evm_loader)

    pre_storage = evm_loader.get_solana_balance(holder_acc)
    pre_acc = evm_loader.get_solana_balance(operator_keypair.public_key)

    delete_holder(holder_acc, operator_keypair, operator_keypair, evm_loader)

    post_acc = evm_loader.get_solana_balance(operator_keypair.public_key)

    assert pre_storage + pre_acc, post_acc + 5000


def test_delete_holder_by_no_owner(operator_keypair, user_account, evm_loader):
    holder_acc = create_holder(operator_keypair, evm_loader)
    with pytest.raises(solana.rpc.core.RPCException, match="invalid owner"):
        delete_holder(holder_acc, user_account.solana_account, user_account.solana_account, evm_loader)


def test_write_to_not_finalized_holder(
    rw_lock_contract, user_account, evm_loader, operator_keypair, treasury_pool, new_holder_acc
):
    signed_tx = make_contract_call_trx(
        evm_loader, user_account, rw_lock_contract, "unchange_storage(uint8,uint8)", [1, 1]
    )
    evm_loader.write_transaction_to_holder_account(signed_tx, new_holder_acc, operator_keypair)
    operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)
    evm_loader.send_transaction_step_from_account(
        operator_keypair,
        operator_balance,
        treasury_pool,
        new_holder_acc,
        [user_account.solana_account_address, user_account.balance_account_address, rw_lock_contract.solana_address],
        1,
        operator_keypair,
    )

    signed_tx2 = make_contract_call_trx(
        evm_loader, user_account, rw_lock_contract, "unchange_storage(uint8,uint8)", [1, 1]
    )

    with pytest.raises(solana.rpc.core.RPCException, match="invalid tag"):
        evm_loader.write_transaction_to_holder_account(signed_tx2, new_holder_acc, operator_keypair)


def test_write_to_finalized_holder(
    rw_lock_contract, session_user, evm_loader, operator_keypair, treasury_pool, new_holder_acc
):
    signed_tx = make_contract_call_trx(
        evm_loader, session_user, rw_lock_contract, "unchange_storage(uint8,uint8)", [1, 1]
    )
    evm_loader.write_transaction_to_holder_account(signed_tx, new_holder_acc, operator_keypair)

    evm_loader.execute_transaction_steps_from_account(
        operator_keypair,
        treasury_pool,
        new_holder_acc,
        [session_user.solana_account_address, session_user.balance_account_address, rw_lock_contract.solana_address],
    )
    signed_tx2 = make_contract_call_trx(
        evm_loader, session_user, rw_lock_contract, "unchange_storage(uint8,uint8)", [1, 1]
    )

    evm_loader.write_transaction_to_holder_account(signed_tx2, new_holder_acc, operator_keypair)
    assert signed_tx2.rawTransaction == transaction_from_holder(
        evm_loader, new_holder_acc
    ), "Account data is not correct"


def test_holder_write_integer_overflow(operator_keypair, holder_acc, evm_loader):
    overflow_offset = int(0xFFFFFFFFFFFFFFFF)

    trx = Transaction()
    trx.add(
        make_WriteHolder(
            operator_keypair.public_key, evm_loader.loader_id, holder_acc, b"\x00" * 32, overflow_offset, b"\x00" * 1
        )
    )
    with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.HOLDER_OVERFLOW):
        evm_loader.send_tx(trx, operator_keypair)


def test_holder_write_account_size_overflow(operator_keypair, holder_acc, evm_loader):
    overflow_offset = int(0xFFFFFFFF)

    trx = Transaction()
    trx.add(
        make_WriteHolder(
            operator_keypair.public_key, evm_loader.loader_id, holder_acc, b"\x00" * 32, overflow_offset, b"\x00" * 1
        )
    )
    with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.HOLDER_INSUFFICIENT_SIZE):
        evm_loader.send_tx(trx, operator_keypair)
