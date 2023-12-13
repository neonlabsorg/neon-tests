import eth from 'k6/x/ethereum';
import wallet from 'k6/x/ethereum/wallet';
import { fundAccountWithNeon, createAccount } from './utils/test_accounts.js';
import { Trend, Counter } from 'k6/metrics'

export const options = {
    scenarios: {
        contacts: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '90s', target: 100 },
                { duration: '600s', target: 100 },
            ],
            gracefulRampDown: '60s',
        },
    },
};

const sendNeonRequests = new Counter('send_neon_requests');
const nonceRequests = new Counter('nonce_requests');
const blockNumberRequests = new Counter('block_number_requests');
const gasPriceRequests = new Counter('gas_price_requests');

const sendNeonErrorCounter = new Counter('send_neon_errors');
const blockNumberErrorCounter = new Counter('block_number_errors');
const nonceErrorCounter = new Counter('nonce_errors');
const gasPriceErrorCounter = new Counter('gas_price_errors');

const sendNeonRequestTime = new Trend('send_neon_request_time', true);
const blockNumberRequestTime = new Trend('block_number_request_time', true);
const nonceRequestTime = new Trend('nonce_request_time', true);
const gasPriceRequestTime = new Trend('gas_price_request_time', true);

export default function () {
    let account = createAccount();
    const accountSender = wallet.newWalletKeyFromPrivateKey(account.private_key);

    const client = new eth.Client({
        privateKey: accountSender.private_key,
        url: 'https://devnet.neonevm.org/',
    });

    fundAccountWithNeon(accountSender.address, 20);

    let nonce;
    try {
        const startTime = new Date();
        nonce = client.getNonce(accountSender.address);
        const finishTime = new Date();
        nonceRequests.add(1);
        nonceRequestTime.add(finishTime - startTime);
    } catch (e) {
        console.log('Error: ' + e);
        nonceErrorCounter.add(1);
    }

    let gasPrice;
    try {
        const startTime = new Date();
        gasPrice = client.gasPrice();
        const finishTime = new Date();
        gasPriceRequests.add(1);
        gasPriceRequestTime.add(finishTime - startTime);
    } catch (e) {
        console.log('Error: ' + e);
        gasPriceErrorCounter.add(1);
    }

    const accountReceiver = createAccount();
    const sendingNeonStartTime = new Date();
    while (new Date() - sendingNeonStartTime < 1000 * 60 * 12) {

        try {
            const startTime = new Date();
            client.blockNumber();
            const finishTime = new Date();
            blockNumberRequests.add(1);
            blockNumberRequestTime.add(finishTime - startTime);
        } catch (e) {
            console.log('Error: ' + e);
            blockNumberErrorCounter.add(1);
        }

        try {
            const startTime = new Date();
            client.getNonce(accountSender.address);
            const finishTime = new Date();
            nonceRequests.add(1);
            nonceRequestTime.add(finishTime - startTime);
        } catch (e) {
            console.log('Error: ' + e);
            nonceErrorCounter.add(1);
        }

        try {
            const startTime = new Date();
            client.gasPrice();
            const finishTime = new Date();
            gasPriceRequests.add(1);
            gasPriceRequestTime.add(finishTime - startTime);
        } catch (e) {
            console.log('Error: ' + e);
            gasPriceErrorCounter.add(1);
        }

        const startTime = new Date();

        try {
            sendNeon(client, accountSender.address, accountReceiver.address, 0.01, 0, gasPrice, nonce);
        } catch (e) {
            console.log('Error: ' + e);
            sendNeonErrorCounter.add(1);
        }

        const finishTime = new Date();
        sendNeonRequests.add(1);
        sendNeonRequestTime.add(finishTime - startTime);
        nonce++;
    }
}


function sendNeon(client, from, to, amount, gas, gasPrice, nonce) {
    const value = amount * 10e18;
    sendTokens(client, from, to, value, gas, gasPrice, nonce)
}

function sendTokens(client, from, to, value, gas, gasPrice, nonce) {
    if (nonce == null) {
        nonce = client.getNonce(from);
        nonceRequests.add(1);
    }

    if (gasPrice == null) {
        gasPrice = client.gasPrice();
        gasPriceRequests.add(1);
    }

    let transaction = {
        "from": from,
        "to": to,
        "value": value,
        "gas_price": gasPrice,
        "gas": gas,
        "nonce": nonce,
        "chain_id": 245022926,
    };

    if (transaction["gas"] == 0) {
        transaction["gas"] = client.estimateGas(transaction);
    }

    const txh = client.sendRawTransaction(transaction);
    const receipt = client.waitForTransactionReceipt(txh);

    return receipt;
}