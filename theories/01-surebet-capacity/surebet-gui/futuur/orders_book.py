import os
import time
import hmac
import hashlib
from collections import OrderedDict
from urllib.parse import urlencode
import requests

# ----------------------- CONFIGURATION -----------------------
# Read credentials from the environment; never commit real keys.
PUBLIC_KEY = os.environ.get("FUTUUR_PUBLIC_KEY", "")
PRIVATE_KEY = os.environ.get("FUTUUR_PRIVATE_KEY", "")

# Specify the market (question) you want to query and currency mode
MARKET_ID = os.environ.get("FUTUUR_MARKET_ID", "222373")
CURRENCY_MODE = "real_money"  # "play_money" or "real_money"
OUTCOME_ID: int | None = None  # Optional outcome filter (set to an int or None)

BASE_URL = "https://api.futuur.com/api/v1/"

# ------------------------ UTILITIES -------------------------

def build_signature(params: dict, private_key: str) -> str:
    """Generate SHA-512 HMAC signature for given parameters."""
    # Sort parameters alphabetically by key – Futuur expects this.
    params_to_sign = OrderedDict(sorted(params.items()))
    encoded_params = urlencode(params_to_sign).encode("utf-8")
    encoded_key = private_key.encode("utf-8")
    return hmac.new(encoded_key, encoded_params, hashlib.sha512).hexdigest()

def build_headers(public_key: str, private_key: str, extra_params: dict | None = None) -> dict:
    """Create Futuur auth headers, including GET/POST params in HMAC."""
    timestamp = int(time.time())

    # Build full param dict for signature -> Key + Timestamp + request params
    signature_params = {
        "Key": public_key,
        "Timestamp": timestamp,
    }
    if extra_params:
        signature_params.update(extra_params)

    hmac_hex = build_signature(signature_params, private_key)
    return {
        "Key": public_key,
        "Timestamp": str(timestamp),
        "HMAC": hmac_hex,
    }

# ---------------------- API CALLS ---------------------------

def fetch_order_book(market_id: int, currency_mode: str, outcome_id: int | None = None) -> dict:
    """Retrieve aggregated order book for a given market/question."""
    endpoint = f"markets/{market_id}/order_book/"
    url = BASE_URL + endpoint

    query_params = {"currency_mode": currency_mode}
    if outcome_id is not None:
        query_params["outcome"] = outcome_id

    headers = build_headers(PUBLIC_KEY, PRIVATE_KEY, query_params)
    response = requests.get(url, headers=headers, params=query_params)
    response.raise_for_status()
    return response.json()

# ---------------------- MAIN FUNCTION -----------------------

def main():
    if not PUBLIC_KEY or not PRIVATE_KEY:
        raise SystemExit(
            "Set FUTUUR_PUBLIC_KEY and FUTUUR_PRIVATE_KEY before running this script."
        )
    try:
        data = fetch_order_book(MARKET_ID, CURRENCY_MODE, OUTCOME_ID)
        print("== Futuur Order Book ==")
        print(data)
    except requests.HTTPError as err:
        print("Request failed:", err.response.text)


if __name__ == "__main__":
    main()
