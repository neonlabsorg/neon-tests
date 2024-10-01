import json
import os
from utils.accounts import EthAccounts
from utils.faucet import Faucet
from utils.web3client import NeonChainWeb3Client

def k6_prepare_accounts(network, users, balance, bank_account):
    print("Setting k6 envs...")
    config = k6_set_envs(network, "envs.json", users, balance, bank_account)

    print("Creating accounts...")
    accounts = {}
    web3_client = NeonChainWeb3Client(proxy_url=config[network]['proxy_url'])
    faucet = Faucet(faucet_url=config[network]['faucet_url'], web3_client=web3_client)
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

def k6_set_envs(network, env_filename, users_number=None, initial_balance=None, bank_account=None):
    with open(env_filename) as json_file:
        config = json.load(json_file)

    if os.environ.get('PROXY_URL') is None:
        os.environ["PROXY_URL"] = config[network]['proxy_url']

    if os.environ.get('SOLANA_URL') is None:
        os.environ["SOLANA_URL"] = config[network]['solana_url']

    if os.environ.get('FAUCET_URL') is None:
        os.environ["FAUCET_URL"] = config[network]['faucet_url']

    if os.environ.get('NETWORK_ID') is None:
        os.environ["NETWORK_ID"] = str(config[network]['network_ids']['neon'])
    
    # This parameter is mandatory for k6 scenario setup
    if os.environ.get('K6_USERS_NUMBER') is None:
        if users_number is not None:
            os.environ["K6_USERS_NUMBER"] = users_number
        else:
            print("Users number is not set. Please set K6_USERS_NUMBER env or pass it as an argument the to k6 run command.")
            exit(1)

    # This parameter is mandatory for k6 scenario setup
    if os.environ.get('K6_INITIAL_BALANCE') is None and initial_balance is not None:
        if initial_balance is not None:
            os.environ["K6_INITIAL_BALANCE"] = initial_balance
        else:
            print("Users initial balance is not set. Please set K6_INITIAL_BALANCE env or pass it as an argument to the k6 run command.")
            exit(1)
    
    if os.environ.get('K6_BANK_ACCOUNT') is None and bank_account is not None:
        os.environ["K6_BANK_ACCOUNT"] = bank_account
    
    return config