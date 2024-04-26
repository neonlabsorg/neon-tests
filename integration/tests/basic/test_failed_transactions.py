import pytest
import allure

from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts


@allure.story("Expected proxy errors during contract calls")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestExpectedErrors:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.proxy_version("v1.12.0")
    def test_bump_allocator_out_of_memory_expected_error(self):
        sender_account = self.accounts[0]
        contract, _ = self.web3_client.deploy_and_get_contract(
            "common/ExpectedErrorsChecker", "0.8.12", sender_account, contract_name="A"
        )

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.method1().build_transaction(tx)
        try:
            resp = self.web3_client.send_transaction(sender_account, instruction_tx)
            assert resp["status"] == 0
        except ValueError as exc:
            assert "Error: memory allocation failed, out of memory." in exc.args[0]["message"]
