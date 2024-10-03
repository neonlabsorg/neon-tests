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
let proxyUrlParam = __ENV.PROXY_URL;
if (proxyUrlParam == undefined) {
    proxyUrlParam = env.proxy_url;
}
export const proxyUrl = proxyUrlParam;

// Accounts data
export const initialAccountBalance = parseInt(__ENV.K6_INITIAL_BALANCE);
export const usersNumber = parseInt(__ENV.K6_USERS_NUMBER);
