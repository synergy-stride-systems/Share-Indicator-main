"""
NSEDataService (slim / hybrid version)
=======================================

yfinance remains the source for OHLCV price history and the
NIFTY 50 index change (both reliable, well-tested libraries).

NSE's public daily bhavcopy archives are used ONLY for the two things
yfinance can't provide:

  1. Delivery % / delivery-qty day-over-day change -> CM bhavcopy
  2. F&O Open Interest % change                     -> F&O bhavcopy

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

- NSE's website API endpoints are unofficial and change without notice.
  In particular, /api/quote-derivative returned 404 and
  /api/historical/cm/equity returned 503 in the deployed scanner, so this
  module uses daily archive files instead of making an API call per symbol.

- NSE's WAF blocks a lot of non-browser traffic on TLS/HTTP
  fingerprint. `curl_cffi` (already in requirements.txt) is used to
  impersonate a real Chrome client where available, falling back to
  plain `requests` otherwise -- but no client-side trick guarantees
  NSE won't block you.

- NSE rate-limits aggressively. A `threading.Semaphore` caps how many
  archive requests this process allows in flight at once, independent of
  ScannerEngine's `max_workers`. Results are cached by date.

- This has not been tested against a live NSE response in this
  environment (nseindia.com isn't reachable from this sandbox's
  network allowlist). Treat it as a strong first draft.
"""

import os
import time
import threading
from io import BytesIO
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
NSE_ARCHIVES = "https://nsearchives.nseindia.com"
FNO_MARKET_LOTS_URL = f"{NSE_ARCHIVES}/content/fo/fo_mktlots.csv"

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

# Small lookback just to get 2+ trading days of delivery data.
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


def _as_trade_date(value=None):
    """Normalize a yfinance/Pandas timestamp to the NSE archive date."""
    if value is None:
        return datetime.today().date()
    if hasattr(value, "date"):
        return value.date()
    return pd.Timestamp(value).date()


