"""Script checks debug_traceTransaction method of neon-tracer service.
We iterate over block range and check if the response of debug_traceTransaction is successful. 
If not we save the response and transaction hash to the file.
Before start:
export TRACER_URL=<tracer_url>
export PROXY_URL=<proxy_url>
mkdir ./trace_diff
"""
import os
import time

from utils.apiclient import JsonRPCSession
from utils.tracer_client import TracerClient

TRACER_URL = os.environ.get("TRACER_URL")
PROXY_URL = os.environ.get("PROXY_URL")
BLOCK_RANGE = [277994008, 278463224]
json_rpc_client = JsonRPCSession(PROXY_URL)
tracer_client = TracerClient(TRACER_URL)

print(f"Tracer url: {TRACER_URL}")
print(f"Proxy url: {PROXY_URL}")

def check_trace_transaction():
    for block in range(BLOCK_RANGE[0], BLOCK_RANGE[1]):
        print("Block: ", block)
        response = json_rpc_client.send_rpc(method="eth_getBlockByNumber", params=[hex(block), True])
        if response["result"] is not None and response["result"]["transactions"] != []:
            for tx in response["result"]["transactions"]:
                response_trace = tracer_client.send_rpc(method="debug_traceTransaction", 
                                                        params=[tx["hash"]])
                if "error" in response_trace:
                    with open(f'./trace_diff/{block}.txt', 'w+') as file:
                        file.write(f"Block: {block}\n\n")
                        file.write(f"eth_getBlockByNumber response: {response}\n\n")
                        file.write(f"debug_traceTransaction response: {response_trace}\n\n")

start_time= time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
with open(f'./trace_diff/time.txt', 'w+') as file:
    file.write(f"Start time: {start_time}\n\n")
check_trace_transaction()
finish_time= time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
with open(f'./trace_diff/time.txt', 'a') as file:
    file.write(f"Finish time: {finish_time}\n\n")
