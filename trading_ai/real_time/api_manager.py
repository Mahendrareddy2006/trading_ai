import time
import requests
from binance.exceptions import BinanceAPIException, BinanceRequestException
from trading_ai.real_time.logger import log_error, log_warning, log_info

MAX_RETRIES = 5
BASE_DELAY = 1  # seconds

def safe_api_call(func, *args, **kwargs):
    """
    Wrap any Binance API call with retry & backoff.
    """

    retries = 0

    while retries < MAX_RETRIES:
        try:
            return func(*args, **kwargs)

        except BinanceAPIException as e:
            # Rate limit
            if e.code == -1003:
                wait_time = BASE_DELAY * (2 ** retries)
                log_warning(f"Rate limit hit. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                log_error(f"Binance API Error: {e}")
                time.sleep(BASE_DELAY)

        except BinanceRequestException as e:
            log_warning(f"Network error: {e}")
            time.sleep(BASE_DELAY * (2 ** retries))

        except requests.exceptions.RequestException as e:
            log_warning(f"Request error: {e}")
            time.sleep(BASE_DELAY * (2 ** retries))

        except Exception as e:
            log_error(f"Unexpected API error: {e}")
            time.sleep(BASE_DELAY)

        retries += 1

    log_error("Max retries exceeded.")
    return None