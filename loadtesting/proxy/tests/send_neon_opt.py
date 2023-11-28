"""
Optimized suite for sending Neon messages very fast, for testing mainnet/devnet for maximum throughput.
"""
import os
import logging
import random
from locust import TaskSet, task, HttpUser
from utils.web3client import NeonChainWeb3Client


LOG = logging.getLogger(__name__)
USERS_PER_INSTANCE = int(os.environ.get("USERS_PER_INSTANCE", "100"))
PROXY_URL = "https://devnet.neonevm.org"
GET_GAS_PRICE = "GET_GAS_PRICE" in os.environ
ONE_RECIPIENT = "USE_ONE_RECIPIENT" in os.environ


class NeonTasksSet(HttpUser):
    wait_time = 2

    def on_start(self):
        self._private_key = (
            int(os.environ.get("BASE_PRIVATE_KEY"))
            + USERS_PER_INSTANCE * self.environment.runner.worker_index
            + self.environment.runner.user_count
        )
        LOG.info("Private key: ", self._private_key)
        self.web3 = NeonChainWeb3Client(PROXY_URL)
        self.account = self.web3._web3.eth.account.from_key(self._private_key)
        self.nonce = self.web3.get_nonce(self.account.address)
        LOG.info(f"Start user {self.account.address} nonce: {self.nonce}")
        if not hasattr(self.environment, "users"):
            self.environment.users = [self.account.address]
        else:
            self.environment.users.append(self.account.address)

    @task
    def task_send_neon(self):
        if ONE_RECIPIENT:
            recipient = self.environment.users[0]
        else:
            recipient = random.choice(self.environment.users)
        tx = self.web3.send_neon(
            self.account,
            to=self.environment.users[recipient],
            gas=30000,
            gas_price=None if GET_GAS_PRICE else 0,
            amount=0.00000001,
            nonce=self.nonce,
            wait_for_recipient=False,
        )
        self.nonce += 1
        LOG.info(f"Sent NEON from {self.account.address} to {recipient}: {tx}")
