import allure
import pytest
import yaml

from integration.tests.basic.helpers.basic import BaseMixin

@allure.story("Graph")
class TestGraph(BaseMixin):
    @pytest.mark.only_devnet
    def test_deploy_gravity_contract_network(self):
        """Deploy GravatarRegistry contract, then get address and block number"""
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "./GravatarRegistry.sol", "0.8.0", account=self.recipient_account
        )

        address = contract.address
        block_number = contract_deploy_tx['blockNumber']

        with open('graph/subgraph.yaml') as f:
            data = yaml.safe_load(f)

        data['dataSources'][0]['source']['address'] = address
        data['dataSources'][0]['source']['startBlock'] = block_number

        with open('graph/subgraph.yaml', 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False)

        breakpoint() # pause test to deploy subgraph then type continue to finish test
        
        instruction_tx =contract.functions.createGravatar('Test_name_0','Test_url_0').build_transaction(
            {
                "from": self.recipient_account.address,
                "nonce": self.web3_client.eth.get_transaction_count(
                    self.recipient_account.address
                ),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        instruction_receipt = self.web3_client.send_transaction(
            self.recipient_account, instruction_tx
        )
        assert instruction_receipt["status"] == 1

        instruction_tx =contract.functions.createGravatar('Test_name_1','Test_url_1').build_transaction(
            {
                "from": self.recipient_account.address,
                "nonce": self.web3_client.eth.get_transaction_count(
                    self.recipient_account.address
                ),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        instruction_receipt = self.web3_client.send_transaction(
            self.recipient_account, instruction_tx
        )
        assert instruction_receipt["status"] == 1

        breakpoint()
        instruction_tx =contract.functions.createGravatar('Test_name_2','Test_url_2').build_transaction(
            {
                "from": self.sender_account.address,
                "nonce": self.web3_client.eth.get_transaction_count(
                    self.sender_account.address
                ),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        instruction_receipt = self.web3_client.send_transaction(
            self.sender_account, instruction_tx
        )
        assert instruction_receipt["status"] == 1
        
        instruction_tx =contract.functions.updateGravatarName('Test_name_000').build_transaction(
            {
                "from": self.recipient_account.address,
                "nonce": self.web3_client.eth.get_transaction_count(
                    self.recipient_account.address
                ),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        instruction_receipt = self.web3_client.send_transaction(
            self.recipient_account, instruction_tx
        )
        assert instruction_receipt["status"] == 1
