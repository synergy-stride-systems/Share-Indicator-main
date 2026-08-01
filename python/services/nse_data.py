"""
NSEDataService (slim / hybrid version)
=======================================

yfinance remains the source for OHLCV price history and the
NIFTY 50 index change (both reliable, well-tested libraries).

NSE's own (unofficial, undocumented) JSON API is used ONLY for the
two things yfinance can't provide:

  1. Delivery % / delivery-qty day-over-day change -> historical/cm/equity
  2. F&O Open Interest % change                     -> quote-derivative

Keeping NSE's footprint small and isolated to these two fields means
that if NSE blocks us, changes its response shape, or is just down,
only `delivery_percentage` / `delivery_change` / `oi_change` come
back as None (which ShortCoveringStrategy already handles as
"data unavailable") -- price data, indicators, and everything else
keep working normally.

CAVEATS (please read before deploying):

- NOT an official/documented API. Field names can change without
  notice. `_first()` tries several plausible key names per field so
  a minor rename degrades to None instead of crashing, but a bigger
  shape change will still need an update here.

- NSE requires "warm-up" cookies (GET the homepage before hitting
  /api/ endpoints) and those cookies expire after a few minutes.
  `_request()` handles warm-up and retries once on 401/403.

- NSE's WAF blocks a lot of non-browser traffic on TLS/HTTP
  fingerprint. `curl_cffi` (already in requirements.txt) is used to
  impersonate a real Chrome client where available, falling back to
  plain `requests` otherwise -- but no client-side trick guarantees
  NSE won't block you.

- NSE rate-limits aggressively. A `threading.Semaphore` caps how
  many NSE requests this process allows in flight at once,
  independent of ScannerEngine's `max_workers`.

- This has not been tested against a live NSE response in this
  environment (nseindia.com isn't reachable from this sandbox's
  network allowlist). Treat it as a strong first draft.
"""

import time
import threading
from datetime import datetime, timedelta

try:
    # Preferred: bypasses NSE's TLS/browser fingerprint blocking.
    from curl_cffi import requests as http
    _USING_CURL_CFFI = True
except ImportError:
    import requests as http
    _USING_CURL_CFFI = False

import pandas as pd


NSE_BASE = "https://www.nseindia.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.nseindia.com/",
}

# How many NSE requests this process allows in flight at once,
# regardless of how many scanner worker threads are running.
MAX_CONCURRENT_NSE_REQUESTS = 1

# Re-warm cookies if they're older than this.
COOKIE_TTL_SECONDS = 240

# Small lookback just to get 2+ days of delivery data - deliberately
# short since this is the only thing NSE is being asked for here.
DELIVERY_LOOKBACK_DAYS = 10


def strip_yf_suffix(symbol):
    """
    'RELIANCE.NS' -> 'RELIANCE'
    NSE's own API wants the bare symbol, not the yfinance-style
    '.NS' suffixed ticker.
    """
    if symbol.upper().endswith(".NS"):
        return symbol[:-3]
    return symbol


def _first(d, *keys, default=None):
    """
    Return the first present, non-None value among several
    candidate key names. Guards against NSE field-name drift
    causing a hard crash instead of a graceful None.
    """
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


