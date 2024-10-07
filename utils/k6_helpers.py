import json
import os
from utils.accounts import EthAccounts
from utils.faucet import Faucet
from utils.web3client import NeonChainWeb3Client

def k6_prepare_accounts(network, network_object, users, balance, bank_account):
    print("Setting k6 envs...")
    k6_set_envs(network, users, balance, bank_account)

    print("Creating accounts...")
    accounts = {}
    web3_client = NeonChainWeb3Client(proxy_url=network_object["proxy_url"])
    faucet = Faucet(faucet_url=network_object['faucet_url'], web3_client=web3_client)
    account_manager = EthAccounts(web3_client, faucet, None)

    # We create 2 accounts for each k6 virtual user: sender and receiver.
    # We need to create 2*VU accounts cause we want to make sure account's nonces is not overlapping.
    for i in range(2*int(users)):
        account_sender = account_manager.create_account(balance=int(balance))
        account_receiver = account_manager.create_account(balance=0)
        print(f"Account {str(i)} sender: {account_sender.address}, initial balance: {balance} Neon.")
        print(f"Account {str(i)} receiver: {account_receiver.address}")
        accounts[i] = {"sender_address": str(account_sender.address), 
                       "sender_key": str(account_sender.key.hex())[2:], 
                       "receiver_address": str(account_receiver.address)}

    with open('./loadtesting/k6/data/accounts.json', 'w', encoding='utf-8') as f:
        json.dump(accounts, f)

def k6_set_envs(network, users_number=None, initial_balance=None, bank_account=None):
    os.environ["K6_NETWORK"] = network
    os.environ["K6_USERS_NUMBER"] = users_number
    os.environ["K6_INITIAL_BALANCE"] = initial_balance
    
    if bank_account is not None:
        os.environ["K6_BANK_ACCOUNT"] = bank_account
