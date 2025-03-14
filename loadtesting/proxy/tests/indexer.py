import logging
import random


from loadtesting.proxy.common.events import execute_before

from locust import User, tag, task
from loadtesting.proxy.common.base import NeonProxyTasksSet

LOG = logging.getLogger(__name__)


@tag("send_neon")
class NeonIterativeTasksSet(NeonProxyTasksSet):
    """Implements Neons transfer base pipeline tasks"""

    contract = None

    def on_start(self) -> None:
        super().on_start()
        self.prepare_account()
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "common/Counter.sol", "0.8.10", account=self.account
        )
        self.contract = contract

    @task
    def task_run_iterative_tx(self):
        """Transferring funds to a random account"""
        tx = self.web3_client.make_raw_tx(self.account)
        instruction_tx = self.contract.functions.moreInstruction(0, 3000).build_transaction(tx)
        trx = self.web3_client.send_transaction(self.account, instruction_tx)
        assert trx.get("status") == 1, trx
        LOG.info("Transaction sent: %s", trx)


@tag("send_neon")
class NeonTasksSet(NeonProxyTasksSet):
    """Implements Neons transfer base pipeline tasks"""

    nonce: int
    recipient: str

    def on_start(self) -> None:
        super().on_start()
        super().setup()
        self.log = logging.getLogger("neon-consumer[%s]" % self.account.address[-8:])
        self.nonce = self.web3_client.get_nonce(self.account)
        self.recipient = self.get_account()

    def get_balances(self):
        sender_balance = self.web3_client.get_balance(self.account.address)
        recipient_balance = self.web3_client.get_balance(self.recipient.address)
        return sender_balance, recipient_balance

    def get_account(self):
        return random.choice(self.user.environment.shared.accounts)

    def create_account(self):
        return self.web3_client.create_account()

    @task
    @execute_before("task_block_number")
    def task_send_neon(self):
        """Transferring funds to a random account"""
        # add credits to account
        self.nonce = self.web3_client.get_nonce(self.account)
        self.recipient = self.get_account()
        self.log.info(
            f"Send `neon` from {str(self.account.address)[-8:]} to {str(self.recipient.address)[-8:]}. nonce {self.nonce}"
        )

        tx = self.web3_client.send_neon(self.account, self.recipient, amount=1, nonce=self.nonce)

        return tx, self.web3_client.get_nonce(self.account)


class ScheduledTxUser(User):
    tasks = {
        NeonTasksSet: 1,
        NeonIterativeTasksSet: 1,
    }
