import wallet from 'k6/x/ethereum/wallet';
import http from 'k6/http';
import { check } from 'k6';


const faucetUrl = 'http://3.13.67.238/request_neon';
const amount = 100;

export function fundAccountWithNeon(address, amount) {
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

export function createAccount() {
    var accountKey = wallet.generateKey();
    return {
        private_key: accountKey.private_key,
        address: accountKey.address,
    };
}

async function waiter({ func, args, value, retries = 10 }) {
    return smartWaiter({ func, args, check: (r) => r == value, retries: retries });
}

async function smartWaiter({ func, args, check, retries = 10 }) {
    let result;
    let counter = 0;
    while (!check(result) && counter < retries) {
        await new Promise(r => setTimeout(r, 200));
        if (args != undefined)
            result = await func(...args);
        else {
            result = await func();
        }
        counter++;
    }
    return result;
}