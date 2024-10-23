from typing import Optional

from datetime import datetime

import requests
from requests import RequestException
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from utils.logger import create_logger


logger = create_logger(__name__)


class RateLimitError(Exception):
    pass


@retry(
    retry=retry_if_exception_type((RateLimitError, RequestException)), wait=wait_fixed(15), stop=stop_after_attempt(5))
def get_coin_price(date: datetime, coin_id: str, currency: str) -> Optional[float]:
    """
    https://docs.coingecko.com/reference/coins-id-history
    """
    formatted_date = date.strftime('%d-%m-%Y')
    url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/history?date={formatted_date}&localization=false'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        try:
            price = data['market_data']['current_price'][currency]
            return price
        except KeyError:
            logger.error(f"No price data available for {formatted_date}.")
            return None

    elif response.status_code == 429:
        logger.warning(f"Rate limit hit. Retrying in 15 seconds")
        raise RateLimitError()

    else:
        logger.error(f"Failed to retrieve data (Status Code: {response.status_code})")
        return None
