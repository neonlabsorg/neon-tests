import allure
import pytest

from utils.accounts import EthAccounts
from deepdiff import DeepDiff
from utils.web3client import NeonChainWeb3Client


@allure.feature("New indexers")
@allure.story("Verify data from different indexers")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestIndexersComparison:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.parametrize("blocks", [[89093, 91093]])
    def test_get_block_and_transactions_for_indexers(self, json_rpc_client, json_rpc_client_bestarch, blocks):
        for block in range(blocks[0], blocks[1]):
            response = json_rpc_client.send_rpc(
                method="eth_getBlockByNumber", 
                params=[hex(block), True],
            )
            response_bestarch = json_rpc_client_bestarch.send_rpc(
                method="eth_getBlockByNumber",
                params=[hex(block), True],
            )
 
            diff = DeepDiff(response, response_bestarch, exclude_paths="root['id']")

            if "values_changed" in diff or "type_changes" in diff:
                # if response_bestarch["result"] is not None:
                    with open(f'./indexers_diff/{block}.txt', 'w') as file:
                        file.write(f"Block: {block}\n")
                        file.write(f"eth_getBlockByNumber response from neon indexer: {response}\n")
                        file.write(f"eth_getBlockByNumber response from bestarch indexer: {response_bestarch}\n")
                        file.write("Differences:\n")
                        file.write(str(diff))
                        file.write("\n")
            
            if response["result"]["transactions"] is not None:
                for tx in response["result"]["transactions"]:
                    receipt_neon = json_rpc_client.send_rpc(
                        method="eth_getTransactionReceipt",
                        params=[tx["hash"]],
                    )
                    receipt_bestarch = json_rpc_client_bestarch.send_rpc(
                        method="eth_getTransactionReceipt",
                        params=[tx["hash"]],
                    )

                    diff_receipt = DeepDiff(receipt_neon, receipt_bestarch, exclude_paths="root['id']")

                    if "values_changed" in diff_receipt or "type_changes" in diff_receipt:
                        with open(f'./indexers_diff/{block}.txt', 'w') as file:
                            file.write(f"Block: {block}\n")
                            file.write(f"eth_getBlockByNumber response from neon indexer: {response}\n")
                            file.write(f"eth_getBlockByNumber response from bestarch indexer: {response_bestarch}\n")
                            file.write(f"Transaction: {tx['hash']}\n")
                            file.write(f"eth_getTransactionReceipt response from neon indexer: {receipt_neon}\n")
                            file.write(f"eth_getTransactionReceipt response from bestarch indexer: {receipt_bestarch}\n")
                            file.write("Differences:\n")
                            file.write(str(diff_receipt))
                            file.write("\n")