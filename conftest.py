import os
import json
import shutil
import pathlib
import typing as tp
from dataclasses import dataclass

import pytest
from _pytest.config import Config
from _pytest.runner import runtestprotocol

from clickfile import create_allure_environment_opts
from utils.web3client import NeonWeb3Client

pytest_plugins = ["ui.plugins.browser"]


@dataclass
class EnvironmentConfig:
    evm_loader: str
    proxy_url: str
    tracer_url: str
    solana_url: str
    faucet_url: str
    network_id: int
    operator_neon_rewards_address: tp.List[str]
    spl_neon_mint: str
    neon_erc20wrapper_address: str
    operator_keys: tp.List[str]
    use_bank: bool
    eth_bank_account: str
    neonpass_url: str = ""
    ws_subscriber_url: str = ""
    account_seed_version: str = "\3"


def pytest_addoption(parser):
    parser.addoption(
        "--network", action="store", default="night-stand", help="Which stand use"
    )
    parser.addoption(
        "--make-report",
        action="store_true",
        default=False,
        help="Store tests result to file",
    )
    parser.addoption(
        "--envs", action="store", default="envs.json", help="Filename with environments"
    )


def pytest_sessionstart(session):
    """Hook for clearing the error log used by the Slack notifications utility"""
    path = pathlib.Path(f"click_cmd_err.log")
    if path.exists():
        path.unlink()


def pytest_runtest_protocol(item, nextitem):
    ihook = item.ihook
    ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
    reports = runtestprotocol(item, nextitem=nextitem)
    ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
    if item.config.getoption("--make-report"):
        path = pathlib.Path(f"click_cmd_err.log")
        with path.open("a") as fd:
            for report in reports:
                if report.when == "call" and report.outcome == "failed":
                    fd.write(f"`{report.outcome.upper()}` {item.nodeid}\n")
    return True


def pytest_configure(config: Config):
    network_name = config.getoption("--network")
    network_name = "terraform" if network_name == "aws" else network_name
    envs_file = config.getoption("--envs")
    with open(pathlib.Path().parent.parent / envs_file, "r+") as f:
        environments = json.load(f)
    assert (
        network_name in environments
    ), f"Environment {network_name} doesn't exist in envs.json"
    env = environments[network_name]
    if network_name == "devnet":
        if "SOLANA_URL" in os.environ and os.environ["SOLANA_URL"]:
            env["solana_url"] = os.environ.get("SOLANA_URL")
        if "PROXY_URL" in os.environ and os.environ["PROXY_URL"]:
            env["proxy_url"] = os.environ.get("PROXY_URL")
    if "use_bank" not in env:
        env["use_bank"] = False
    if "eth_bank_account" not in env:
        env["eth_bank_account"] = ""
    if network_name == "terraform":
        env["solana_url"] = env["solana_url"].replace(
            "<solana_ip>", os.environ.get("SOLANA_IP")
        )
        env["proxy_url"] = env["proxy_url"].replace(
            "<proxy_ip>", os.environ.get("PROXY_IP")
        )
        env["faucet_url"] = env["faucet_url"].replace(
            "<proxy_ip>", os.environ.get("PROXY_IP")
        )
    config.environment = EnvironmentConfig(**env)


@pytest.fixture(scope="session", autouse=True)
def allure_environment(pytestconfig: Config, web3_client: NeonWeb3Client):
    opts = {}
    if pytestconfig.getoption("--network") != "geth":
        opts = {
            "Network": pytestconfig.environment.proxy_url,
            "Proxy.Version": web3_client.get_proxy_version()["result"],
            "EVM.Version": web3_client.get_evm_version()["result"],
            "CLI.Version": web3_client.get_cli_version()["result"],
        }

    yield opts

    allure_dir = pytestconfig.getoption("--alluredir")
    allure_path = pathlib.Path() / allure_dir
    create_allure_environment_opts(opts)
    categories_from = pathlib.Path() / "allure" / "categories.json"
    categories_to = allure_path / "categories.json"
    shutil.copy(categories_from, categories_to)

    if "CI" in os.environ:
        with open(allure_path / "executor.json", "w+") as f:
            json.dump(
                {
                    "name": "Github Action",
                    "type": "github",
                    "url": "https://github.com/neonlabsorg/neon-tests/actions",
                    "buildOrder": os.environ.get("GITHUB_RUN_ID", "0"),
                    "buildName": os.environ.get("GITHUB_WORKFLOW", "neon-tests"),
                    "buildUrl": f'{os.environ.get("GITHUB_SERVER_URL", "https://github.com")}/{os.environ.get("GITHUB_REPOSITORY", "neon-tests")}/actions/runs/{os.environ.get("GITHUB_RUN_ID", "0")}',
                    "reportUrl": "",
                    "reportName": "Allure report for neon-tests",
                },
                f,
            )


@pytest.fixture(scope="session", autouse=True)
def web3_client(pytestconfig: Config) -> NeonWeb3Client:
    client = NeonWeb3Client(
        pytestconfig.environment.proxy_url, pytestconfig.environment.network_id, tracer_url=pytestconfig.environment.tracer_url
    )
    return client
