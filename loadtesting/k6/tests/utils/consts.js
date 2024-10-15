import http from 'k6/http';

// Parse envs.json
const network = __ENV.K6_NETWORK;
const envConfig = JSON.parse(open("../../../../envs.json"));
if (network == undefined) {
    throw new Error("Network is not defined, please set K6_NETWORK env variable.");
}

let env;
switch (network) {
    case "local":
        env = envConfig.local;
        break;
    case "devnet":
        env = envConfig.devnet;
        break;
    default:
        env = envConfig.local;
}

// Set Chain Id
export const networkId = parseInt(env.network_ids.neon);

// Set Proxy URL
export const proxyUrl = env.proxy_url;

// Faucet URL
let faucetUri = env.faucet_url;
let faucetUrlObject;
if (!faucetUri.includes("request_neon")) {
    faucetUrlObject = http.url([faucetUri, 'request_neon']);
}
export const faucetUrl = faucetUrlObject.url;

// Accounts data
export const initialAccountBalance = parseInt(__ENV.K6_INITIAL_BALANCE);
export const usersNumber = parseInt(__ENV.K6_USERS_NUMBER);


// ERC20 contract data
export const erc20Address = __ENV.K6_ERC20_ADDRESS;
export const erc20Owner = __ENV.K6_ERC20_OWNER;
export const erc20OwnerKey = __ENV.K6_ERC20_OWNER_KEY;