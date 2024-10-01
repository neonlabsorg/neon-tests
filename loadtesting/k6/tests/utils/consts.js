import http from 'k6/http';

// Network params
let faucetUri = __ENV.FAUCET_URL;
let faucetUrlObject;
if (!faucetUri.includes("request_neon")) {
    faucetUrlObject = http.url([faucetUri, 'request_neon']);
}
export const faucetUrl = faucetUrlObject;
export const proxyUrl = __ENV.PROXY_URL;
export const networkId = parseInt(__ENV.NETWORK_ID);

// Accounts data
export const initialAccountBalance = parseInt(__ENV.K6_INITIAL_BALANCE);
export const usersNumber = parseInt(__ENV.K6_USERS_NUMBER);
