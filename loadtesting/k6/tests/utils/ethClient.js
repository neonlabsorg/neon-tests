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
    return sendTokens(client, from, to, amount, null, gas, gasPrice, nonce)
}

export function sendErc20ViaTransferFunction(client, erc20, owner, abi, signerAddress, receiverAddress, amount) {
    const input = erc20.fillInput(abi, "transfer");
    const nonce = client.getNonce(signerAddress);
    return sendTokens(client, owner, receiverAddress, amount, input, null, null, nonce)
}

export function sendTokens(client, from, to, value, input, gas, gasPrice, nonce) {
    if (nonce == null) {
        nonce = client.getNonce(from);
    }

    if (gasPrice == null) {
        gasPrice = client.gasPrice();
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

    if (input != null) {
        transaction["input"] = input;
    }

    if (gas == null) {
        transaction["gas"] = client.estimateGas(transaction);
    }

    const txh = client.sendRawTransaction(transaction);
    const receipt = client.waitForTransactionReceipt(txh);

    return receipt;
}
