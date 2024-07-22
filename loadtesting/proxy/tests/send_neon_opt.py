"""
Optimized suite for sending Neon messages very fast, for testing mainnet/devnet for maximum throughput.
"""
import os
import time
import logging
import random
from locust import TaskSet, task, HttpUser, constant
from utils.web3client import NeonChainWeb3Client


LOG = logging.getLogger(__name__)
USERS_PER_INSTANCE = int(os.environ.get("USERS_PER_INSTANCE", "100"))
BASE_PRIVATE_KEY = int(os.environ.get("BASE_PRIVATE_KEY"), 16)
PROXY_URL = os.environ.get("PROXY_URL", "https://devnet.neonevm.org")
GET_GAS_PRICE = "GET_GAS_PRICE" in os.environ
ONE_RECIPIENT = "USE_ONE_RECIPIENT" in os.environ
GET_NONCE = "GET_NONCE" in os.environ


class NeonTasksSet(HttpUser):
    wait_time = constant(2)

    def on_start(self):
        self._private_key = (
            BASE_PRIVATE_KEY
            + USERS_PER_INSTANCE * self.environment.runner.worker_index
            + self.environment.runner.user_count
        )
        LOG.info(
            f"Create new user: {USERS_PER_INSTANCE} * {self.environment.runner.worker_index} + {self.environment.runner.user_count}"
        )
        # LOG.info(f"Private key: {self._private_key}")
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

        request_meta = {
            "request_type": "http",
            "name": "Send neon",
            "start_time": time.time(),
            "response_length": 0,
            "response": None,
            "context": {},
            "exception": None,
        }
        start_perf_counter = time.perf_counter()
        LOG.info(f"Send from {self.account.address} to {recipient} and nonce: {self.nonce}")
        try:
            tx = self.web3.send_neon(
                self.account,
                to=recipient,
                gas=30000,
                gas_price=None if GET_GAS_PRICE else 0,
                amount=0.00000001,
                nonce=None if GET_NONCE else self.nonce,
                wait_for_recipient=False,
            )
            request_meta["response"] = tx.hex()
            LOG.info(f"Sent from {self.account.address} to {recipient}: {tx.hex()}")
        except Exception as e:
            request_meta["exception"] = e
            LOG.info(f"Sent from {self.account.address} to {recipient} failed: {e}")
        request_meta["response_time"] = (time.perf_counter() - start_perf_counter) * 1000
        self.nonce += 1
        self.environment.events.request.fire(**request_meta)
