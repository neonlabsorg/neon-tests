import { ethClient, deployContract, getContract } from './utils/ethClient.js';
import { randomItem } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import { createAccount, fundAccountFromFaucet } from './utils/accountManager.js';
import { initialAccountBalance, erc20Address } from './utils/consts.js';
import { sendTokenOptions } from '../options/options.js';
import { Trend, Counter } from 'k6/metrics';
import exec from 'k6/execution';
// import { check } from 'k6';

const sendNeonRequests = new Counter('send_neon_requests');
const sendNeonErrorCounter = new Counter('send_neon_errors');
const sendNeonRequestTime = new Trend('send_neon_request_time', true);

export const options = sendTokenOptions;

const account = createAccount();
const client = ethClient(account.privateKey);
const pathToContractData = '../contracts/ERC20';
const abi = open(pathToContractData + '.abi');
const bytecode = open(pathToContractData + '.bin');
let contract;

export function setup() {
    fundAccountFromFaucet(client, account.address, initialAccountBalance);
    // const contract = deployContract(client, abi, bytecode, ["TestToken", "TT", 10000000000]);
    contract = client.newContract(erc20Address, abi);
    // console.log('Contract: ' + JSON.stringify(contract));
    // console.log('Contract deployed at address: ' + contract.address);
}

const transferAmountRange = [0.01, 0.02, 0.03, 0.04, 0.05];

export default function sendErc20Test() {
    const vuID = exec.vu.idInTest;
    const index = vuID % usersArray.length;

    console.log('Contract: ' + JSON.stringify(contract));
    txOpts = {
        "value": randomItem(transferAmountRange),
        "gas_price": client.gasPrice(),
        "gas_limit": gas,
        "nonce": client.getNonce(from),
    };

    contract.txn("transfer", {
       
    });

    const accountSenderAddress = usersArray[index].sender_address;
    const accountReceiverAddress = usersArray[index].receiver_address;
}