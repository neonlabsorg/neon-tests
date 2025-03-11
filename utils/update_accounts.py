import base64
import urllib
import urllib3
import json
import pathlib
from pprint import pp
import re
import time
import typing as tp

from eth_keys import keys as eth_keys
from solana.rpc.commitment import Confirmed
from solana.rpc.core import RPCNoResultException
from solana.exceptions import SolanaExceptionBase
from solana.transaction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from utils.consts import OPERATOR_KEYPAIR_PATH
from utils.evm_loader import EvmLoader

class AccIndexer:
    def __init__(self,
                 owner: str,
                 filters: tp.Mapping[int, str],
                 rpc_source: str = None,
                 rpc_owner: str = None,
                 tracer_source: str = None,
                 tracer_pos: int = None):
        self.rpc = dict()
        self.tracer = dict()
        self.filters = filters
        self.owner = owner
        self.takes = 0

        if rpc_source is not None:
            assert tracer_source is None, "AccIndexer:: source arguments ambiguous"
            assert tracer_pos is None,    "AccIndexer:: source arguments ambiguous"
            assert rpc_owner is not None, "AccIndexer:: RPC source require owner address"
            pool = urllib3.PoolManager()
            response = pool.request(method="POST",
                                    url=rpc_source,
                                    headers={"Content-Type": "application/json"},
                                    body=json.dumps({
                                        "jsonrpc": "2.0",
                                        "id": 1,
                                        "method": "getProgramAccounts",
                                        "params": [
                                            rpc_owner,
                                            {"encoding" : "base64", "dataSlice": { "offset": 0, "length": 21 } }
                                        ],
                                    }))
            self.rpc["accounts"] = json.loads(response.data.decode("utf-8"))
            self.rpc["iter"] = iter(self.rpc["accounts"]["result"])

        if tracer_source is not None:
            assert rpc_source is None,    "AccIndexer:: source arguments ambiguous"
            assert rpc_owner is None,     "AccIndexer:: source arguments ambiguous"
            assert tracer_pos is not None,"AccIndexer:: Tracer file seek position should be set"

            self.tracer["file"] = open(tracer_source)
            if tracer_pos:
                self.tracer["file"].seek(tracer_pos)


    def dump(self):
        if self.rpc:
            for account in self.rpc["accounts"]["result"]:
                tag = base64.b64decode(account["account"]["data"][0])[0]
                comment = self.filters[tag] if tag in self.filters.keys() else "       "

                print("{}    {}    {}    {}".format(
                    comment,
                    base64.b64decode(account["account"]["data"][0]).hex(),
                    account["pubkey"],
                    account["account"]["owner"],
                ))


    def take_accounts(self, amount: int = 1):
        accounts = []
        self.takes += 1

        if self.rpc:
            stat = {"accounts_taken": 0,
                    "accounts_missed": 0 }
            for idx, account in enumerate(self.rpc["iter"], start=1):
                owner = account["account"]["owner"]
                tag = base64.b64decode(account["account"]["data"][0])[0]
                if (owner == self.owner) and (tag in self.filters.keys()):
                    accounts.append({ "owner": account["account"]["owner"],
                                      "pubkey": account["pubkey"],
                                      "data": base64.b64decode(account["account"]["data"][0]).hex()
                                       })
                    stat["accounts_taken"] += 1
                else:
                    stat["accounts_missed"] += 1

                if stat["accounts_taken"] == amount:
                    break
            stat["take_accounts calls"] = self.takes
            return {"accounts": accounts, "rpc_stat": stat}

        if self.tracer:
            stat = {"accounts_taken":  0,
                    "accounts_missed": 0,
                    "lines_missed":    0,
                    "position_start":  self.tracer["file"].tell(),
                    "position_end":    0 }
            line = self.tracer["file"].readline()
            while line:
                match = re.search("STARTUP ACCOUNT: (\w+) -> (\w+) .+data: 0x(\w+)", line)
                if match:
                    owner = match.group(1)
                    tag = int(match.group(3)[:2], 16)
                    if (owner == self.owner) and (tag in self.filters.keys()):
                        accounts.append({"owner": match.group(1),
                                         "pubkey": match.group(2),
                                         "data": match.group(3)
                                         })
                        stat["accounts_taken"] += 1
                    else:
                        stat["accounts_missed"] += 1
                else:
                    stat["lines_missed"] += 1

                if stat["accounts_taken"] == amount:
                    break
                line = self.tracer["file"].readline()

            stat["position_end"] = self.tracer["file"].tell()
            stat["take_accounts calls"] = self.takes
            return {"accounts": accounts, "tracer_stat": stat}

