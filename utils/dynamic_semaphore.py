import asyncio
import logging

from utils.logger import create_logger


class DynamicSemaphore(asyncio.Semaphore):
    def __init__(self, initial_permits: int, log_level: int = logging.INFO):
        super().__init__(initial_permits)
        self._current_permits = initial_permits
        self.logger = create_logger(name=__name__, level=log_level)

    async def set_permits(self, new_permits: int):
        self.logger.debug(f"Attempting to change permits from {self._current_permits} to {new_permits}")

        if new_permits < self._current_permits:
            await self._wait_for_permits_release(new_permits)

        difference = new_permits - self._current_permits
        self._current_permits = new_permits

        if difference > 0:
            # Increase permits
            for _ in range(difference):
                self.release()
            self.logger.debug(f"Increased permits by {difference}")
        # Decreasing permits is handled by `_wait_for_permits_release`, so no further action needed

    async def _wait_for_permits_release(self, new_permits: int):
        required_releases = self._current_permits - new_permits
        self.logger.debug(f"Waiting for {required_releases} permits to be released before reducing")

        while self._value < required_releases:
            await asyncio.sleep(0.1)  # Polling to check for available permits

        self.logger.debug(f"Sufficient permits released, reducing to {new_permits}")
