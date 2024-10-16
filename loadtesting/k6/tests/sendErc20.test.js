import { ethClient, sendErc20ViaTransferFunction } from './utils/ethClient.js';
import { createAccount, fundAccountFromFaucet } from './utils/accountManager.js';
import { initialAccountBalance, erc20Address, erc20Owner } from './utils/consts.js';
import { sendTokenOptions } from '../options/options.js';
import { Trend, Counter } from 'k6/metrics';
import { check } from 'k6';

const sendErc20Requests = new Counter('send_erc20_requests');
const sendErc20ErrorCounter = new Counter('send_erc20_errors');
const sendErc20RequestTime = new Trend('send_erc20_request_time', true);

export const options = sendTokenOptions;

const pathToContractData = '../contracts/ERC20/ERC20';
const abi = JSON.parse(open(pathToContractData + '.abi'));

export default function sendErc20Test() {
    // We need to have a unique signer account for each VU
    // We can't use the same account for all VUs because of nonce
    // Reason: k6 doesn't support shared state between VUs
    const signerAccount = createAccount();
    const client = ethClient(signerAccount.privateKey);
    fundAccountFromFaucet(client, signerAccount.address, initialAccountBalance / 10);

    const erc20 = client.newContract(erc20Address, JSON.stringify(abi), signerAccount.privateKey)

    const startTime = new Date();

    try {
        const receiver = createAccount();
        const receipt = sendErc20ViaTransferFunction(
            client,
            erc20,
            erc20Owner,
            JSON.stringify(abi),
            signerAccount.privateKey,
            receiver.address,
            1
        );
        check(receipt, {
            'receipt status is 1': (r) => r.status === 1,
        });
    } catch (e) {
        console.log('Error sendErc20: ' + e);
        sendErc20ErrorCounter.add(1);
    }
    sendErc20RequestTime.add(new Date() - startTime);
    sendErc20Requests.add(1);
}