def prepare_operator(key_file: pathlib.Path | str, evm_loader: EvmLoader) -> Keypair:
    chain_ids: tuple[int, int] = (evm_loader.sol_chain_id, evm_loader.chain_id)
    with open(key_file, "r") as key:
        secret_key = json.load(key)
        account = Keypair.from_bytes(secret_key)

    #evm_loader.request_airdrop(account.pubkey(), 1000 * 10**9, commitment=Confirmed)

    #operator_ether = eth_keys.PrivateKey(account.secret()[:32]).public_key.to_canonical_address()
    #for chain_id in chain_ids:
    #    ether_balance_pubkey = evm_loader.ether2operator_balance(account, operator_ether, chain_id)
    #    acc_info = evm_loader.get_account_info(ether_balance_pubkey, commitment=Confirmed)
    #    if acc_info.value is None:
    #        evm_loader.create_operator_balance_account(account, operator_ether, chain_id)

    return account


"""
indexer = AccIndexer(tracer_source="/opt/devnet_accounts.log",
                     tracer_pos=0,
                     filters={0x0c: "ACC_OLD", 0x2a: "CEL_OLD"})
while True:
    chunk = indexer.get_accounts(amount=11)
    pp(chunk["tracer_stat"])
    if chunk["tracer_stat"]["accounts_taken"] == 0:
        break
"""

def update_devnet(startpos: int, stepsize: int, steps: int):
    evm_loader = EvmLoader(
        program_id='eeLSJgWzzxrqKv1UxtRVVH8FX3qCQWUs9QuAjJpETGU',
        endpoint='https://devnet.sol-rpc.neoninfra.xyz:8443/qccxeCwY02UM5p0ELvbdHS9uedrKbPE2f7eUqabd/',
        neon_chain_id=245022926,
        sol_chain_id=245022927,
        neon_token_mint_str='89dre8rZjLNft7HoupGiyxu3MNftR577ZYu8bHe2kK7g',
    )
    keypair = prepare_operator("/opt/neon-tests/ayazkov-devnet-keypair.json", evm_loader)
    indexer = AccIndexer(tracer_source="/opt/devnet_accounts.log",
                         tracer_pos=startpos,
                         filters={0x0c: "ACC_OLD", 0x2a: "CEL_OLD"},
                         owner="eeLSJgWzzxrqKv1UxtRVVH8FX3qCQWUs9QuAjJpETGU")
    neon_account = "35ccd00ef9eaf8577eab37e60d7e11ad6dab0ea4"
    split_workarounds = 0
    repeat_workarounds = 0
    repeat_flag = False
    accounts = {}

    for itx in range(steps):
        ba_accounts = []
        if not repeat_flag:
            accounts = indexer.take_accounts(amount=stepsize)
        accounts["tracer_stat"]["split_workarounds"] = split_workarounds
        accounts["tracer_stat"]["repeat_workarounds"] = repeat_workarounds
        print(accounts["accounts"])
        print(accounts["tracer_stat"])
        if not accounts["accounts"]:
            break
        for acc in accounts["accounts"]:
            ba_accounts.append(Pubkey.from_string(acc["pubkey"]))
            ba_accounts.append(Pubkey.from_string(evm_loader.ether2program(acc["data"][2:42])[0]), )
            #ba_accounts.append(evm_loader.ether2balance(acc["data"][2:42]))
        try:
            evm_loader.create_balance_account(bytes.fromhex(neon_account),
                                              keypair,
                                              additional=ba_accounts)
            repeat_flag = False
        except RPCNoResultException as e:
            try:
                for i in range(0, len(ba_accounts), 2): # divide into individual transactions per account
                    evm_loader.create_balance_account(bytes.fromhex(neon_account),
                                                      keypair,
                                                      additional=ba_accounts[i:i + 2])
                split_workarounds += 1
                repeat_flag = False
            except SolanaExceptionBase as e:
                time.sleep(3)
                repeat_flag = True
                repeat_workarounds += 1
                continue

        except SolanaExceptionBase as e:
            time.sleep(3)
            repeat_flag = True
            repeat_workarounds += 1


