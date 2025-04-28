import allure
import pytest
import os

from integration.tests.indexers_comparison.constants import LOGS_PATH, START_BLOCK, FINISH_BLOCK
from deepdiff import DeepDiff


@allure.feature("New indexers")
@allure.story("Verify data from different indexers")
class TestCompareRpcEthResponses:
    @pytest.fixture(autouse=True)
    def prepare_log_folder(self):
        if os.path.exists(LOGS_PATH):
            for file in os.listdir(LOGS_PATH):
                os.remove(f"{LOGS_PATH}/{file}")
        else:
            os.makedirs(LOGS_PATH)

    @pytest.mark.parametrize("blocks", [[START_BLOCK, FINISH_BLOCK]])
    def test_get_block_and_transactions_for_indexers(self, endpoints, blocks):
        start_block = int(blocks[0])
        finish_block = int(blocks[1])
        for block in range(start_block, finish_block):
            print(block)

            response = self.compare_rpc_method_responses(
                method_name="eth_getBlockByNumber",
                params=[hex(block), True],
                endpoints=endpoints,
                file_name=block,
            )

            hash_neon = response["result"]["hash"]

            self.compare_rpc_method_responses(
                method_name="eth_getBlockByHash",
                params=[hash_neon, True],
                endpoints=endpoints,
                file_name=block,
            )

            if response["result"]["transactions"] is not None:
                for tx in response["result"]["transactions"]:
                    receipt = self.compare_rpc_method_responses(
                        method_name="eth_getTransactionReceipt",
                        params=[tx["hash"]],
                        endpoints=endpoints,
                        file_name=block,
                    )

                    self.compare_rpc_method_responses(
                        method_name="eth_getTransactionByHash",
                        params=[tx["hash"]],
                        endpoints=endpoints,
                        file_name=block,
                    )
                    if len(receipt["result"]["logs"]) > 0:
                        self.compare_rpc_method_responses(
                            method_name="eth_getLogs",
                            params=[
                                {
                                    "topics": [receipt["result"]["logs"][0]["topics"][0]],
                                    "fromBlock": hex(block),
                                    "toBlock": hex(block),
                                }
                            ],
                            endpoints=endpoints,
                            file_name=block,
                        )
        assert os.listdir(LOGS_PATH) == [], f"Check logs in {LOGS_PATH}"

    @staticmethod
    def compare_rpc_method_responses(method_name, params, endpoints, file_name):
        responses = []
        for endpoint in endpoints:
            rpc_client = endpoint["rpc_client"]
            responses.append(
                rpc_client.send_rpc(
                    method=method_name,
                    params=params,
                )
            )
        diff = DeepDiff(responses[0], responses[1], exclude_paths="root['id']")

        if "values_changed" in diff or "type_changes" in diff:
            filename = f"{LOGS_PATH}/{file_name}.txt"
            mode = "a" if os.path.exists(filename) else "w"
            with open(filename, mode) as file:
                if mode == "w":
                    file.write(f"Method: {method_name}\n")
                else:
                    file.write(f"\n\n\n\nMethod: {method_name}\n")
                file.write(f"Params: {params}\n")
                for i, response in enumerate(responses):
                    file.write(f"\nResponse from {endpoints[i]['name']} indexer: {response}\n")
                file.write("\nDifferences:\n")
                file.write(str(diff))

        return responses[0]
