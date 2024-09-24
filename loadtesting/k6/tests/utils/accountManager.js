import wallet from 'k6/x/ethereum/wallet';
import http from 'k6/http';
import { check } from 'k6';
import { faucetUrl } from './consts.js';
import { sendTokens } from './ethClient.js';
import { waiter } from './helpers.js';

export function createAccount() {
    var accountKey = wallet.generateKey();
    return {
        private_key: accountKey.private_key,
        address: accountKey.address,
    };
}

export function fundAccountFromFaucet(client, address, amount) {
    fundAccount(client, requestFaucet, [address, amount], address, amount);
}

export function fundAccountFromBank(client, bankAccount, address, amount) {
    fundAccount(client, sendTokens, [client, bankAccount, address, amount, null, null, null], address, amount);
}

async function fundAccount(client, fundFunc, fundFuncArgs, address, amount) {
    let initialBalance = parseInt(client.getBalance(address));
    if (initialBalance != 0) {
        initialBalance = initialBalance / 10 ** 18;
    }
    await fundFunc(...fundFuncArgs);
    waiter({ func: client.getBalance, args: [address], value: (initialBalance + amount) * 10 ** 18, retries: 60 });
}

function requestFaucet(address, amount) {
    const payload = JSON.stringify({
        amount: amount,
        wallet: address,
    });

    const params = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const response = http.post(faucetUrl, payload, params);
    check(response, {
        'status is 200': (r) => r.status === 200,
    });
}
