from flask import Flask, Response, request, stream_with_context
from flask_cors import CORS

import os
import json
import queue
import threading
import logging
from datetime import datetime

import pandas as pd

from engines.scanner_engine import ScannerEngine
from services.nse_data import NSEDataService


app = Flask(__name__)

CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "http://localhost:3000",
                "https://synergyapp-frontend-f9bxarh2ehbycuhh.canadacentral-01.azurewebsites.net",
            ]
        }
    },
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

logger = logging.getLogger("scanner")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.FileHandler(
        os.path.join(LOG_DIR, "scanner.log"),
        encoding="utf-8",
    )

    handler.setFormatter(
        logging.Formatter("%(asctime)s %(message)s"),
    )

    logger.addHandler(handler)


# Loads NSE's current F&O stock universe and caches it for the day.
fno_universe = NSEDataService()


def save_results(results, mode="condition"):
    if not results:
        return None

    df = pd.DataFrame(results)

    sort_column = (
        "score"
        if mode == "strategy" and "score" in df.columns
        else "percent_gain"
    )

    df.sort_values(
        by=sort_column,
        ascending=False,
        inplace=True,
    )

    filename_prefix = (
        "Strategy_signals"
        if mode == "strategy"
        else "Buy_signals"
    )

    filename = (
        f"{filename_prefix}_{datetime.now():%Y-%m-%d_%H-%M-%S}.txt"
    )

    filepath = os.path.join(OUTPUT_DIR, filename)

    df.to_csv(
        filepath,
        sep="\t",
        index=False,
        float_format="%.2f",
    )

    return filepath, df


def run_scan(
    q,
    conditions,
    mode="condition",
    strategy_name="Short Covering",
    minimum_score=0,
):
    symbols = fno_universe.get_fno_symbols()

    if not symbols:
        q.put({
            "type": "summary",
            "total_scanned": 0,
            "total_signals": 0,
            "message": "Could not load NSE's current F&O stock universe.",
        })

        q.put({"type": "stop"})
        return

    scanner = ScannerEngine(symbols)

    def progress_callback(current, total, symbol):
        q.put({
            "type": "progress",
            "current": current,
            "total": total,
            "symbol": symbol,
        })

    results = scanner.scan(
        conditions,
        progress_callback=progress_callback,
        mode=mode,
        strategy_name=strategy_name,
        minimum_score=minimum_score,
    )

    for stock in results:
        q.put({
            "type": "result",
            "data": stock,
        })

    if results:
        saved = save_results(results, mode=mode)

        if saved:
            filepath, df = saved

            max_row = df.loc[df["percent_gain"].idxmax()]
            min_row = df.loc[df["percent_gain"].idxmin()]

            q.put({
                "type": "summary",
                "total_scanned": len(symbols),
                "total_signals": len(results),
                "max_gain": round(
                    float(max_row["percent_gain"]),
                    2,
                ),
                "max_gain_symbol": max_row["symbol"],
                "min_gain": round(
                    float(min_row["percent_gain"]),
                    2,
                ),
                "min_gain_symbol": min_row["symbol"],
                "output_file": filepath,
            })
    else:
        q.put({
            "type": "summary",
            "total_scanned": len(symbols),
            "total_signals": 0,
            "message": (
                f"No {strategy_name if mode == 'strategy' else 'buy'} "
                "signals detected."
            ),
        })

    q.put({"type": "stop"})


@app.route("/scan")
def scan():
    q = queue.Queue()

    conditions = request.args.get("conditions", "[]")

    try:
        conditions = json.loads(conditions)
    except Exception:
        conditions = []

    mode = request.args.get("mode", "condition")
    strategy_name = request.args.get("strategy", "Short Covering")

    try:
        minimum_score = float(request.args.get("minimumScore", 0))
    except (TypeError, ValueError):
        minimum_score = 0

    def generate():
        thread = threading.Thread(
            target=run_scan,
            args=(
                q,
                conditions,
                mode,
                strategy_name,
                minimum_score,
            ),
            daemon=True,
        )

        thread.start()

        while True:
            message = q.get()

            yield f"data: {json.dumps(message)}\n\n"

            if message["type"] == "stop":
                break

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/health")
def health():
    return {
        "status": "running",
        "symbols": len(fno_universe.get_fno_symbols()),
    }


if __name__ == "__main__":
    app.run(
        debug=True,
        port=5000,
    )