import { fundAccountFromFaucet, createAccount } from './utils/accountManager.js';
import { ethClient, sendNeon } from './utils/ethClient.js';
import { initialAccountBalance } from './utils/consts.js';
import { check } from 'k6';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import { Trend, Counter } from 'k6/metrics';

const sendNeonRequests = new Counter('send_neon_requests');
const sendNeonErrorCounter = new Counter('send_neon_errors');
const sendNeonRequestTime = new Trend('send_neon_request_time', true);

const testConfig = JSON.parse(open('../run_options/options.json'));
export const options = testConfig;

const transferAmount = randomIntBetween(1, 5);

export default function sendNeonTest() {
    const accountReceiver = createAccount();
    const accountSender = createAccount();
    const client = ethClient(accountSender.private_key);
    fundAccountFromFaucet(client, accountSender.address, initialAccountBalance);

    const startTime = new Date();

    try {
        let receipt = sendNeon(
            client,
            accountSender.address,
            accountReceiver.address,
            transferAmount,
            null,
            null,
            null
        );
        check(receipt, {
            'receipt status is 1': (r) => r.status === 1,
        });
    } catch (e) {
        console.log('Error sendNeon: ' + e);
        sendNeonErrorCounter.add(1);
    }
    sendNeonRequestTime.add(new Date() - startTime);
    sendNeonRequests.add(1);
}
