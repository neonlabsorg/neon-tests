import math
import allure
import pytest
import requests

from integration.tests.base import BaseTests


SOL_USD_ID = "0x78f57ae1195e8c497a8be054ad52adf4c8976f8436732309e22af7067724ad96"
CHAINLINK_URI = "https://min-api.cryptocompare.com/"


@pytest.fixture()
def chainlink_contract(web3_client, prepare_account):
    contract, _ = web3_client.deploy_and_get_contract(
        contract="./chainlink/ChainlinkOracle",
        version="0.8.19",
        account=prepare_account,
        constructor_args=[SOL_USD_ID],
        contract_name="ChainlinkOracle",
    )
    return contract


@allure.feature("Oracles")
@allure.story("Chainlink")
class TestChainlink(BaseTests):
    @pytest.mark.only_devnet
    def test_deploy_contract_chainlink_network(self, chainlink_contract):
        """Deploy chainlink contract, then get the latest price for SOL/USD"""

        version = chainlink_contract.functions.version().call()
        description = chainlink_contract.functions.description().call()
        decimals = chainlink_contract.functions.decimals().call()
        latest_round_data = chainlink_contract.functions.latestRoundData().call()

        assert version == 2
        assert description == "SOL / USD"
        assert decimals == 8

        latest_price = latest_price_feeds("SOL", "USD")
        assert math.isclose(
            abs(latest_price - latest_round_data[1] * 1e-8), 0.0, rel_tol=1
        )

    @pytest.mark.only_devnet
    def test_get_chainlink_info_from_contract(self, chainlink_contract):
        """Call latest price for SOL/USD from another contract"""
        contract, _ = self.web3_client.deploy_and_get_contract(
            contract="./chainlink/GetLatestData", version="0.8.15", account=self.acc
        )

        address = chainlink_contract.address
        version = contract.functions.getVersion(address).call()
        description = contract.functions.getDescription(address).call()
        decimals = contract.functions.getDecimals(address).call()
        latest_data = contract.functions.getLatestData(address).call()

        assert version == 2
        assert description == "SOL / USD"
        assert decimals == 8

        latest_price = latest_price_feeds("SOL", "USD")
        assert math.isclose(abs(latest_price - latest_data[1] * 1e-8), 0.0, rel_tol=1)

    def test_round_data_method(self, chainlink_contract):
        round_data = chainlink_contract.functions.getRoundData(0).call()
        assert len(round_data) == 5
        print(round_data)


def latest_price_feeds(sym_one, sym_two):
    response = requests.get(
        CHAINLINK_URI + f"data/pricemultifull?fsyms={sym_one}&tsyms={sym_two}"
    )
    return response.json()["RAW"][f"{sym_one}"][f"{sym_two}"]["PRICE"]
