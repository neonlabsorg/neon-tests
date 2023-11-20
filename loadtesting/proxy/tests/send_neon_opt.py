"""
Optimized suite for sending Neon messages very fast, for testing mainnet/devnet for maximum throughput.
"""
import logging
from locust import TaskSet, task


LOG = logging.getLogger(__name__)


class NeonTasksSet(TaskSet):
    def on_start(self):
        pass

    def on_stop(self):
        pass

    @task
    def task_send_neon(self):
        pass
