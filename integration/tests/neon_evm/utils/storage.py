from solana.publickey import PublicKey
from solana.keypair import Keypair

from .instructions import make_DeleteHolder, make_CreateHolder
from ..solana_utils import send_transaction, solana_client
from solana.transaction import Transaction


def create_holder(signer: Keypair, seed: str = None, size: int = None, fund: int = None,
                  storage: PublicKey = None) -> PublicKey:
    storage, trx = make_CreateHolder(signer, seed, size, fund, storage)
    send_transaction(solana_client, trx, signer)
    print(f"Created holder account: {storage}")
    return storage


def delete_holder(del_key: PublicKey, acc: Keypair, signer: Keypair):
    trx = Transaction()
    trx.add(make_DeleteHolder(del_key, acc, signer))
    return send_transaction(solana_client, trx, signer)
