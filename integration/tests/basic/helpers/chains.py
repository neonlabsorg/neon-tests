def make_nonce_the_biggest_for_chain(account, client, rest_clients):
    # to avoid error "EVM Error. Attempt to deploy to existing account 0x..."
    clients = [c for c in rest_clients if c]
    new_account = client.create_account()
    while client.get_nonce(account.address) < max([c.get_nonce(account.address) for c in clients]):
        client.send_tokens(account, new_account.address, 10)
