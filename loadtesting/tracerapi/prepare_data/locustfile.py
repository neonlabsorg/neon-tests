import collections
import functools
import json
import logging
import pathlib
import random
import typing as tp

import gevent
import web3
from locust import User, between, events, tag, task
from loadtesting.proxy import locustfile as head

RETRIEVE_STORE_VERSION = "0.8.10"
"""RetrieveStore contract version
"""

DEFAULT_DUMP_FILE = "dumped_data/transaction.json"
"""Default file name for transaction history
"""

transaction_history = collections.defaultdict(
    functools.partial(collections.defaultdict, list)
)
"""Transactions storage {account: [{blockNumber, blockHash, contractAddress},]}
"""

LOG = logging.getLogger("neon_client")


def dump_history(attr) -> tp.Callable:
    """Save transaction history"""

    @functools.wraps(attr)
    def ext_runner(func: tp.Callable) -> tp.Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> tp.Any:
            tx, info = func(self, *args, **kwargs)
            if tx:
                transaction_history[attr][str(tx["from"])].append(
                    {
                        "blockHash": tx["blockHash"].hex(),
                        "blockNumber": hex(tx["blockNumber"]),
                        "contract": tx.get("contract", ""),
                        "to": str(tx["to"]),
                        "additional_info": info,
                    }
                )
            return tx

        return wrapper

    return ext_runner


@events.test_stop.add_listener
def teardown(*args, **kwargs) -> None:
    """Test stop event handler"""
    if transaction_history:
        dumped_path = pathlib.Path(__file__).parent.parent / DEFAULT_DUMP_FILE
        dumped_path.parents[0].mkdir(parents=True, exist_ok=True)
        with open(dumped_path, "w") as fp:
            LOG.info(
                f"Dumped transaction history to `{dumped_path.as_posix()}`")
            json.dump(transaction_history, fp=fp, indent=4, sort_keys=True)


@tag("store")
@tag("call")
class EthGetStorageAtPreparationStage(head.NeonTasksSet):
    """
        Preparation stage for eth_getStorageAt and eth_call test suite. 
        Deploy RetrieveStore contract.
    """

    _deploy_contract_locker = gevent.threading.Lock()
    _deploy_contract_done = False
    storage_contract: tp.Optional["web3._utils.datatypes.Contract"] = None

    wait_time = between(0.5, 2)

    def deploy_storage_contract(self):
        """Deploy once for all spawned users"""
        EthGetStorageAtPreparationStage._deploy_contract_done = True
        account = self.web3_client.create_account()
        self.check_balance(account=account)
        contract_name = "RetrieveStore"
        self.log.info(f"`{contract_name}`: deploy contract.")
        contract, _ = self.deploy_contract(
            contract_name, RETRIEVE_STORE_VERSION, account, contract_name="Storage"
        )
        if not contract:
            self.log.error(f"`{contract_name}` contract deployment failed.")
            EthGetStorageAtPreparationStage._deploy_contract_done = False
            return
        EthGetStorageAtPreparationStage.storage_contract = contract

    def on_start(self) -> None:
        """on_start is called when a Locust start before any task is scheduled"""
        super(EthGetStorageAtPreparationStage, self).on_start()
        # setup class once
        with self._deploy_contract_locker:
            if not EthGetStorageAtPreparationStage._deploy_contract_done:
                self.deploy_storage_contract()

    @task
    @dump_history("store")
    def prepare_data_by_store_int(self) -> None:
        """Store random int to contract"""
        contract = EthGetStorageAtPreparationStage.storage_contract
        if contract:
            data = random.choice(range(100000))
            self.log.info(
                f"Store random data `{data}` to contract by {self.account.address[:8]}."
            )
            tx = contract.functions.store(data).build_transaction(
                {
                    "nonce": self.web3_client.eth.get_transaction_count(
                        self.account.address
                    ),
                    "gasPrice": self.web3_client.gas_price(),
                }
            )
            tx_receipt = dict(
                self.web3_client.send_transaction(self.account, tx))
            tx_receipt.update(
                {"contract": {"address": contract.address, "abi": contract.abi}}
            )
            return tx_receipt, {}
        self.log.info(f"no `storage` contracts found, data store canceled.")


@tag("neon")
@tag("transfer")
class NeonTransferPreparationStage(head.NeonTasksSet):
    def get_account():
        return super().web3_client.create_account()
    
    @task
    @dump_history("transfer")
    def prepare_data_by_neon_transfer(
        self,
    ) -> tp.Union[None, web3.datastructures.AttributeDict]:
        """Make number of `NEONs` transfer transactions between different client accounts"""
        return super(NeonTransferPreparationStage, self).task_send_neon()


@tag("erc20")
@tag("transfer")
class ERC20TransferPreparationStage(head.ERC20TasksSet):
    def get_account():
        return super().web3_client.create_account()
    
    @task
    @dump_history("transfer")
    def prepare_data_by_erc20_transfer(
        self,
    ) -> tp.Union[None, web3.datastructures.AttributeDict]:
        """Make number of `ERC20` transfer transactions between different client accounts"""
        return super(ERC20TransferPreparationStage, self).task_send_erc20()


@tag("erc20spl")
@tag("logs")
class ERC20WrappedPreparationStage(head.ERC20SPLTasksSet):
    def get_account():
        return super().web3_client.create_account()
    
    @task
    @dump_history("logs")
    def prepare_data_by_erc20_wrapped(
        self,
    ) -> tp.Union[None, web3.datastructures.AttributeDict]:
        """Make number of `ERC20Wrapper` transfer transactions between different client accounts"""
        return super(ERC20WrappedPreparationStage, self).task_send_erc20_spl()


@tag("prepare")
class TracerAPIPreparationUser(User):
    """Preparation stage for TracerAPI"""

    tasks = {
        ERC20WrappedPreparationStage: 1,
        EthGetStorageAtPreparationStage: 1,
        NeonTransferPreparationStage: 1,
        ERC20TransferPreparationStage: 1,
    }
