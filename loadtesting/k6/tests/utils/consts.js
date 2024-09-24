import http from 'k6/http';

// params from envs
let faucetUri = __ENV.FAUCET_URL;
let faucetUrlObject;
if (!faucetUri.includes("request_neon")) {
    faucetUrlObject = http.url([faucetUri, 'request_neon']);
}
export const faucetUrl = faucetUrlObject;
export const proxyUrl = __ENV.PROXY_URL;
