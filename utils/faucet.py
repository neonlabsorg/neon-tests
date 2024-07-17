import abc
import time

import requests
import typing as tp
import urllib.parse

from utils.consts import FAUCET_ADDRESSES
from utils.helpers import wait_condition
from utils.web3client import NeonChainWeb3Client, Web3Client


class BaseFaucet(abc.ABC):
    def __init__(
        self,
        faucet_url: str,
        web3_client: Web3Client,
        session: tp.Optional[tp.Any] = None,
    ):
        self._url = faucet_url
        self._session = session or requests.Session()
        self.web3_client = web3_client

    def _request_tokens(
            self,
            endpoint: tp.Literal["request_neon", "request_erc20"],
            payload: dict[tp.Union[tp.Literal["wallet"], str], str],
    ) -> requests.Response:
        address = payload["wallet"]
        assert address.startswith("0x")

        url = urllib.parse.urljoin(self._url, endpoint)

        # TODO delete after https://neonlabs.atlassian.net/browse/DOPS-730 completed
        if endpoint == "request_erc20":
            url = urllib.parse.urljoin("https://api.neonfaucet.org/request_erc20", endpoint)

        balance_before = self.web3_client.get_balance(address)

        response = self._session.post(url, json=payload)
        counter = 0
        while "Blockhash not found" in response.text and counter < 3:
            time.sleep(3)
            response = self._session.post(url, json=payload)
            counter += 1
        assert (
            response.ok
        ), "Faucet returned error: {}, status code: {}, url: {}".format(
            response.text, response.status_code, response.url
        )
        wait_condition(lambda: self.web3_client.get_balance(address) > balance_before)
        return response


class NeonFaucet(BaseFaucet):
    def __init__(
            self,
            faucet_url: str,
            web3_client: NeonChainWeb3Client,
            session: tp.Optional[tp.Any] = None,
    ):
        super().__init__(
            faucet_url=faucet_url,
            web3_client=web3_client,
            session=session,
        )

    def request_neon(self, address: str, amount: int = 100) -> requests.Response:
        return self._request_tokens(
            endpoint="request_neon",
            payload={"amount": amount, "wallet": address},
        )


class ERC20Faucet(BaseFaucet):
    @abc.abstractmethod
    def request_erc20(self, address: str, amount: int = 100) -> requests.Response:
        raise NotImplementedError


class USDCFaucet(ERC20Faucet):
    def request_erc20(self, address: str, amount: int = 100) -> requests.Response:
        token_addr = FAUCET_ADDRESSES["USDC"]
        return self._request_tokens(
            endpoint="request_erc20",
            payload={"amount": amount, "wallet": address, "token_addr": token_addr},
        )
