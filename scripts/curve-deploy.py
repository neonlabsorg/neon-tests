"""Script to deploy Curve contracts from: https://github.com/curvefi/curve-factory/blob/simple-dev/data.json"""
import json
import os
import time
import random
import urllib

import requests


FAUCET_URL = os.environ.get("FAUCET_URL")
PROXY_URL = os.environ.get("PROXY_URL")
NETWORK_ID = os.environ.get("NETWORK_ID")

CURVE_DATA_URL = (
    "https://raw.githubusercontent.com/curvefi/curve-factory/simple-dev/data.json"
)

report = {"name": "Curve-factory", "actions": []}

print(f"Faucet url: {FAUCET_URL}")
print(f"Proxy url: {PROXY_URL}")

curve_resp = requests.get(CURVE_DATA_URL)

if curve_resp.status_code != 200:
    raise Exception(f"Can't download Curve factory: {curve_resp.text}")

curve_data = curve_resp.json()

for tr in curve_data.values():
    resp = requests.post(
        urllib.parse.urljoin(FAUCET_URL, "request_neon"),
        json={"amount": 2000, "wallet": tr["origin"]},
    )
    print(f"Faucet response: {resp.text} - {resp.status_code}")
    assert resp.status_code == 200, resp.text

gas_price = int(
    requests.post(
        PROXY_URL,
        json={
            "jsonrpc": "2.0",
            "method": "eth_gasPrice",
            "id": random.randint(1, 1000),
        },
    ).json()["result"],
    16,
)


for key in ["factory", "2", "3", "4"]:
    tr = curve_data[key]
    resp = requests.post(
        PROXY_URL,
        json={
            "jsonrpc": "2.0",
            "method": "eth_sendRawTransaction",
            "params": ["0x" + tr["raw_tx"]],
            "id": random.randint(1, 1000),
        },
    )
    print(f"Response on sendRawTransaction: {resp.text}")
    tr_id = resp.json()["result"]
    time.sleep(5)
    receipt = requests.post(
        PROXY_URL,
        json={
            "jsonrpc": "2.0",
            "method": "eth_getTransactionReceipt",
            "params": [tr_id],
            "id": random.randint(1, 1000),
        },
    ).json()

    for _ in range(5):
        receipt = requests.post(
            PROXY_URL,
            json={
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [tr_id],
                "id": random.randint(1, 1000),
            },
        ).json()

        if receipt["result"] is None:
            time.sleep(5)
            continue
        break
    else:
        print(f"Can't get receipt for {tr_id} ({key})")
        continue

    report["actions"].append(
        {
            "name": f"Deploy {key}",
            "usedGas": int(receipt["result"]["gasUsed"], 16),
            "gasPrice": gas_price,
            "tx": tr_id,
        }
    )

    assert (
        receipt["result"]["status"] == "0x1"
    ), f"Transaction for factory: {key} failed: {receipt}"

    with open("curve-factory-report.json", "w") as f:
        json.dump(report, f)