def update_local():
    evm_loader = EvmLoader(
        program_id='53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io',
        endpoint='http://solana:8899/',
        neon_chain_id=111,
        sol_chain_id=112,
        neon_token_mint_str='HPsV9Deocecw3GeZv1FkAPNCBRfuVyfw9MMwjwRe1xaU',
    )
    keypair = prepare_operator(pathlib.Path(OPERATOR_KEYPAIR_PATH + "/" + "id.json"), evm_loader)

    indexer = AccIndexer(rpc_source="http://solana:8899/solana",
                         rpc_owner="53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io",
                         filters={0x0c: "ACC_OLD", 0x2a: "CEL_OLD"},
                         owner="53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io")
    while True:
        accounts = indexer.take_accounts(amount=10)
        pp(accounts)
        ba_accounts = []
        if not accounts["accounts"]:
            break
        for acc in accounts["accounts"]:
            ba_accounts.append(Pubkey.from_string(acc["pubkey"]))
            ba_accounts.append(Pubkey.from_string(evm_loader.ether2program(acc["data"][2:42])[0]), )
            ba_accounts.append(evm_loader.ether2balance(acc["data"][2:42]))

        neon_account = "35ccd00ef9eaf8577eab37e60d7e11ad6dab0ea4"
        evm_loader.create_balance_account(bytes.fromhex(neon_account),
                                          keypair,
                                          additional=ba_accounts)





update_devnet(startpos=0, stepsize=10, steps=10000000)



#indexer = AccIndexer(tracer_source="/opt/devnet_accounts.log",
#                     tracer_pos=0,
#                     filters={0x0c: "ACC_OLD", 0x2a: "CEL_OLD"})
#chunk0 = indexer.get_accounts(amount=11)
#pp(chunk0)
#pp(indexer.get_accounts(amount=11))

#print("!! recreate indexer from {}".format(chunk0["tracer_stat"]["position_end"]))
#indexer = AccIndexer(tracer_source="/opt/devnet_accounts.log",
#                     tracer_pos=chunk0["tracer_stat"]["position_end"],
#                     filters={0x0c: "ACC_OLD", 0x2a: "CEL_OLD"})
#pp(indexer.get_accounts(amount=11))




#keypair = Keypair()
#pp(keypair)
#pp(keypair.pubkey())
#print("!!! exit")
#exit(0)




"""

evm_loader = EvmLoader(
    program_id          = '53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io',
    endpoint            = 'http://solana:8899/',
    neon_chain_id       = 111,
    sol_chain_id        = 112,
    neon_token_mint_str = 'HPsV9Deocecw3GeZv1FkAPNCBRfuVyfw9MMwjwRe1xaU',
)
keypair = prepare_operator(pathlib.Path(OPERATOR_KEYPAIR_PATH + "/" + "id.json"), evm_loader)

#
#  TAG_STORAGE_CELL_DEPRECATED    : u8 = 42 // (2a / Kg==)
#

acckey0  = "378AUnw2M4XnKewAnoz8NnWQyXRkGkKsXPkrDHkLkcZd"
accdata0 = "2a14fd0b205739e8da7d66b3dd312d05d48363a38b"
#acckey1  = "UyNAsdzYL9mU7NADQGpk3GFyN2vgfspbpGm8HGGfmFj"
#accdata1 = "2add76916bb60a1b0be57fca6ffc02666b27f38feb"

#pp(base64.b64decode(accdata_b64).hex()[2:42])
#pp(evm_loader.ether2program(base64.b64decode(accdata_b64).hex()[2:42]))
#pp(evm_loader.ether2balance(base64.b64decode(accdata_b64).hex()[2:42]))
#pp(Pubkey.from_string(evm_loader.ether2program(base64.b64decode(accdata_b64).hex()[2:42])[0]))

#print("evm_loader.ether2balance(base64.b64decode(accdata_b64)[1:21]): {}", evm_loader.ether2balance(base64.b64decode(accdata_b64)[1:21]))

accounts = [
    Pubkey.from_string(acckey0),
    Pubkey.from_string(evm_loader.ether2program(accdata0[2:42])[0]),
    evm_loader.ether2balance(accdata0[2:42]),

#    Pubkey.from_string(acckey1),
#    Pubkey.from_string(evm_loader.ether2program(accdata1[2:42])[0]),
#    evm_loader.ether2balance(accdata1[2:42]),


#    Pubkey.from_string("42Typw1DdKoQG8wnd4BfgfFbX3JrwhKiSkuSnagVHZ5h"),
#    #evm_loader.ether2balance(base64.b64decode(accdata_b64)[1:21])
#    #Pubkey.from_string("59QjErC8cNLPhbaGzirbtPBVSfmYDh9XeTLg5dmoL85Y"),
]
#pp(accounts)
neon_account = "35ccd00ef9eaf8577eab37e60d7e11ad6dab0ea4";
#evm_loader.make_new_user(keypair)
evm_loader.create_balance_account(bytes.fromhex("35ccd00ef9eaf8577eab37e60d7e11ad6dab0ea4"),
                                  keypair,
                                  additional=accounts)

"""