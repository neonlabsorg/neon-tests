import allure
import pytest
import yaml

from integration.tests.base import BaseTests


@allure.story("Graph")
class TestGraph(BaseTests):
    @pytest.mark.only_devnet
    def test_deploy_gravity_contract_network(self):
        """Deploy GravatarRegistry contract, then get address and block number"""
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "./GravatarRegistry.sol", "0.8.0", account=self.acc
        )

        address = contract.address
        block_number = contract_deploy_tx['blockNumber']

        with open('graph/subgraph.yaml') as f:
            data = yaml.safe_load(f)

        data['dataSources'][0]['source']['address'] = address
        data['dataSources'][0]['source']['startBlock'] = block_number

        with open('graph/subgraph.yaml', 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False)