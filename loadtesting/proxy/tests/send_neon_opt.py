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
PROXY_URL = os.environ.get("PROXY_URL", "https://devnet.neonevm.org")
GET_GAS_PRICE = "GET_GAS_PRICE" in os.environ
ONE_RECIPIENT = "USE_ONE_RECIPIENT" in os.environ


class NeonTasksSet(HttpUser):
    # wait_time = constant(2)

    def on_start(self):
        self._private_key = (
            int(os.environ.get("BASE_PRIVATE_KEY"), 16)
            + USERS_PER_INSTANCE * self.environment.runner.worker_index
            + self.environment.runner.user_count
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
        try:
            tx = self.web3.send_neon(
                self.account,
                to=recipient,
                gas=30000,
                gas_price=None if GET_GAS_PRICE else 0,
                amount=0.00000001,
                nonce=self.nonce,
                wait_for_recipient=True,
            )
            request_meta["response"] = tx.hex()
            self.nonce += 1
            LOG.info(f"Sent NEON from {self.account.address} to {recipient}: {tx}")
        except Exception as e:
            request_meta["exception"] = e
            LOG.info(f"Sent NEON from {self.account.address} to {recipient} failed: {e}")
        request_meta["response_time"] = (time.perf_counter() - start_perf_counter) * 1000
        self.environment.events.request.fire(**request_meta)
