import os
import random
import logging
import time
import decimal

import web3
from locust import tag, task, User

from loadtesting.proxy.common.base import NeonProxyTasksSet
from loadtesting.proxy.common.events import execute_before

LOG = logging.getLogger(__name__)


GASLESS_INSTALL = True if "GASLESS" in os.environ else False


class BankAccountFaucet:
    def __init__(self, web3_client: "NeonWeb3ClientExt"):
        self.web3_client = web3_client
        if "BANK_PRIVATE_KEY" not in os.environ:
            raise AssertionError("BANK_PRIVATE_KEY env variable is not set")
        self._bank_account = web3.Account.from_key(os.environ["BANK_PRIVATE_KEY"])

    def request_neon(self, to_address: str, amount: int) -> str:
        """Request neon from bank account"""
        for _ in range(3):
            time.sleep(random.randint(1, 10))
            try:
                return self.web3_client.send_neon(
                    self._bank_account,
                    to_address,
                    amount,
                    receipt_timeout=300,
                    gas_price=0 if GASLESS_INSTALL else None,
                )
            except Exception as e:
                LOG.error(f"Can't send amount from bank account, retry: {e}")
        else:
            raise AssertionError("Can't send money to account for 3 retries")

    def return_neons(self, from_address: web3.Account) -> str:
        """Return neon to bank account"""
        balance = self.web3_client.get_balance(from_address.address)
        LOG.info(
            f"Balance of {from_address.address} is {balance} {balance - 21000} {type(balance)}"
        )
        amount = balance - decimal.Decimal("0.02")
        LOG.info(f"Return {amount} neon from {from_address.address} to bank account")
        for _ in range(5):
            try:
                time.sleep(random.randint(1, 10))
                return self.web3_client.send_neon(
                    from_address,
                    self._bank_account,
                    amount,
                    gas_price=0 if GASLESS_INSTALL else None,
                    gas=21000,
                    receipt_timeout=300,
                )
            except Exception as e:
                LOG.error(f"Can't return NEONs from {from_address.address}: {e}")
                time.sleep(random.randint(1, 10))


@tag("send_neon")
class NeonTasksSet(NeonProxyTasksSet):
    """Implements Neons transfer base pipeline tasks"""

    nonce: int
    recipient: str

    def on_start(self) -> None:
        super().on_start()
        self.faucet = BankAccountFaucet(self.web3_client)
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

    def on_stop(self) -> None:
        self.faucet.return_neons(self.account)

    @task
    # @execute_before("task_block_number")
    def task_send_neon(self):
        """Transferring funds to a random account"""
        # add credits to account
        if self.nonce % 20 == 0:
            self.check_balance(self.account)
        # self.nonce = self.web3_client.get_nonce(self.account)
        self.recipient = self.get_account()
        self.log.info(
            f"Send `neon` from {str(self.account.address)[-8:]} to {str(self.recipient.address)[-8:]}. nonce {self.nonce}"
        )

        self.nonce += 1

        tx = self.web3_client.send_neon(
            self.account,
            self.recipient,
            amount=0.00000001,
            nonce=self.nonce - 1,
            gas=21000,
            gas_price=0 if GASLESS_INSTALL else None,
            wait_receipt=True,
        )
        # time.sleep(3)
        # return tx, self.web3_client.get_nonce(self.account)
        return tx, self.nonce


class NeonUser(User):
    tasks = {NeonTasksSet: 1}
