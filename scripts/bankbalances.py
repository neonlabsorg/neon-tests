import os
import sys
import time
import decimal

import web3


# w = web3.Web3(web3.HTTPProvider("https://neon-mainnet.everstake.one")) # mainnet
w = web3.Web3(web3.HTTPProvider(os.environ.get("PROXY_URL", "https://devnet.neonevm.org/")))

CHAIN_ID = 245022934  # mainnet
# CHAIN_ID = 245022926  # devnet


def prepare_subbanks_accounts():
    accounts = []
    with open("../mainnet_banks.keys", "r") as f:
        for line in f.readlines():
            line = line.strip()
            if not line:
                continue
            key = line.split()[0]
            accounts.append(w.eth.account.from_key(key))

    for account in accounts:
        balance = w.eth.get_balance(account.address)
        print(f"Address: {account.address} has balance: {w.from_wei(balance, 'ether')}")
    return accounts


def generate_user_accounts(count=100):
    base_account = os.environ.get("BASE_PRIVATE_KEY")
    offset = 0 if not "USERS_OFFSET" in os.environ else int(os.environ.get("USERS_OFFSET"))
    accounts = []
    for i in range(offset, count + offset):
        private_key = int(base_account, 16) + i
        account = w.eth.account.from_key(private_key)
        accounts.append(account)
    return accounts


def verify_users(accounts):
    for i, acc in enumerate(accounts):
        balance = w.eth.get_balance(web3.Web3.to_checksum_address(acc.address))
        # print(f"Account: {acc.address} has funds: index {i} - {balance}")
        if balance == 0:
            print(f"Account: {acc.address} has no funds: index {i} - {balance}")


def distribute(from_account, to_accounts, amount=None):
    main_balance = round(w.from_wei(w.eth.get_balance(from_account.address), "ether") - decimal.Decimal(1))

    if amount is None:
        part_size = w.to_wei(main_balance // len(to_accounts), "ether")
    else:
        part_size = w.to_wei(amount, "ether")

    print(
        f"Main balance: {w.from_wei(w.eth.get_balance(from_account.address), 'ether')}, part in wei: {part_size} in ether: {w.from_wei(part_size, 'ether')}"
    )
    print("---------------------------------------")
    for acc in to_accounts:
        print(f"Send {part_size} wei to {acc.address}")
        transaction = {
            "from": from_account.address,
            "to": acc.address,
            "value": part_size,
            "chainId": CHAIN_ID,
            "gasPrice": w.eth.gas_price,
            "gas": 30000,
            "nonce": w.eth.get_transaction_count(from_account.address),
        }

        transaction["gas"] = w.eth.estimate_gas(transaction)

        signed_tx = w.eth.account.sign_transaction(transaction, from_account.key)
        for _ in range(3):
            try:
                tx = w.eth.send_raw_transaction(signed_tx.rawTransaction)
                w.eth.wait_for_transaction_receipt(tx)
                print(f"    -- TX: {tx.hex()}")
                break
            except Exception as e:
                print(f"Error in send neon, sleep and retry: {e}")
                time.sleep(10)


def collect(from_accounts, to_account):
    for account in from_accounts:
        balance = w.eth.get_balance(account.address)
        if balance < (w.eth.gas_price * 23000):
            print(f"Can't send money from {account.address} because amount is low {balance}")
            continue
        print(f"Send from account: {account.address} to {to_account.address}")
        transaction = {
            "from": account.address,
            "to": to_account.address,
            "value": balance - (w.eth.gas_price * 32000),
            "chainId": CHAIN_ID,
            "gasPrice": w.eth.gas_price,
            "gas": 30000,
            "nonce": w.eth.get_transaction_count(account.address),
        }
        signed_tx = w.eth.account.sign_transaction(transaction, account.key)
        tx = w.eth.send_raw_transaction(signed_tx.rawTransaction)
        w.eth.wait_for_transaction_receipt(tx)
        print(f"    -- TX: {tx.hex()}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("You should use: send|collect users|subbanks")
        sys.exit(1)
    instruction = sys.argv[1]
    acc_type = sys.argv[2]
    if acc_type == "users":
        count = 100
        if len(sys.argv) == 4:
            count = int(sys.argv[3])
        accounts = generate_user_accounts(count)
    else:
        accounts = prepare_subbanks_accounts()
    main_bank = w.eth.account.from_key(os.environ.get("BANK_PRIVATE_KEY"))
    if instruction == "send":
        if acc_type == "users":
            distribute(main_bank, accounts, amount=2)
        else:
            distribute(main_bank, accounts)
    elif instruction == "collect":
        collect(accounts, main_bank)
    elif instruction == "verify":
        verify_users(accounts)
