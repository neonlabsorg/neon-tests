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

export function sendNeon(client, from, to, amount) {
    return sendTokens(client, from, to, amount, null);
}

export function sendErc20ViaTransferFunction(client, erc20, from, to, abi, receiverAddress, amount) {
    let input = erc20.fillInput(abi, "transfer", receiverAddress, amount);
    return sendTokens(client, from, to, 0, input);
}

export function sendTokens(client, from, to, value, input) {
    let transaction = {
        "from": from,
        "to": to,
        "value": value
    };

    if (input != null) {
        transaction["input"] = input;
    }

    const txh = client.sendRawTransaction(transaction);
    return client.waitForTransactionReceipt(txh, 120);
}
