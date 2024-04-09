import json
import os
import pathlib
from collections import defaultdict

NETWORK_NAME = os.environ.get("NETWORK", "full_test_suite")
EXPANDED_ENVS = [
    "PROXY_URL",
    "FAUCET_URL",
    "SOLANA_URL",
]


class NetworkManager:
    def __init__(self):
        self._networks = {}

        with open(pathlib.Path.cwd() / "envs.json", "r") as f:
            self._networks = json.load(f)
            environments = defaultdict(dict)

            if NETWORK_NAME not in self._networks.keys() and os.environ.get("DUMP_ENVS"):
                for var in EXPANDED_ENVS:
                    environments[NETWORK_NAME].update({var.lower(): os.environ.get(var, "")})
                environments[NETWORK_NAME]["network_ids"] = {"neon": os.environ.get("NETWORK_ID", "")}
                self._networks.update(environments)

            if NETWORK_NAME in ["devnet", "tracer_ci"]:
                for var in ["FAUCET_URL", "SOLANA_URL"]:
                    environments[NETWORK_NAME].update({var.lower(): os.environ.get(var, "")})
                    self._networks[NETWORK_NAME][var.lower()] = environments[NETWORK_NAME][var.lower()]
            

    def get_network_param(self, network, params=None):
        value = ""
        if network in self._networks:
            value = self._networks[network]
            if params:
                for item in params.split("."):
                    value = value[item]
        if isinstance(value, str):
            if os.environ.get("SOLANA_IP"):
                value = value.replace("<solana_ip>", os.environ.get("SOLANA_IP"))
            if os.environ.get("PROXY_IP"):
                value = value.replace("<proxy_ip>", os.environ.get("PROXY_IP"))
        return value

    def get_network_object(self, network_name):
        network = self.get_network_param(network_name)
        if network_name == "terraform":
            network["proxy_url"] = self.get_network_param(network_name, "proxy_url")
            network["solana_url"] = self.get_network_param(network_name, "solana_url")
            network["faucet_url"] = self.get_network_param(network_name, "faucet_url")
        return network
