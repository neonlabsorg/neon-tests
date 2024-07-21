from hashlib import sha256
from random import randrange

from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.instruction import Instruction

from solana.transaction import Transaction, AccountMeta

from utils.evm_loader import EvmLoader
from utils.instructions import make_CreateAccountWithSeed, make_CreateHolderAccount


def create_holder(signer: Keypair, evm_loader: EvmLoader, seed: str = None, size: int = None, fund: int = None,
                  storage: Pubkey = None, ) -> Pubkey:
    if size is None:
        size = 128 * 1024
    if fund is None:
        fund = 10 ** 9
    if seed is None:
        seed = str(randrange(1000000))
    if storage is None:
        storage = Pubkey(
            sha256(bytes(signer.pubkey()) + bytes(seed, 'utf8') + bytes(evm_loader.loader_id)).digest())

    print(f"Create holder account with seed: {seed}")

    if evm_loader.get_solana_balance(storage) == 0:
        trx = Transaction()
        trx.add(
            make_CreateAccountWithSeed(signer.pubkey(), signer.pubkey(), seed, fund, size, evm_loader.loader_id),
            make_CreateHolderAccount(storage, signer.pubkey(), bytes(seed, 'utf8'), evm_loader.loader_id)
        )
        evm_loader.send_tx(trx, signer)
    print(f"Created holder account: {storage}")
    return storage


def delete_holder(del_key: Pubkey, acc: Keypair, signer: Keypair, evm_loader: EvmLoader):
    trx = Transaction()

    trx.add(Instruction(
        program_id=evm_loader.loader_id,
        data=bytes.fromhex("25"),
        accounts=[
            AccountMeta(pubkey=del_key, is_signer=False, is_writable=True),
            AccountMeta(pubkey=acc.pubkey(), is_signer=(signer == acc), is_writable=True),
        ]))
    return evm_loader.send_tx(trx, signer)
