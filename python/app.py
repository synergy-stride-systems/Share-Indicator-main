from flask import Flask, Response, request, stream_with_context
from flask_cors import CORS

import os
import json
import queue
import threading
import logging

import pandas as pd
from datetime import datetime

from engines.scanner_engine import ScannerEngine

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "http://localhost:3000",
                "https://synergyapp-frontend-f9bxarh2ehbycuhh.canadacentral-01.azurewebsites.net"
            ]
        }
    }
)

# ============================================================
# LOGGING
# ============================================================

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
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s %(message)s"
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)


# ============================================================
# LOAD SYMBOLS
# ============================================================

file_path = os.path.join(BASE_DIR, "fno_list.txt")

with open(file_path) as f:

    SYMBOLS = [

        line.strip()

        for line in f

        if line.strip()

    ]


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(results):

    if not results:

        return None

    df = pd.DataFrame(results)

    df.sort_values(

        by="percent_gain",

        ascending=False,

        inplace=True

    )

    filename = f"Buy_signals_{datetime.now():%Y-%m-%d_%H-%M-%S}.txt"

    filepath = os.path.join(

        OUTPUT_DIR,

        filename

    )

    df.to_csv(

        filepath,

        sep="\t",

        index=False,

        float_format="%.2f"

    )

    return filepath, df


# ============================================================
# RUN SCAN
# ============================================================

# ============================================================
# RUN SCAN
# ============================================================

def run_scan(q, conditions):

    scanner = ScannerEngine(SYMBOLS)

    def progress_callback(current, total, symbol):

        q.put({
            "type": "progress",
            "current": current,
            "total": total,
            "symbol": symbol
        })

    # Run Scanner
    results = scanner.scan(
        conditions,
        progress_callback=progress_callback
    )

    # Send Results
    for stock in results:

        q.put({
            "type": "result",
            "data": stock
        })

    # Save Results
    if results:

        saved = save_results(results)

        if saved:

            filepath, df = saved

            max_row = df.loc[df["percent_gain"].idxmax()]
            min_row = df.loc[df["percent_gain"].idxmin()]

            q.put({
                "type": "summary",
                "total_scanned": len(SYMBOLS),
                "total_signals": len(results),
                "max_gain": round(float(max_row["percent_gain"]), 2),
                "max_gain_symbol": max_row["symbol"],
                "min_gain": round(float(min_row["percent_gain"]), 2),
                "min_gain_symbol": min_row["symbol"],
                "output_file": filepath
            })

    else:

        q.put({
            "type": "summary",
            "total_scanned": len(SYMBOLS),
            "total_signals": 0,
            "message": "No BUY signals detected."
        })

    q.put({
        "type": "stop"
    })



# ============================================================
# SSE ROUTE
# ============================================================

@app.route("/scan")

def scan():

    q = queue.Queue()

    conditions = request.args.get(

        "conditions",

        "[]"

    )

    try:

        conditions = json.loads(conditions)

    except Exception:

        conditions = []

    def generate():

        thread = threading.Thread(

            target=run_scan,

            args=(q, conditions),

            daemon=True

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

            "X-Accel-Buffering": "no"

        }

    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")

def health():

    return {

        "status": "running",

        "symbols": len(SYMBOLS)

    }


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(

        debug=True,

        port=5000

    )