class NSEDataService:

    def __init__(self):
        self._session = None
        self._cookie_time = None
        self._lock = threading.Lock()
        self._nse_semaphore = threading.Semaphore(
            MAX_CONCURRENT_NSE_REQUESTS
        )
        self._delivery_cache = {}
        self._fo_bhavcopy_cache = {}
        self._archive_lock = threading.Lock()
        self._fno_symbols_cache = None
        self._fno_symbols_cache_date = None

    # --------------------------------------------------
    # CURRENT F&O STOCK UNIVERSE
    # --------------------------------------------------

    import os

    def get_fno_symbols(self):
        today = datetime.today().date()

        if (
            self._fno_symbols_cache is not None
            and self._fno_symbols_cache_date == today
        ):
            return self._fno_symbols_cache

        file_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
            "fno_list.txt"
        )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                symbols = [
                    line.strip().upper()
                    for line in f
                    if line.strip()
             ]

            self._fno_symbols_cache = symbols
            self._fno_symbols_cache_date = today

            return symbols

        except Exception as e:
            print(f"Unable to load fno_list.txt: {e}")
            return []
    
    

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

            # Warming the session helps with the public web API, but it is
            # optional for the archive host.  Do not let a failed warm-up
            # discard price/indicator data for an entire symbol.
            try:
                session.get(NSE_BASE, timeout=10)
            except Exception as e:
                print(f"NSE session warm-up failed: {e}")

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

        # Retry in a loop, rather than recursively.  The old implementation
        # retried while holding this non-reentrant semaphore and could hang
        # forever after a 401/403 response.
        for attempt in range(retries + 1):
            with self._nse_semaphore:
                time.sleep(0.5)
                try:
                    resp = self._session.get(url, params=params, timeout=10)
                except Exception as e:
                    print(f"NSE request error ({path}): {e}")
                    return None

            if resp.status_code == 200:
                try:
                    return resp.json()
                except Exception as e:
                    print(f"NSE response not JSON ({path}): {e}")
                    return None

            if resp.status_code in (401, 403) and attempt < retries:
                self._cookie_time = None
                self._warm_up()
                continue

            print(f"NSE request failed ({path}): HTTP {resp.status_code}")
            return None

        return None

    # --------------------------------------------------
    # DAILY BHAVCOPY ARCHIVES
    # --------------------------------------------------

    def _archive_get(self, path):
        """Fetch a public NSE archive file without using retired web APIs."""

        self._warm_up()
        url = f"{NSE_ARCHIVES}{path}"

        with self._nse_semaphore:
            time.sleep(0.5)
            try:
                resp = self._session.get(url, timeout=15)
            except Exception as e:
                print(f"NSE archive request error ({path}): {e}")
                return None

        if resp.status_code == 404:
            # Weekends, holidays, and a file not yet published are expected.
            return None
        if resp.status_code != 200:
            print(f"NSE archive request failed ({path}): HTTP {resp.status_code}")
            return None
        return resp.content

    @staticmethod
    def _column(frame, *names):
        """Return the first matching column, tolerating NSE schema casing."""

        columns = {str(column).strip().upper(): column for column in frame.columns}
        for name in names:
            column = columns.get(name.upper())
            if column is not None:
                return frame[column]
        return None

    def _delivery_for_date(self, date):
        """Read delivery data from the daily CM bhavcopy, cached by date."""

        key = date.strftime("%Y%m%d")
        with self._archive_lock:
            if key in self._delivery_cache:
                return self._delivery_cache[key]

            content = self._archive_get(
                f"/products/content/sec_bhavdata_full_{key}.csv"
            )
            if content is None:
                self._delivery_cache[key] = None
                return None

            try:
                frame = pd.read_csv(BytesIO(content))
            except Exception as e:
                print(f"Could not parse CM bhavcopy for {key}: {e}")
                self._delivery_cache[key] = None
                return None

            self._delivery_cache[key] = frame
            return frame

    def _fo_bhavcopy_for_date(self, date):
        """Read the daily F&O bhavcopy, cached so a scan downloads it once."""

        key = date.strftime("%d%b%Y").upper()
        with self._archive_lock:
            if key in self._fo_bhavcopy_cache:
                return self._fo_bhavcopy_cache[key]

            content = self._archive_get(f"/content/fo/fo{key}bhav.csv.zip")
            if content is None:
                self._fo_bhavcopy_cache[key] = None
                return None

            try:
                frame = pd.read_csv(BytesIO(content), compression="zip")
            except Exception as e:
                print(f"Could not parse F&O bhavcopy for {key}: {e}")
                self._fo_bhavcopy_cache[key] = None
                return None

            self._fo_bhavcopy_cache[key] = frame
            return frame

    # --------------------------------------------------
    # DELIVERY % / DELIVERY CHANGE
    # --------------------------------------------------

    def warm_archives(self, as_of_date=None):
        """
        Pre-fetch today's CM and F&O bhavcopy archives once, sequentially,
        before a scan's worker threads start.

        Every symbol scanned on a given day needs the *same* date's
        archive files, and both are cached by date -- but without this,
        the first several symbols to reach get_delivery_data /
        get_oi_data all queue up behind the single-slot NSE semaphore
        while each independently walks back through lookback days
        looking for a published file. Doing that walk once up front
        means worker threads hit a warm cache immediately instead of
        stalling on the semaphore.
        """
        trade_date = _as_trade_date(as_of_date)

        for offset in range(DELIVERY_LOOKBACK_DAYS):
            if self._delivery_for_date(trade_date - timedelta(days=offset)) is not None:
                break

        for offset in range(7):
            if self._fo_bhavcopy_for_date(trade_date - timedelta(days=offset)) is not None:
                break

    def get_delivery_data(self, symbol, as_of_date=None):
        """
        Returns {"delivery_percentage": float|None,
                 "delivery_change": float|None}

        delivery_percentage = today's delivered-qty / traded-qty %
        delivery_change     = % change in delivery_percentage vs
                               the previous trading day
        """

        bare_symbol = strip_yf_suffix(symbol).upper()
        trade_date = _as_trade_date(as_of_date)
        delivery_days = []

        # The old /api/historical/cm/equity endpoint is currently returning
        # 503 in production.  The daily archive is stable, has the same
        # delivery fields, and is shared by every symbol in a scan.
        for offset in range(DELIVERY_LOOKBACK_DAYS):
            date = trade_date - timedelta(days=offset)
            frame = self._delivery_for_date(date)
            if frame is None:
                continue

            symbol_column = self._column(frame, "SYMBOL", "TCKRSYMB")
            series_column = self._column(frame, "SERIES", "SCTYSRS")
            delivery_column = self._column(
                frame, "DELIV_PER", "COP_DELIV_PERC", "DELIVERY_PERCENT"
            )
            quantity_column = self._column(
                frame, "DELIV_QTY", "COP_DELIV_QTY", "DELIVERY_QUANTITY"
            )
            if symbol_column is None or delivery_column is None:
                continue

            matches = frame[symbol_column.astype(str).str.upper() == bare_symbol]
            if series_column is not None:
                matches = matches[series_column.astype(str).str.upper() == "EQ"]
            if matches.empty:
                continue

            value = pd.to_numeric(
                delivery_column.loc[matches.index].iloc[0], errors="coerce"
            )
            if pd.notna(value):
                quantity = None
                if quantity_column is not None:
                    parsed_quantity = pd.to_numeric(
                        quantity_column.loc[matches.index].iloc[0], errors="coerce"
                    )
                    if pd.notna(parsed_quantity):
                        quantity = float(parsed_quantity)
                delivery_days.append({
                    "percentage": float(value),
                    "quantity": quantity,
                })
            if len(delivery_days) == 2:
                break

        if not delivery_days:
            return {
                "delivery_percentage": None,
                "delivery_change": None,
                "delivery_quantity": None,
                "delivery_quantity_change": None,
            }

        curr_pct = delivery_days[0]["percentage"]
        prev_pct = delivery_days[1]["percentage"] if len(delivery_days) > 1 else None
        curr_qty = delivery_days[0]["quantity"]
        prev_qty = delivery_days[1]["quantity"] if len(delivery_days) > 1 else None

        delivery_change = None

        if prev_pct not in (0, None):
            delivery_change = round(
                ((curr_pct - prev_pct) / prev_pct) * 100, 2
            )

        delivery_quantity_change = None
        if curr_qty is not None and prev_qty not in (0, None):
            delivery_quantity_change = round(
                ((curr_qty - prev_qty) / prev_qty) * 100, 2
            )

        return {
            "delivery_percentage": round(curr_pct, 2),
            "delivery_change": delivery_change,
            "delivery_quantity": curr_qty,
            "delivery_quantity_change": delivery_quantity_change,
        }

    # --------------------------------------------------
    # F&O OPEN INTEREST
    # --------------------------------------------------

    @staticmethod
    def _oi_result(current_oi, change_in_oi, source):
        """Convert NSE absolute OI and OI change into a percentage change."""
        current_oi = pd.to_numeric(current_oi, errors="coerce")
        change_in_oi = pd.to_numeric(change_in_oi, errors="coerce")
        if pd.isna(current_oi) or pd.isna(change_in_oi):
            return None
        previous_oi = current_oi - change_in_oi
        if previous_oi == 0:
            return None
        return {
            "oi_change": round(float((change_in_oi / previous_oi) * 100), 2),
            "oi_status": f"Available ({source})",
        }

    def _get_live_oi_data(self, bare_symbol):
        """Fallback for when an end-of-day F&O archive is unavailable."""
        payload = self._request("/api/quote-derivative", params={"symbol": bare_symbol})
        if not payload:
            return None

        contracts = payload.get("stocks", [])
        futures = []
        for contract in contracts:
            metadata = contract.get("metadata", {})
            instrument = str(_first(metadata, "instrumentType", "instrument", default="")).upper()
            if "FUT" not in instrument and "FUTURE" not in instrument:
                continue
            expiry = pd.to_datetime(
                _first(metadata, "expiryDate", "expiry_date"), errors="coerce", dayfirst=True
            )
            futures.append((expiry, contract))

        if not futures:
            return None
        futures.sort(key=lambda item: (pd.isna(item[0]), item[0]))
        trade_info = futures[0][1].get("marketDeptOrderBook", {}).get("tradeInfo", {})
        return self._oi_result(
            _first(trade_info, "openInterest", "open_interest"),
            _first(trade_info, "changeinOpenInterest", "changeInOpenInterest", "change_in_open_interest"),
            "live NSE API",
        )

    def get_oi_data(self, symbol, as_of_date=None):
        """Return nearest-future OI change plus a dashboard-safe status."""

        bare_symbol = strip_yf_suffix(symbol).upper()
        trade_date = _as_trade_date(as_of_date)

        # /api/quote-derivative now returns HTTP 404.  The F&O bhavcopy
        # provides OPEN_INT and CHG_IN_OI for each FUTSTK contract instead.
        archive_found = False
        for offset in range(7):
            date = trade_date - timedelta(days=offset)
            frame = self._fo_bhavcopy_for_date(date)
            if frame is None:
                continue
            archive_found = True

            instrument = self._column(frame, "INSTRUMENT")
            symbols = self._column(frame, "SYMBOL")
            expiry = self._column(frame, "EXPIRY_DT", "EXPIRYDATE")
            open_interest = self._column(frame, "OPEN_INT", "OPENINTEREST")
            change_in_oi = self._column(frame, "CHG_IN_OI", "CHANGE_IN_OI")
            if any(column is None for column in (
                instrument, symbols, open_interest, change_in_oi
            )):
                continue

            contracts = frame[
                (instrument.astype(str).str.upper() == "FUTSTK")
                & (symbols.astype(str).str.upper() == bare_symbol)
            ].copy()
            if contracts.empty:
                return {"oi_change": None, "oi_status": "No FUTSTK contract found"}

            if expiry is not None:
                contracts["_expiry"] = pd.to_datetime(
                    expiry.loc[contracts.index], errors="coerce", dayfirst=True
                )
                contracts = contracts.sort_values("_expiry", na_position="last")

            contract = contracts.iloc[0]
            result = self._oi_result(
                open_interest.loc[contract.name],
                change_in_oi.loc[contract.name],
                "NSE bhavcopy",
            )
            if result:
                return result
            return {"oi_change": None, "oi_status": "OI fields unavailable in bhavcopy"}

        live_result = self._get_live_oi_data(bare_symbol)
        if live_result:
            return live_result
        if not archive_found:
            return {"oi_change": None, "oi_status": "NSE bhavcopy and live OI unavailable"}
        return {"oi_change": None, "oi_status": "F&O bhavcopy format unavailable"}

    def get_oi_change(self, symbol, as_of_date=None):
        """Backward-compatible OI-only accessor."""
        return self.get_oi_data(symbol, as_of_date=as_of_date)["oi_change"]