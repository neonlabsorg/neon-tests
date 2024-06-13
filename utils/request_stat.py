import json
import re
from collections import defaultdict
import pandas as pd
import statistics
from pprint import pprint


# Regular expression to match the log format
log_pattern = re.compile(r"{.*}")


def extract_method(request_body):
    try:
        request_json = json.loads(request_body)
        return request_json.get("method", "unknown")
    except json.JSONDecodeError:
        return "unknown"


def parse_log_entry(log_file_path):
    # Read and parse the log file
    stats = defaultdict(lambda: {"times": list()})
    with open(log_file_path, "r") as log_file:
        lines = (line for line in log_file)
        log_entries = (json.loads(line) for line in lines)
        formated_requests = (
            {
                "request_time": float(log_entry.get("request_time", 0)),
                "method": extract_method(log_entry.get("jsonrpc_method", "")),
            }
            for log_entry in log_entries
        )
        for formated_request in formated_requests:
            print(formated_request, "\n\n")
            method = formated_request["method"]
            # Update method data
            stats[method]["times"].append(formated_request["request_time"])
    return stats


def calculate_stats(stats):
    formated_stats = {key: {} for key in stats.keys()}
    for method, data in stats.items():
        formated_stats[method]["count"] = len(data["times"])
        formated_stats[method]["average_time"] = statistics.mean(data["times"])
        formated_stats[method]["max_time"] = max(data["times"])
        formated_stats[method]["min_time"] = min(data["times"])
        formated_stats[method]["median_time"] = statistics.median(data["times"])
        formated_stats[method]["percentile_95"] = statistics.quantiles(data["times"], n=20)[-2]
        formated_stats[method]["percentile_90"] = statistics.quantiles(data["times"], n=10)[-2]
    return formated_stats


class StatView:
    def __init__(self, data):
        self.data = data
        self.order = ["count", "min_time", "max_time", "average_time", "median_time", "percentile_90", "percentile_95"]

    def __str__(self) -> str:
        lines = [" ".join(("{:>27s}".format(key) for key in ["method"] + self.order))]
        for method, stats in self.data.items():
            line = [method]
            for key in self.order:
                line.append(str(stats.get(key, "N/A")))
            lines.append(" ".join(("{:>27s}".format(key) for key in line)))
        return "\n".join(lines)



# pprint(method_data, indent=4)
if __name__ == "__main__":
    # log_file_path = 'log.log'
    log_file = "/Users/andreineonlabs/Documents/neon-proxy.py/docker-compose/access.log"

    method_data = parse_log_entry(log_file)
    calculated_stats = calculate_stats(method_data)

    # df = pd.DataFrame.from_dict(calculated_stats, orient="index")
    # df = df.rename(
    #     columns={
    #         "count": "Number of Requests",
    #         "min_time": "Min Time(s)",
    #         "max_time": "Max Time(s)",
    #         "average_time": "AvgTime(s)",
    #         "median_time": "Median Time(s)",
    #         "percentile_90": "90th Percentile Request Time (s)",
    #         "percentile_95": "95th Percentile Request Time (s)",
    #     }
    # )
    # print(df)

    df = StatView(calculated_stats)
    print(df)
