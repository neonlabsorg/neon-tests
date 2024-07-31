import textwrap
import typing as tp
from decimal import Decimal, ROUND_HALF_UP

import click
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.backends.backend_pdf import PdfPages

from utils.types import RepoType
from deploy.test_results_db.db_handler import PostgresTestResultsHandler


class TestResultsHandler:
    def __init__(self):
        self.db_handler = PostgresTestResultsHandler()

    def save_to_db(
            self,
            report_data: pd.DataFrame,
            repo: RepoType,
            branch: str,
            github_tag: tp.Optional[str],
            neon_evm_tag: str,
            proxy_tag: str,
            token_usd_gas_price: float,
    ):
        cost_report_id = self.db_handler.save_cost_report(
            repo=repo,
            branch=branch,
            github_tag=github_tag,
            neon_evm_tag=neon_evm_tag,
            proxy_tag=proxy_tag,
            token_usd_gas_price=token_usd_gas_price,
        )
        self.db_handler.save_cost_report_data(report_data=report_data, cost_report_id=cost_report_id)

    def delete_report_and_data(self, repo: str, branch: str, tag: tp.Optional[str]):
        click.echo(f"delete_report_and_data: {locals()}")
        report_ids = self.db_handler.get_cost_report_ids(repo=repo, branch=branch, tag=tag)
        if report_ids:
            self.db_handler.delete_data_by_report_ids(report_ids=report_ids)
            self.db_handler.delete_reports(report_ids=report_ids)

    def get_historical_data(
            self,
            depth: int,
            repo: RepoType,
            last_branch: str,
            previous_branch: str,
            github_tag: str,
    ) -> pd.DataFrame:
        return self.db_handler.get_historical_data(
            depth=depth,
            repo=repo,
            last_branch=last_branch,
            previous_branch=previous_branch,
            github_tag=github_tag,
        )

    @staticmethod
    def generate_and_save_plots_pdf(
            historical_data: pd.DataFrame,
            title_end: str,
            output_pdf: str,
    ) -> str:
        historical_data["timestamp"] = pd.to_datetime(historical_data["timestamp"], errors="coerce")
        historical_data["fee_in_neon"] = historical_data["fee_in_neon"].apply(Decimal)
        historical_data["fee_in_usd"] = historical_data["fee_in_neon"] * historical_data["token_usd_gas_price"]
        historical_data["acc_count"] = historical_data["acc_count"].apply(Decimal)
        historical_data["trx_count"] = historical_data["trx_count"].apply(Decimal)
        historical_data["gas_estimated"] = historical_data["gas_estimated"].apply(Decimal)
        historical_data["gas_used"] = historical_data["gas_used"].apply(Decimal)
        historical_data["token_usd_gas_price"] = historical_data["token_usd_gas_price"].apply(Decimal)
        historical_data["used_%_of_EG"] = (
            (historical_data["gas_used"] / historical_data["gas_estimated"]) * Decimal("100")
        ).apply(lambda x: x.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP))

        # analyze only the dapps that are present in the latest report
        latest_timestamp = historical_data["timestamp"].max()
        latest_report_data = historical_data[historical_data["timestamp"] == latest_timestamp]
        dapp_names = latest_report_data["dapp_name"].unique()
        metrics = ["fee_in_neon", "fee_in_usd", "acc_count", "trx_count", "gas_estimated", "gas_used", "used_%_of_EG"]
        historical_data = historical_data.sort_values(by=["timestamp"])

        unique_timestamps = historical_data["timestamp"].unique().tolist()
        unique_tags = historical_data["tag"].unique().tolist()

        if unique_tags:
            x_tick_labels = unique_tags
        else:
            x_tick_labels = [historical_data["branch"].unique()[0]] * len(unique_timestamps)

        with PdfPages(output_pdf) as pdf:
            for dapp_name in dapp_names:
                # Filter data for the current dapp_name
                dapp_data = historical_data[historical_data["dapp_name"] == dapp_name]
                actions = dapp_data["action"].unique()

                num_rows = len(actions)
                num_cols = len(metrics)
                fig, axes = plt.subplots(nrows=num_rows, ncols=num_cols, figsize=(5 * num_cols, 3 * num_rows), sharex="col")
                fig.suptitle(t=f'Cost report for "{dapp_name}" dApp on {title_end}', fontsize=16, fontweight="bold")

                for action_idx, action in enumerate(actions):
                    # Calculate y-axis limits for each metric
                    buffer_fraction = Decimal("0.5")
                    action_data = dapp_data[dapp_data["action"] == action]
                    y_limits = {}

                    # define y limits
                    for metric in metrics:
                        metric_data = action_data[metric]
                        min_val = metric_data.min()
                        max_val = metric_data.max()
                        range_val = max_val - min_val

                        if range_val == 0:
                            min_val -= abs(min_val) * buffer_fraction
                            max_val += abs(max_val) * buffer_fraction
                        else:
                            min_val -= range_val * buffer_fraction
                            max_val += range_val * buffer_fraction

                        y_limits[metric] = (min_val, max_val)

                    for metric_idx, metric in enumerate(metrics):
                        ax = axes[action_idx, metric_idx] if num_rows > 1 else axes[metric_idx]
                        data_subset = dapp_data[dapp_data["action"] == action].copy()

                        # normalize data
                        need_to_add_rows = len(unique_timestamps) - len(data_subset)
                        if need_to_add_rows:
                            for i, unique_timestamp in enumerate(unique_timestamps):
                                if unique_timestamp not in data_subset["timestamp"].values:
                                    new_row = pd.DataFrame(
                                        data=[{
                                            "timestamp": unique_timestamp,
                                            "branch": data_subset["branch"].unique()[0],
                                            "tag": unique_tags[i] if unique_tags else None,
                                            "dapp_name": data_subset.iloc[0]["dapp_name"],
                                            "action": data_subset.iloc[0]["action"],
                                        }],
                                        columns=data_subset.columns,
                                    )
                                    data_subset = pd.concat([data_subset, new_row], ignore_index=True)

                        data_subset = data_subset.sort_values(by='timestamp').reset_index(drop=True)

                        if not data_subset.empty:
                            prev_value = None
                            prev_is_valid = True

                            # Fill data for smooth lines
                            data_subset_filled = data_subset.copy()

                            for column in data_subset.columns:
                                for i in range(1, len(data_subset) - 1):
                                    if pd.isna(data_subset_filled.loc[i, column]):
                                        above_value = data_subset_filled.loc[i - 1, column]
                                        below_value = data_subset_filled.loc[i + 1, column]
                                        if pd.notna(above_value) and pd.notna(below_value):
                                            data_subset_filled.loc[i, column] = (above_value + below_value) / 2

                            # Plot grey lines before scatter
                            ax.plot(
                                data_subset_filled.index,
                                data_subset_filled[metric],
                                color="darkgrey",
                                linestyle="-",
                                linewidth=2,
                                zorder=1,
                            )

                            # Plot blue or red dots
                            for x, y in zip(data_subset.index, data_subset[metric]):
                                if not pd.isna(y):
                                    if prev_value is not None and y != prev_value:
                                        # next data point has different value compared to the previous one
                                        ax.scatter(x, y, color="red", zorder=2)
                                        ax.annotate(
                                            f"{y}",
                                            (x, y),
                                            textcoords="offset points",
                                            xytext=(15, 5),
                                            ha="center",
                                            color="red",
                                            rotation=60,
                                        )

                                        if prev_is_valid:
                                            # if the previous data point had the same value as the preceding one
                                            ax.annotate(
                                                f"{prev_value}",
                                                (prev_x, prev_y),
                                                textcoords="offset points",
                                                xytext=(15, 5),
                                                ha="center",
                                                color="blue",
                                                rotation=60,
                                            )
                                        prev_is_valid = False
                                    else:
                                        ax.scatter(x, y, color="blue")
                                        prev_is_valid = True

                                    prev_value = y
                                    prev_x, prev_y = x, y

                            # Set x-axis ticks and labels
                            ax.set_xticks(range(len(x_tick_labels)))
                            ax.set_xticklabels(x_tick_labels, rotation=45)

                            # Set y-axis limits and labels
                            ax.tick_params(axis="y", labelsize=8)
                            ax.set_ylim(float(y_limits[metric][0]), float(y_limits[metric][1]))
                            has_decimals = any(Decimal(str(value)) % 1 != 0 for value in data_subset[metric])
                            if has_decimals:
                                ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.3f"))
                            else:
                                ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f"))

                            if metric_idx == 0:
                                multiline_action = textwrap.fill(action, width=30)
                                ax.set_ylabel(multiline_action)

                            if action_idx == 0:
                                ax.set_title(metric)

                plt.tight_layout()
                plt.subplots_adjust(top=0.9)
                pdf.savefig(fig)
                plt.close(fig)

        return output_pdf
