__doc__ = """
    --batch_request_size and --concurrent_requests work together, and Solana will regard the number of sent requests 
    as the multiple of the two. Use with caution to avoid hitting the request rate limit (error 429)
"""


import argparse
import datetime
import json
import logging
import asyncio
import time
import typing as tp
from itertools import zip_longest
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import pydantic
from solana.rpc.async_api import AsyncClient
from solana.constants import LAMPORTS_PER_SOL
from solana.exceptions import SolanaRpcException
from solana.rpc.commitment import Finalized
from solders.pubkey import Pubkey
from solana.rpc.providers.async_http import AsyncHTTPProvider
from solders.rpc.config import RpcTransactionConfig
from solders.rpc.requests import GetTransaction
from solders.signature import Signature
from solders.rpc.responses import (
    GetSignaturesForAddressResp,
    RpcConfirmedTransactionStatusWithSignature,
    GetTransactionResp,
)
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, RetryCallState
from tqdm.asyncio import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from utils.dynamic_semaphore import DynamicSemaphore
from utils.logger import create_logger


T = tp.TypeVar('T')

logger: logging.Logger
semaphore: DynamicSemaphore
batch_request_size: int


class Operator(pydantic.BaseModel):
    name: str
    accounts: list[str]

    @pydantic.field_validator("accounts", mode="before")
    def validate_account(cls, accounts):
        for account in accounts:
            try:
                Pubkey.from_string(account)
            except ValueError:
                raise ValueError(f"Invalid Solana account: {account}")
        return accounts


def parse_args() -> argparse.Namespace:
    def valid_url(url):
        try:
            result = urlparse(url)
            if all([result.scheme, result.netloc]):
                return url
            else:
                raise argparse.ArgumentTypeError(f"'{url}' is not a valid URL.")
        except ValueError:
            raise argparse.ArgumentTypeError(f"'{url}' is not a valid URL.")

    def parse_operators(file_path: str) -> list[Operator]:
        with open(file_path) as f:
            data = json.load(f)
        operators = [Operator(**operator) for operator in data]
        return operators

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--solana_url", type=valid_url, required=True)
    parser.add_argument('--csv_report', action='store_true', help="Enable CSV report generation")
    parser.add_argument('--push_to_prometheus', action='store_true', help="Enable data push to Prometheus")
    parser.add_argument("--from_slot", type=int, required=True, help="Oldest slot")
    parser.add_argument("--to_slot", type=int, required=True, help="Newest slot")
    parser.add_argument("--operators", type=parse_operators, required=True, help=str(Operator.schema()))
    parser.add_argument("--batch_request_size", type=int, default=33)
    parser.add_argument("--concurrent_requests", type=int, default=3)
    parser.add_argument(
        "--log_level",
        type=str,
        default="INFO",
        choices=[
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        ],
    )

    args, _ = parser.parse_known_args()
    if not args.csv_report and not args.push_to_prometheus:
        parser.error("At least one of these options must me used: --csv_report, --push_to_prometheus")

    if args.csv_report:
        parser.add_argument("--report_dir", type=Path, default=Path(__file__).parent),

    args, _ = parser.parse_known_args()

    if args.csv_report:
        report_dir: Path = args.report_dir
        if not report_dir.exists() or not report_dir.is_dir():
            parser.error(f"Directory {report_dir} does not exist")

    if args.push_to_prometheus:
        parser.add_argument("--prometheus_push_gateway", type=valid_url, required=True)

    known_args, _ = parser.parse_known_args()

    return known_args


async def handle_retry(retry_state: RetryCallState) -> None:
    scale_factor = 0.8

    if retry_state.attempt_number > 1:
        logger.debug(f"Retrying {retry_state.attempt_number - 1} time. Args: {retry_state.args}")

        # Cut the number of concurrent connections
        new_permits = max(1, int(semaphore._current_permits * scale_factor))
        await semaphore.set_permits(new_permits)

        # Cut batch request size
        global batch_request_size
        batch_request_size = int(batch_request_size * scale_factor)


