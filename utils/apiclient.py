import time
import typing as tp
import random

from requests import Session


class JsonRPCSession(Session):
    def __init__(self, url):
        super(JsonRPCSession, self).__init__()
        self.url = url

    def send_rpc(
        self,
        method: str,
        params: tp.Optional[tp.Any] = None,
        req_type: tp.Optional[str] = None,
    ) -> tp.Dict:
        req_id = random.randint(0, 100)
        body = {"jsonrpc": "2.0", "method": method, "id": req_id}

        if req_type is not None:
            body["req_type"] = req_type

        if params:
            if not isinstance(params, (list, tuple)):
                params = [params]
            body["params"] = params

        resp = self.post(self.url, json=body, timeout=60)
        response_body = resp.json()
        if "result" not in response_body and "error" not in response_body:
            raise AssertionError("Request must contains 'result' or 'error' field")

        if "error" in response_body:
            assert "result" not in response_body, "Response can't contains error and result"
        if "error" not in response_body:
            assert response_body["id"] == req_id

        return response_body

    def get_contract_code(self, contract_address: str) -> str:
        response = self.send_rpc("eth_getCode", [contract_address, "latest"])
        return response["result"]

    def get_neon_trx_receipt(self, trx_hash: str) -> tp.Dict:
        return self.send_rpc("neon_getTransactionReceipt", params=[trx_hash.hex()])
    
    def get_solana_trx_by_neon(self, trx_hash: str) -> tp.Dict:
        return self.send_rpc("neon_getSolanaTransactionByNeonTransaction", params=[trx_hash.hex()])


def wait_finalized_block(rpc_client: JsonRPCSession, block_num: int):
    fin_block_num = block_num - 32
    while block_num > fin_block_num:
        time.sleep(1)
        response = rpc_client.send_rpc("neon_finalizedBlockNumber", [])
        fin_block_num = int(response["result"], 16)
