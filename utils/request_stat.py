import json
import re
from collections import defaultdict
import statistics





# # pprint(method_data, indent=4)
# if __name__ == "__main__":
#     # log_file_path = 'log.log'
#     log_file = "/Users/andreineonlabs/Documents/neon-proxy.py/docker-compose/access.log"

#     method_data = parse_log_file(log_file)
#     calculated_stats = calculate_stats(method_data)

#     # df = pd.DataFrame.from_dict(calculated_stats, orient="index")
#     # df = df.rename(
#     #     columns={
#     #         "count": "Number of Requests",
#     #         "min_time": "Min Time(s)",
#     #         "max_time": "Max Time(s)",
#     #         "average_time": "AvgTime(s)",
#     #         "median_time": "Median Time(s)",
#     #         "percentile_90": "90th Percentile Request Time (s)",
#     #         "percentile_95": "95th Percentile Request Time (s)",
#     #     }
#     # )
#     # print(df)

#     df = StatView(calculated_stats)
#     print(df)
