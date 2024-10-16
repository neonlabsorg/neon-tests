import subprocess
import sys
import time

import requests
from pkg_resources import parse_version


def get_installable_vyper_versions():
    url = f"https://pypi.org/pypi/vyper/json"
    for _ in range(5):
        res = requests.get(url, timeout=5)
        if res.status_code != 200:
            time.sleep(1)
            print(f"Failed request attempt: {url}, response:{res.text}")
        else:
            data = res.json()
            versions = data["releases"]
            return sorted(versions, key=parse_version, reverse=True)

    raise RuntimeError(f"Failed to request available vyper versions")


def install(version):
    code = subprocess.check_call([sys.executable, "-m", "uv", "pip", "install", f"vyper=={version}"])
    if code != 0:
        raise RuntimeError(f"Failed to install vyper {version}")


def get_three_last_versions():
    versions = get_installable_vyper_versions()
    major_versions = sorted(set(version.split(".")[1] for version in versions), reverse=True)
    last_three_majors = major_versions[:3]
    last_three_versions = []
    for major in last_three_majors:
        filtered_versions = [
            version for version in versions if version.startswith(f"0.{major}.") and "rc" not in version
        ]
        highest_version = max(
            filtered_versions, key=lambda v: [int(part.replace("b", "").replace("rc", "")) for part in v.split(".")]
        )
        last_three_versions.append(highest_version)
    return last_three_versions
