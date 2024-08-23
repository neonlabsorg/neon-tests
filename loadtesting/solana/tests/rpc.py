import json
import random

import requests

from locust import HttpUser, task

START_BLOCK = 195350522
MAX_BLOCK = 285326658

class SolanaRpc(HttpUser):
    def send_rpc(self, method, params):
        req_id = random.randint(0, 10000000000000)
        body = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        resp = self.client.post("/", json=body, headers={"Content-Type": "application/json"}, name=method)
        try:
            resp = resp.json()
        except requests.exceptions.JSONDecodeError as e:
            assert False,  f"Bad response for {body} \n resp body:{resp.text} resp code:{resp.status_code}"
        return resp

    @task
    def task_get_block(self):
        last_slot = self.send_rpc("getSlot", params=[])["result"]

        block_number = random.randint(195350522, last_slot)
        params = [
            block_number,
            {
                "encoding": "json",
                "maxSupportedTransactionVersion": 0,
                "transactionDetails": "full",
                "rewards": False
            }
        ]
        resp = self.send_rpc("getBlock", params)
        if "result" not in resp:
            assert resp["error"]["code"] ==-32009, resp
            print(f"Block {block_number} missed")
        else:
            assert resp["result"], f"result is empty for {params}, resp: {resp}"
            if "blockhash" not in resp["result"]:
                assert False, resp

    def is_exist_in_mainnet(self, params):
        body = {"jsonrpc": "2.0", "id": 1, "method": "getBlock", "params": params}
        resp = requests.post(url="https://api.mainnet-beta.solana.com", json=body).json()
        if "error" in resp:
            return False
        else:
            return True

    @task
    def task_get_slot(self):
        self.send_rpc("getSlot", params=[])

    @task
    def task_get_account_info(self):
        block = self.get_some_exist_block()
        params = [
            block,
            {
                "encoding": "json",
                "maxSupportedTransactionVersion": 0,
                "transactionDetails": "full",
                "rewards": False
            }
        ]

        account = self.send_rpc("getBlock", params)["result"]["transactions"][0]["transaction"]["message"]["accountKeys"][0]

        params = [
                account,
                {
                    "encoding": "base58"
                }
            ]

        resp = self.send_rpc("getAccountInfo", params)
        assert "result" in resp, f"{resp} for {params}"

    @task
    def task_get_transaction(self):
        block = self.get_some_exist_block()
        assert len(block["transactions"]) > 0, f"block {block['blockhash']} doesn't have trx"
        signature = block["transactions"][0]["transaction"]["signatures"][0]

        params = [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0
                }
            ]
        resp = self.send_rpc("getTransaction", params)
        assert "result" in resp, f"{resp} for {params} for getTransaction"

    @task
    def task_blocks(self):
        random_block = random.randint(START_BLOCK, MAX_BLOCK)
        params = [random_block, random_block+10]
        resp = self.send_rpc("getBlocks", params)
        assert "result" in resp, f"{resp} for {params}"

    def get_some_exist_block(self):
        random_block = random.randint(START_BLOCK, MAX_BLOCK)
        params = [
            random_block,
            {
                "encoding": "json",
                "maxSupportedTransactionVersion": 0,
                "transactionDetails": "full",
                "rewards": False,
                "commitment": "finalized"
            }
        ]
        resp = self.send_rpc("getBlock", params)
        if "error" in resp or resp["result"]:
            print(f"!Block {random_block} missed")
            self.get_some_exist_block()
        else:
            return resp["result"]

