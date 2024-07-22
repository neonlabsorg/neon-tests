from utils.web3client import NeonChainWeb3Client


web3_client = NeonChainWeb3Client("https://neon-proxy-mainnet.solana.p2p.org")

base_private_key = int("0xce3b1af8967d05e005e21d183cceeeb9114b76079f937c983d1a1c639e3fed7f", 16)

for acc_priv_key in range(base_private_key, base_private_key + 4000):
    account = web3_client.eth.account.from_key(hex(acc_priv_key))
    balance = web3_client.get_balance(account.address)
    if balance > 12000000000000000:
        amount = web3_client._web3.from_wei(balance - 12000000000000000, "ether")
        print(f"Sending {amount} from {account.address}")
        try:
            web3_client.send_neon(account, "0xaB0f34f3E6b7C507388C88B0DD1c38aCF4CCa50B", amount)
        except Exception as e:
            print(e)
    else:
        print(f"Balance too low for {account.address}")