class NSEDataService:

    def __init__(self):
        self._session = None
        self._cookie_time = None
        self._lock = threading.Lock()
        self._nse_semaphore = threading.Semaphore(
            MAX_CONCURRENT_NSE_REQUESTS
        )

    # --------------------------------------------------
    # SESSION / COOKIE HANDLING
    # --------------------------------------------------

    def _cookies_stale(self):

        if self._session is None or self._cookie_time is None:
            return True

        return (time.time() - self._cookie_time) > COOKIE_TTL_SECONDS

    def _warm_up(self):

        with self._lock:

            if not self._cookies_stale():
                return

            session = http.Session()
            session.headers.update(HEADERS)

            session.get(NSE_BASE, timeout=10)

            try:
                session.get(
                    f"{NSE_BASE}/market-data/live-equity-market",
                    timeout=10
                )
            except Exception:
                pass

            self._session = session
            self._cookie_time = time.time()

    def _request(self, path, params=None, retries=1):

        self._warm_up()

        url = f"{NSE_BASE}{path}"

        with self._nse_semaphore:
            time.sleep(0.5)

            try:
                resp = self._session.get(
                    url, params=params, timeout=10
                )
            except Exception as e:
                print(f"NSE request error ({path}): {e}")
                return None

            if resp.status_code in (401, 403) and retries > 0:

                self._cookie_time = None
                self._warm_up()

                return self._request(
                    path, params=params, retries=retries - 1
                )

            if resp.status_code != 200:
                print(
                    f"NSE request failed ({path}): "
                    f"HTTP {resp.status_code}"
                )
                return None

            try:
                return resp.json()
            except Exception as e:
                print(f"NSE response not JSON ({path}): {e}")
                return None

    # --------------------------------------------------
    # DELIVERY % / DELIVERY CHANGE
    # --------------------------------------------------

    def get_delivery_data(self, symbol):
        """
        Returns {"delivery_percentage": float|None,
                 "delivery_change": float|None}

        delivery_percentage = today's delivered-qty / traded-qty %
        delivery_change     = % change in delivery_percentage vs
                               the previous trading day
        """

        bare_symbol = strip_yf_suffix(symbol)

        end = datetime.today()
        start = end - timedelta(days=DELIVERY_LOOKBACK_DAYS)

        params = {
            "symbol": bare_symbol,
            "series": '["EQ"]',
            "from": start.strftime("%d-%m-%Y"),
            "to": end.strftime("%d-%m-%Y"),
        }

        payload = self._request(
            "/api/historical/cm/equity", params=params
        )

        if not payload or not payload.get("data"):
            return {"delivery_percentage": None, "delivery_change": None}

        rows = []

        for rec in payload["data"]:

            date_str = _first(
                rec, "CH_TIMESTAMP", "TIMESTAMP", "mTIMESTAMP"
            )
            deliv_pct = _first(
                rec, "COP_DELIV_PERC", "DeliveryPercent"
            )

            if date_str is None or deliv_pct is None:
                continue

            rows.append({
                "date": pd.to_datetime(date_str),
                "delivery_percent": float(deliv_pct),
            })

        if len(rows) < 2:
            return {"delivery_percentage": None, "delivery_change": None}

        df = pd.DataFrame(rows).sort_values("date")

        curr_pct = df["delivery_percent"].iloc[-1]
        prev_pct = df["delivery_percent"].iloc[-2]

        delivery_change = None

        if prev_pct not in (0, None):
            delivery_change = round(
                ((curr_pct - prev_pct) / prev_pct) * 100, 2
            )

        return {
            "delivery_percentage": round(curr_pct, 2),
            "delivery_change": delivery_change,
        }

    # --------------------------------------------------
    # F&O OPEN INTEREST
    # --------------------------------------------------

    def get_oi_change(self, symbol):
        """
        Returns the % change in Open Interest for the nearest-expiry
        stock future, or None if unavailable/not parseable.
        """

        bare_symbol = strip_yf_suffix(symbol)

        payload = self._request(
            "/api/quote-derivative", params={"symbol": bare_symbol}
        )

        if not payload:
            return None

        stocks = payload.get("stocks") or []

        if not stocks:
            return None

        # Contracts are typically nearest-expiry first; take the
        # first futures contract entry. Worth confirming against a
        # live response for your actual symbols.
        metadata = stocks[0].get("metadata", {})

        open_interest = _first(metadata, "openInterest", "openInt")
        change_in_oi = _first(
            metadata, "changeinOpenInterest", "changeInOpenInterest"
        )

        if open_interest is None or change_in_oi is None:
            return None

        previous_oi = open_interest - change_in_oi

        if previous_oi == 0:
            return None

        return round((change_in_oi / previous_oi) * 100, 2)