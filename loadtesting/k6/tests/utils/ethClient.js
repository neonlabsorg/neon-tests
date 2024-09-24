import eth from 'k6/x/ethereum';
import { proxyUrl, networkId } from './consts.js';


export function ethClient(privateKey) {
    const client = new eth.Client({
        url: proxyUrl,
        chainID: networkId,
        privateKey: privateKey,
    });
    return client;
}

export function sendNeon(client, from, to, amount, gas, gasPrice, nonce) {
    const value = amount;
    return sendTokens(client, from, to, value, gas, gasPrice, nonce)
}

export function sendTokens(client, from, to, value, gas, gasPrice, nonce) {
    let nonceRequests = 0;
    let gasPriceRequests = 0;
    if (nonce == null) {
        nonce = client.getNonce(from);
        nonceRequests++;
    }

    if (gasPrice == null) {
        gasPrice = client.gasPrice();
        gasPriceRequests++;
    }

    let transaction = {
        "from": from,
        "to": to,
        "value": value,
        "gas_price": gasPrice,
        "gas": gas,
        "nonce": nonce,
        "chain_id": client.chainID,
    };

    if (gas == null) {
        transaction["gas"] = client.estimateGas({
            "from": from,
            "to": to,
            "value": value,
            "input": [],
            "gas_price": gasPrice,
            "gas": 0,
        });
    }

    const txh = client.sendRawTransaction(transaction);
    const receipt = client.waitForTransactionReceipt(txh);

    return receipt, nonceRequests, gasPriceRequests;
}

