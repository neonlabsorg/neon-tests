import itertools
import logging
import pathlib
import shutil
import sys
import tarfile
import time
import uuid
from dataclasses import dataclass

import six
from playwright.sync_api import BrowserContext, Page

from ui.libs import exc

LOG = logging.getLogger(__name__)


@dataclass
class Token:
    name: str
    address: str = None

    def __str__(self):
        return self.name


@dataclass
class Platform:
    solana: str = "Solana"
    neon: str = "Neon"


@dataclass
class TransactionFee:
    network_name: str
    token_name: str

    def __str__(self):
        return self.network_name


@dataclass
class TransactionFeeType:
    neon: TransactionFee = TransactionFee("Neon", "NEON")
    sol: TransactionFee = TransactionFee("Solana", "SOL")
    none: TransactionFee = None


@dataclass
class PriorityFee:
    fast: str = "Fast"
    turbo: str = "Turbo"
    ultra: str = "Ultra"
    custom: str = "Custom"
    none: str = None


@dataclass
class Tokens:
    neon = Token("NEON", "89dre8rZjLNft7HoupGiyxu3MNftR577ZYu8bHe2kK7g")
    wneon = Token("wNEON", "0x11adC2d986E334137b9ad0a0F290771F31e9517F")
    sol = Token("SOL", "0xc7Fc9b46e479c5Cb42f6C458D1881e55E6B7986c")
    wsol = Token("wSOL", "0xc7Fc9b46e479c5Cb42f6C458D1881e55E6B7986c")
    usdt = Token("USDT", "0x6eEf939FC6e2B3F440dCbB72Ea81Cd63B5a519A5")
    usdc = Token("USDC", "0x512E48836Cd42F3eB6f50CEd9ffD81E0a7F15103")


BASE_USER_DATA_DIR = "user_data"
"""Base Path to a Chrome extensions User Data Directory.
"""

TMP_USER_DATA_DIR = f"/tmp/{BASE_USER_DATA_DIR}"
"""Temporary path to a MetaMask extensions User Data Directory, which stores browser session data like cookies and local storage.
"""


def open_safe(context: BrowserContext, url: str, retry_count: int = 3) -> Page:
    while retry_count > 0:
        try:
            page = context.new_page()
            page.goto(url)
            return page
        except:
            retry_count -= 1
            if retry_count == 0:
                raise TimeoutError
            page.close()


def insert_cookies_to_context(resp_cookies, context):
    cookies = []
    for cook in resp_cookies:
        if cook.name.startswith("__"):  # playwright can't load this cookies, don't know why
            continue
        cookies.append(
            {
                "name": cook.name,
                "value": cook.value,
                "domain": cook.domain,
                "path": cook.path,
            }
        )
    context.add_cookies(cookies)


def rm_tree(p: pathlib.Path) -> None:
    """Remove directory recursively"""
    if p.is_file():
        p.unlink()
    else:
        for child in p.iterdir():
            rm_tree(child)
        p.rmdir()


def clone_user_data(extensions_dir: pathlib.Path) -> pathlib.Path:
    """Clone chrome extension user data"""
    return shutil.copytree(
        extensions_dir,
        pathlib.Path(TMP_USER_DATA_DIR) / uuid.uuid4().hex,
    )


def extract_tar_gz(source: pathlib.Path, dest: pathlib.Path) -> pathlib.Path:
    """Extract source into destination"""
    with tarfile.open(source) as file:
        file.extractall(dest)
    return dest


def try_until(func, try_msg=None, error_msg=None, log=None, interval=1, timeout=360, times=None, raise_on_timeout=True):
    """
    repeat call func while it returns False
    raises exc.TimeoutError if timeout expired or call times reached
    """
    log = log or LOG
    begin_msg = "Trying {0} until (timeout: {1} interval: {2} times: {3})".format(
        func, timeout, interval, times or "unlimited"
    )
    try_msg = try_msg or "{0} returns false".format(func)
    error_msg = error_msg or "Try {0} Failed!".format(try_msg)

    start_time = time.monotonic()
    log.debug(begin_msg)
    for num in itertools.count(1):
        log.debug("%s (%s) ...", try_msg, num)
        try:
            result = func()
            if result:
                return result
        except Exception as e:
            msg = "{0}: got error: {1}".format(error_msg, e)
            six.reraise(exc.Error, exc.Error(msg), sys.exc_info()[2])
        else:
            if time.monotonic() - start_time > timeout:
                if not raise_on_timeout:
                    return
                else:
                    msg = "{0}: timeout {1} seconds exceeded".format(error_msg, timeout)
                    raise exc.TimeoutError(msg)
            if times and num >= times:
                if not raise_on_timeout:
                    return
                else:
                    msg = "{0}: call count {1} times exceeded".format(error_msg, times)
                    raise exc.TimeoutError(msg)
                raise exc.TimeoutError(msg)
        log.debug("Wait {:.2f} seconds before the next attempt".format(interval))
        time.sleep(interval)