@retry(
    wait=wait_exponential(3),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(SolanaRpcException),
    before_sleep=handle_retry,
)
async def get_signatures_in_range(
        sol_client: AsyncClient,
        operator: Operator,
        account: str,
        from_slot: int,
        to_slot: int,
) -> dict[str, dict[str, RpcConfirmedTransactionStatusWithSignature]]:
    account_pubkey = Pubkey.from_string(account)
    all_signatures = []
    before_signature = None

    while True:
        async with semaphore:
            signatures: GetSignaturesForAddressResp = await sol_client.get_signatures_for_address(
                account_pubkey, before=before_signature, commitment=Finalized,
            )

        if not signatures.value:
            break

        for signature_info in signatures.value:
            slot = signature_info.slot

            if slot > to_slot:
                continue

            if slot < from_slot:
                break

            all_signatures.append(signature_info)

        before_signature = signatures.value[-1].signature

        if signatures.value[-1].slot <= from_slot:
            break

    all_signatures.sort(key=lambda sig: sig.block_time)

    if all_signatures:
        first_timestamp = all_signatures[0].block_time
        first_timestamp_human = datetime.datetime.utcfromtimestamp(first_timestamp)
        last_timestamp = all_signatures[-1].block_time
        last_timestamp_human = datetime.datetime.utcfromtimestamp(last_timestamp)
        logger.info(f"{account} first signature timestamp: {first_timestamp}, {first_timestamp_human}")
        logger.info(f"{account} last signature timestamp: {last_timestamp}, {last_timestamp_human}")
    else:
        logger.info("No signatures found in the specified range.")

    return {operator.name: {account: all_signatures}}


def get_key_index_from_tx(tx: GetTransactionResp, key: Pubkey) -> int:
    for index, account_key in enumerate(tx.value.transaction.transaction.message.account_keys):
        if account_key == key:
            return index
    else:
        raise LookupError(f"Key {key} not found in transaction {tx.value}")


@retry(
    wait=wait_exponential(3),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(SolanaRpcException),
    before_sleep=handle_retry,
)
async def batch_fetch_transaction_balance_timestamp(
        provider: AsyncHTTPProvider,
        sol_client: AsyncClient,
        signatures: tuple[str, ...],
        operator_key: Pubkey,
) -> tuple[tuple[str, int, int, int], ...]:
    reqs = tuple(
        GetTransaction(Signature.from_string(sig), config=RpcTransactionConfig(max_supported_transaction_version=0),)
        for sig in signatures
    )
    parsers = tuple(GetTransactionResp for _ in range(len(signatures)))

    async with semaphore:
        transactions_batch = await provider.make_batch_request(reqs, parsers)  # noqa

    balances_and_timestamps = []

    for i, transaction in enumerate(transactions_batch):
        account_index = get_key_index_from_tx(tx=transaction, key=operator_key)
        balance_before = transaction.value.transaction.meta.pre_balances[account_index]
        balance_after = transaction.value.transaction.meta.post_balances[account_index]
        timestamp = (
            transaction.value.block_time or (await sol_client.get_block(slot=transaction.value.slot)).value.block_time
        )
        signature = str(signatures[i])
        balances_and_timestamps.append((signature, balance_before, balance_after, timestamp))
    return tuple(balances_and_timestamps)


async def get_transaction_data(
        signatures: tuple[str, ...],
        sol_client: AsyncClient,
        operator_name: str,
        operator_key: str,
        concurrent_requests: int,
) -> list[dict[str, tp.Any]]:
    operator_key = Pubkey.from_string(operator_key)

    data = []

    if signatures:
        provider = AsyncHTTPProvider(sol_client._provider.endpoint_uri)
        sig_batches = split_into_tuples(signatures, batch_request_size)

        desc = f"Fetch Transactions for Operator {operator_name}, key {operator_key}"
        with logging_redirect_tqdm():
            with tqdm(total=len(signatures), desc=desc) as pbar:
                for signature_batch_group in zip_longest(*[iter(sig_batches)] * concurrent_requests, fillvalue=None):
                    tasks = []
                    for signature_batch in signature_batch_group:
                        if signature_batch is not None:
                            coroutine = batch_fetch_transaction_balance_timestamp(
                                provider=provider,
                                sol_client=sol_client,
                                signatures=signature_batch,
                                operator_key=operator_key,
                            )
                            task = asyncio.create_task(coroutine)
                            tasks.append(task)

                    for completed_task in asyncio.as_completed(tasks):
                        balance_and_timestamp_batch = await completed_task
                        pbar.update(len(balance_and_timestamp_batch))

                        for signature, balance_before, balance_after, timestamp in balance_and_timestamp_batch:
                            data.append(
                                {
                                    "operator_name": operator_name.strip(),
                                    "operator_key": str(operator_key).strip(),
                                    "signature": str(signature).strip(),
                                    "timestamp": timestamp,
                                    "balance_before": balance_before,
                                    "balance_after": balance_after,
                                }
                            )

    logger.debug(f"Done getting Operator {operator_name} account  {operator_key} data")
    return data


def split_into_tuples(collection: tp.Collection[T], length: int) -> tuple[tuple[T, ...], ...]:
    return tuple(tuple(collection[i:i + length]) for i in range(0, len(collection), length))


