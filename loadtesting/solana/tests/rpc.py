import json
import random

import requests

from locust import HttpUser, task, tag


class SolanaRpc(HttpUser):
    def send_rpc(self, method, params):
        req_id = random.randint(0, 10000000000000)
        body = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        resp = self.client.post("/", json=body, headers={"Content-Type": "application/json"}, name=method)
        try:
            resp = resp.json()
        except Exception as e:
            assert False,  f"Bad response for {body} \n resp body:{resp.text} resp code:{resp.status_code}"
        return resp


    @task
    def task_get_block(self):
        block_number = random.randint(0, 277134978)
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
            assert resp["result"]["blockhash"], resp

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

    #@task
    def task_get_account_info(self):
        slot = self.send_rpc("getSlot", params=[])["result"]
        params = [
            slot,
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

        self.send_rpc("getAccountInfo", params)

    @task
    def task_blocks(self):
        slot = self.send_rpc("getSlot", params=[])["result"]
        random_block = random.randint(0, slot)
        params = [random_block, random_block+5]
        resp = self.send_rpc("getBlocks", params)
        assert "result" in resp, f"{resp} for {params}"

    def get_some_exist_block(self):
        slot = self.send_rpc("getSlot", params=[])["result"]
        params = [
            slot-100,
            {
                "encoding": "json",
                "maxSupportedTransactionVersion": 0,
                "transactionDetails": "full",
                "rewards": False,
                "commitment": "finalized"
            }
        ]
        resp = self.send_rpc("getBlock", params)
        while "error" in resp:
            slot = self.send_rpc("getSlot", params=[])["result"]
            params = [
                slot - 1000,
                {
                    "encoding": "json",
                    "maxSupportedTransactionVersion": 0,
                    "transactionDetails": "full",
                    "rewards": False,
                    "commitment": "finalized"
                }
            ]
            resp = self.send_rpc("getBlock", params)
        return resp["result"]

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
        self.send_rpc("getTransaction", params)
