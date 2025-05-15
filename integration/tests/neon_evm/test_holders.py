import json
import pathlib


from eth_keys import keys as eth_keys
import solders.system_program as sp
from solana.rpc.commitment import Confirmed
from solana.transaction import Transaction
from solders.instruction import Instruction, AccountMeta
from solders.keypair import Keypair

from utils.consts import InstructionTags, OPERATOR_KEYPAIR_PATH


def test_create_holder_instruction(operator_keypair, evm_loader):
    evm_loader.create_holder(operator_keypair)
    evm_loader.create_get_authority_address()
    # /// Create Holder Account
    # ///
    # /// Accounts:
    # ///  `[WRITE]` Holder Account
    # ///  `[SIGNER]` Holder Account Owner
    # /// Instruction data:
    # ///  0..8          - seed length in little endian
    # ///  8..8+seed_len - seed in utf-8
    # HolderCreate,
    # ---> Go check in sql database transaction


def test_treasury_collect(evm_loader):
    evm_loader.create_treasury_pool_address()


def test_delete_holder_instruction(operator_keypair, evm_loader):
    holder_acc = evm_loader.create_holder(operator_keypair)
    evm_loader.delete_holder(holder_acc, operator_keypair, operator_keypair)


# def test_collect_treasure(treasury_pool, treasury_pool_new, operator_keypair):
#     # /// Collect lamports from treasury pool accounts to main pool balance
#     # ///
#     # /// Accounts:
#     # ///  `[WRITE]` Main treasury balance: PDA["treasury_pool"]
#     # ///  `[WRITE]` Auxiliary treasury balance: PDA["treasury_pool", index.to_le_bytes()]
#     # ///  `[]` System program
#     # /// Instruction data:
#     # ///  0..4 - treasury index in little endian
#     # CollectTreasure,
#     instruction = Instruction(
#         program_id=COUNTER_ID,
#         accounts=[
#             AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
#         ],
#         data=bytes([0x1]),
#     )

# def test_holder_write(session_user, second_session_user, evm_loader, operator_keypair):
#     holder_acc = evm_loader.create_holder(operator_keypair)
#     signed_tx = make_eth_transaction(evm_loader, second_session_user.eth_address, None, session_user, 10)
#     evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)


def test_create_account_balance(session_user):
    print("""....""")


def test_deposit(account_with_all_tokens):
    print(""".....""")


def test_create_operator_balance_account(neon_user, evm_loader):
    with open(pathlib.Path(f"{OPERATOR_KEYPAIR_PATH}/id.json"), "r") as key:
        secret_key = json.load(key)
        account = Keypair.from_bytes(secret_key)

    evm_loader.request_airdrop(account.pubkey(), 1000 * 10**9, commitment=Confirmed)

    operator_ether = eth_keys.PrivateKey(account.secret()[:32]).public_key.to_canonical_address()
    evm_loader.create_operator_balance_account(account, operator_ether, evm_loader.chain_id)
    evm_loader.withdraw_operator_balance_account(account, operator_ether, evm_loader.chain_id)

    print("test_create_operator_balance_account")


def test_create_treasury_pool(operator_keypair, treasury_pool_main, treasury_pool_new, evm_loader):
    #     # /// Collect lamports from treasury pool accounts to main pool balance
    #     # ///
    #     # /// Accounts:
    #     # ///  `[WRITE]` Main treasury balance: PDA["treasury_pool"]
    #     # ///  `[WRITE]` Auxiliary treasury balance: PDA["treasury_pool", index.to_le_bytes()]
    #     # ///  `[]` System program
    #     # /// Instruction data:
    #     # ///  0..4 - treasury index in little endian
    #     # CollectTreasure,
    main_address = treasury_pool_main.account
    tag = InstructionTags.COLLECT_TREASURE

    trx = Transaction()
    trx.add(
        Instruction(
            accounts=[
                # AccountMeta(pubkey=operator_keypair.pubkey(), is_signer=True, is_writable=False),
                AccountMeta(pubkey=main_address, is_signer=False, is_writable=True),
                AccountMeta(pubkey=treasury_pool_new.account, is_signer=False, is_writable=True),
                AccountMeta(pubkey=sp.ID, is_signer=False, is_writable=False),
                AccountMeta(pubkey=operator_keypair.pubkey(), is_signer=True, is_writable=False),
            ],
            program_id=evm_loader.loader_id,
            data=tag + treasury_pool_new.buffer,
        )
    )
    sig = evm_loader.send_tx_and_check_status_ok(trx, operator_keypair)
    print(sig)
