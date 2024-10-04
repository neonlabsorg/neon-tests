import { randomItem } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import { ethClient, sendNeon } from './utils/ethClient.js';
import { sendNeonOptions } from '../options/options.js';
import { Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';
import exec from 'k6/execution';
import { check } from 'k6';

const sendNeonRequests = new Counter('send_neon_requests');
const sendNeonErrorCounter = new Counter('send_neon_errors');
const sendNeonRequestTime = new Trend('send_neon_request_time', true);

export const options = sendNeonOptions;

const usersArray = new SharedArray('Users accounts', function () {
    const accounts = JSON.parse(open("../data/accounts.json"));
    let data = [];
    for (let i = 0; i < Object.keys(accounts).length; i++) {
        data[i] = accounts[i];
    }
    return data;
});

const transferAmountRange = [0.01, 0.02, 0.03, 0.04, 0.05];

export default function sendNeonTest() {
    const vuID = exec.vu.idInTest
    const index = vuID % usersArray.length;

    const accountSenderAddress = usersArray[index].sender_address;
    const accountSenderPrivateKey = usersArray[index].sender_key;
    const accountReceiverAddress = usersArray[index].receiver_address;

    const client = ethClient(accountSenderPrivateKey);

    const startTime = new Date();

    try {
        let receipt = sendNeon(
            client,
            accountSenderAddress,
            accountReceiverAddress,
            randomItem(transferAmountRange),
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
