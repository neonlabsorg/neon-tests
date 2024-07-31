import os
import glob
import json
import typing as tp
import pathlib
from collections import Counter

import pandas as pd

from deploy.cli.infrastructure import get_solana_accounts_in_tx
from deploy.cli.network_manager import NetworkManager
from utils.web3client import NeonChainWeb3Client


NETWORK_MANAGER = NetworkManager()


def set_github_env(envs: tp.Dict, upper=True) -> None:
    """Set environment for GitHub action"""
    path = os.getenv("GITHUB_ENV", str())
    if os.path.exists(path):
        with open(path, "a") as env_file:
            for key, value in envs.items():
                env_file.write(f"\n{key.upper() if upper else key}={str(value)}")


def prepare_report_data(directory: str) -> pd.DataFrame:
    proxy_url = NETWORK_MANAGER.get_network_param(os.environ.get("NETWORK"), "proxy_url")
    web3_client = NeonChainWeb3Client(proxy_url)

    reports = {}
    for path in glob.glob(str(pathlib.Path(directory) / "*-report.json")):
        with open(path, "r") as f:
            rep = json.load(f)
            if isinstance(rep, list):
                for r in rep:
                    if "actions" in r:
                        reports[r["name"]] = r["actions"]
            else:
                if "actions" in rep:
                    reports[rep["name"]] = rep["actions"]

    data = []

    for app, actions in reports.items():
        added_number = 1
        counts = Counter([action["name"].lower().strip() for action in actions])
        duplicate_actions = [action for action, count in counts.items() if count > 1]

        for action in actions:
            # Ensure action name is unique by appending a counter if necessary
            base_action_name = action["name"].lower().strip()
            if base_action_name in duplicate_actions:
                unique_action_name = f"{base_action_name} {added_number}"
                added_number += 1
            else:
                unique_action_name = base_action_name

            accounts, trx = get_solana_accounts_in_tx(action["tx"])
            # accounts, trx = (2, 12)
            tx = web3_client.get_transaction_by_hash(action["tx"])
            estimated_gas = int(tx.gas) if tx and tx.gas else None
            # estimated_gas = 122879
            used_gas = int(action["usedGas"])
            fee = used_gas * int(action["gasPrice"]) / 1000000000000000000

            data.append(
                {
                    "dapp_name": app.lower().strip(),
                    "action": unique_action_name,
                    "fee_in_neon": fee,
                    "acc_count": accounts,
                    "trx_count": trx,
                    "gas_estimated": estimated_gas,
                    "gas_used": used_gas,
                }
            )

    df = pd.DataFrame(data)
    return df


def report_data_to_markdown(df: pd.DataFrame) -> str:
    report_content = ""
    dapp_names = df['dapp_name'].unique()
    df.columns = [col.upper() for col in df.columns]
    df['USED_%_OF_EG'] = df['USED_%_OF_EG'].apply(lambda x: f"{x:.2f}")

    for dapp_name in dapp_names:
        dapp_df = df[df['DAPP_NAME'] == dapp_name].drop(columns='DAPP_NAME')
        report_content += f'\n## Cost Report for "{dapp_name.title()}" dApp\n\n'
        report_content += dapp_df.to_markdown(index=False) + "\n"

    return report_content
