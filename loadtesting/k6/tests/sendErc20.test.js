import { ethClient } from './utils/ethClient.js';
import { fundAccountFromFaucet } from './utils/accountManager.js';
import { initialAccountBalance, erc20Address, erc20Owner, erc20OwnerKey } from './utils/consts.js';
import { sendTokenOptions } from '../options/options.js';
import { Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';
import exec from 'k6/execution';
import { check } from 'k6';

const sendErc20Requests = new Counter('send_erc20_requests');
const sendErc20ErrorCounter = new Counter('send_erc20_errors');
const sendErc20RequestTime = new Trend('send_erc20_request_time', true);

export const options = sendTokenOptions;

const client = ethClient(erc20OwnerKey);
const pathToContractData = '../contracts/ERC20/ERC20'; 
const abi = JSON.parse(open(pathToContractData + '.abi'));
const bytecode = open(pathToContractData + '.bin');

const usersArray = new SharedArray('Users accounts', function () {
    const accounts = JSON.parse(open("../data/accounts.json"));
    let data = [];
    for (let i = 0; i < Object.keys(accounts).length; i++) {
        data[i] = accounts[i];
    }
    return data;
});

export function setup() {
    // const receipt = client.deployContract(JSON.stringify(abi), bytecode, "TestToken", "TT", 500000000000);
    // console.log('Contract deployed: ' + JSON.stringify(receipt));

    const erc20 = client.newContract(erc20Address, JSON.stringify(abi), erc20OwnerKey);
    const signer = erc20.getAddress();
    fundAccountFromFaucet(client, signer, initialAccountBalance*10);
}

export default function sendErc20Test(data) {
    const vuID = exec.vu.idInTest;
    const index = vuID % usersArray.length;
    const receiverAddress = usersArray[index].sender_address;
    
    const erc20 = client.newContract(erc20Address, JSON.stringify(abi), erc20OwnerKey);
    
    const signer = erc20.getAddress();
    const txOpts = {
        "value": 1,
        "gas_price": 0,
        "gas_limit": 0,
        "nonce": client.getNonce(signer),
    };  
    console.log('TxOpts: ' + JSON.stringify(txOpts));

    const startTime = new Date();
    let receipt;
    try {
        const hash = erc20.txn("transfer", txOpts, receiverAddress, 1);
        receipt = client.waitForTransactionReceipt(txh);
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