def render_csv_report(df: pd.DataFrame, report_dir: Path, title: str):
    csv_file = report_dir / f"operator_daily_report_{time.time()}.csv"
    logger.info(f"Save daily report to {csv_file}")
    csv_file.unlink(missing_ok=True)
    header = True

    for operator_name, group in df.groupby("operator_name"):
        total_expense = group["expense"].sum()
        total_deposit = group["deposit"].sum()
        total_diff = group["diff"].sum()
        total = pd.DataFrame({
            "operator_name": [""],
            "date": ["TOTAL"],
            "expense": [total_expense],
            "deposit": [total_deposit],
            "diff": [total_diff],
        })

        csv_df = pd.concat([group, total])
        scv_data = csv_df.to_csv(header=header)

        with open(csv_file, "a") as f:
            if header:
                f.write(f"{title}\n")
            f.write(scv_data)
            f.write("\n")

        header = False


def push_to_prometheus(df: pd.DataFrame, gateway: str):
    ...


async def main():
    args = parse_args()

    global logger
    log_level = getattr(logging, args.log_level)
    logger = create_logger(name=Path(__file__).name, level=log_level)

    global semaphore
    semaphore = DynamicSemaphore(initial_permits=args.concurrent_requests, log_level=log_level)

    global batch_request_size
    batch_request_size = args.batch_request_size

    async with AsyncClient(endpoint=args.solana_url) as sol_client:

        # slot = (await sol_client.get_slot()).value - int(48 * 60 * 60 * 2.5)
        # args.from_slot = slot

        operator: Operator

        # Get signatures
        get_signature_tasks = []
        for operator in args.operators:
            for operator_account in operator.accounts:
                task = get_signatures_in_range(sol_client, operator, operator_account, args.from_slot, args.to_slot)
                get_signature_tasks.append(task)
        signature_infos = await asyncio.gather(*get_signature_tasks)

        data = []
        for signature_info in signature_infos:
            for operator_name, transactions_per_account in signature_info.items():
                for operator_key, signatures in transactions_per_account.items():
                    signature: RpcConfirmedTransactionStatusWithSignature
                    for signature in signatures:
                        row = [
                            operator_name,
                            operator_key,
                            str(signature.signature),
                        ]
                        data.append(row)
        df = pd.DataFrame(data, columns=['operator_name', 'operator_key', 'signature'])

        # Get transactions per signatures
        transactions_data = []
        for (operator_name, operator_key), group in df.groupby(["operator_name", "operator_key"]):
            signatures = group["signature"].to_list()
            task = get_transaction_data(
                signatures=signatures,
                sol_client=sol_client,
                operator_name=operator_name,
                operator_key=operator_key,
                concurrent_requests=args.concurrent_requests,
            )
            transaction_info_batches = await asyncio.gather(task)
            flat_transaction_info = [item for batch in transaction_info_batches for item in batch]
            transactions_data.extend(flat_transaction_info)

        # Merge signature and transaction data and validate it
        transactions_df = pd.DataFrame(transactions_data)
        assert len(transactions_df) == len(df), f"Found {len(df)} signatures but {len(transactions_df)} transactions"
        df = df.merge(transactions_df, how="left")
        assert not df.isna().any().any(), f"Data has missing values\n {df[df.isna().any(axis=1)]}"
        df = df.sort_values(by=["operator_name", "operator_key", "timestamp"]).reset_index(drop=True)

        # df = pd.read_csv("data_dump.csv")

        # Convert balance_before and balance_after from lamports to SOL
        df["balance_before"] = df["balance_before"] / LAMPORTS_PER_SOL
        df["balance_after"] = df["balance_after"] / LAMPORTS_PER_SOL

        # Add 'expense', 'deposit', 'diff' columns based on balance changes
        df["balance_change"] = df["balance_after"] - df["balance_before"]
        df["expense"] = df["balance_change"].apply(lambda x: x if x < 0 else 0)  # Negative expense values
        df["deposit"] = df["balance_change"].apply(lambda x: x if x > 0 else 0)  # Positive deposit values
        df["diff"] = df["expense"] + df["deposit"]

        # Convert timestamp to datetime and add column "date" for daily aggregation
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df["date"] = df["timestamp"].dt.date

        # Aggregate data to daily sums by Operator
        daily_df = df.groupby(['operator_name', 'date']).agg({
            'expense': 'sum',
            'deposit': 'sum',
            'diff': 'sum',

        }).reset_index()

        if not df.empty:
            dump_file = f"data_dump_{time.time()}.csv"
            logger.info(f"Dump data to {dump_file}")
            df.to_csv(dump_file, index=False)

            if args.csv_report:
                title = f"Report from slot {args.from_slot} to slot {args.to_slot}"
                render_csv_report(daily_df.copy(), report_dir=args.report_dir, title=title)
            if args.push_to_prometheus:
                push_to_prometheus(daily_df.copy(), gateway=args.prometheus_push_gateway)


if __name__ == "__main__":
    asyncio.run(main())
