from flask import Flask, Response, request, stream_with_context
from flask_cors import CORS
import yfinance as yf
from datetime import datetime, timedelta
import json
import queue
import threading
import os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:3000",
            "https://synergyapp-frontend-f9bxarh2ehbycuhh.canadacentral-01.azurewebsites.net"
        ]
    }
})



# Load symbols
base_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(base_dir, "fno_list.txt")

with open(file_path, "r") as f:
    symbols = [line.strip() for line in f if line.strip()]

MAX_WORKERS = 10


# =========================
# CONDITION LOGIC
# =========================

def evaluate_condition(stock, cond):
    lhs = stock.get(cond["lhs"])
    rhs = stock.get(cond["rhs"])

    if lhs is None or rhs is None:
        return False

    op = cond["op"]

    if op == "<":    return lhs < rhs
    elif op == ">":  return lhs > rhs
    elif op == "<=": return lhs <= rhs
    elif op == ">=": return lhs >= rhs
    elif op == "==": return lhs == rhs

    return False


def evaluate_conditions(stock, conditions):
    if not conditions:
        return True

    groups = []
    current_group = []

    for i, cond in enumerate(conditions):
        current_group.append(cond)
        if i == len(conditions) - 1 or cond.get("conn") == "or":
            groups.append(current_group)
            current_group = []

    for group in groups:
        if all(evaluate_condition(stock, c) for c in group):
            return True

    return False


# =========================
# PROCESS SINGLE STOCK
# =========================

def process_stock(symbol, conditions):
    try:
        end_date = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=5)).strftime('%Y-%m-%d')

        # No session= — let yfinance use curl_cffi internally
        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start_date, end=end_date, auto_adjust=False)

        # Flatten MultiIndex columns if present
        if hasattr(data.columns, "levels"):
            data.columns = data.columns.get_level_values(0)

        if data.empty or len(data) < 2:
            return None

        prev = data.iloc[-2]
        curr = data.iloc[-1]

        stock_data = {
            "prev_close": float(prev["Close"]),
            "prev_low":   float(prev["Low"]),
            "curr_open":  float(curr["Open"]),
            "curr_low":   float(curr["Low"]),
            "curr_close": float(curr["Close"]),
            "volume":     int(curr["Volume"]),
        }

        if not evaluate_conditions(stock_data, conditions):
            return None

        # Fetch P/E only when conditions pass
        pe_ratio = None
        try:
            info = ticker.info
            pe_ratio = info.get("trailingPE", None)
        except Exception:
            pe_ratio = None

        percent_gain = (
            (stock_data["curr_close"] - stock_data["curr_open"])
            / stock_data["curr_open"]
        ) * 100

        return {
            "symbol":       symbol,
            "prev_close":   stock_data["prev_close"],
            "prev_low":     stock_data["prev_low"],
            "curr_open":    stock_data["curr_open"],
            "curr_low":     stock_data["curr_low"],
            "curr_close":   stock_data["curr_close"],
            "volume":       stock_data["volume"],
            "percent_gain": round(percent_gain, 2),
            "pe_ratio":     pe_ratio,
        }

    except Exception as e:
        print(f"Skipping {symbol}: {e}")
        return None


# =========================
# SAVE RESULTS TO FILE
# =========================

def save_results(results):
    if not results:
        return None

    if not os.path.exists("output"):
        os.makedirs("output")

    df = pd.DataFrame(results)
    df = df.sort_values(by="percent_gain", ascending=False)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"Buy_signals_{timestamp}.txt"
    filepath = os.path.join("output", filename)

    df.to_csv(filepath, sep="\t", index=False, float_format="%.2f")
    return filepath, df


# =========================
# SCANNER (THREAD)
# =========================

def run_scan(q, conditions):
    total = len(symbols)
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_symbol = {
            executor.submit(process_stock, sym, conditions): sym
            for sym in symbols
        }

        for i, future in enumerate(as_completed(future_to_symbol)):
            symbol = future_to_symbol[future]

            q.put({
                "type":    "progress",
                "current": i + 1,
                "total":   total,
                "symbol":  symbol,
            })

            try:
                result = future.result()
            except Exception as e:
                print(f"Thread error for {symbol}: {e}")
                result = None

            if result:
                results.append(result)
                q.put({
                    "type": "result",
                    "data": result
                })

    # Summary + file save
    if results:
        saved = save_results(results)
        if saved:
            filepath, df = saved
            max_row = df.loc[df["percent_gain"].idxmax()]
            min_row = df.loc[df["percent_gain"].idxmin()]

            q.put({
                "type":            "summary",
                "total_scanned":   total,
                "total_signals":   len(results),
                "max_gain":        round(float(max_row["percent_gain"]), 2),
                "max_gain_symbol": max_row["symbol"],
                "min_gain":        round(float(min_row["percent_gain"]), 2),
                "min_gain_symbol": min_row["symbol"],
                "output_file":     filepath,
            })
    else:
        q.put({
            "type":          "summary",
            "total_scanned": total,
            "total_signals": 0,
            "message":       "No BUY signals detected.",
        })

    q.put({"type": "stop"})


# =========================
# SCAN ENDPOINT (SSE)
# =========================

@app.route("/scan")
def scan():
    q = queue.Queue()

    conditions_param = request.args.get("conditions", "[]")
    try:
        conditions = json.loads(conditions_param)
    except Exception:
        conditions = []

    def generate():
        thread = threading.Thread(target=run_scan, args=(q, conditions), daemon=True)
        thread.start()

        while True:
            msg = q.get()
            yield f"data: {json.dumps(msg)}\n\n"
            if msg["type"] == "stop":
                break

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


# =========================
# DEBUG ROUTE
# =========================

@app.route("/debug/<symbol>")
def debug(symbol):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=5)).strftime('%Y-%m-%d')

    ticker = yf.Ticker(symbol)
    data = ticker.history(start=start_date, end=end_date, auto_adjust=False)

    if len(data) < 2:
        return {"error": "Not enough data"}

    prev = data.tail(2).iloc[0]
    curr = data.tail(2).iloc[1]

    return {
        "prev_close": float(prev['Close']),
        "prev_low":   float(prev['Low']),
        "curr_open":  float(curr['Open']),
        "curr_low":   float(curr['Low']),
        "curr_close": float(curr['Close']),
    }


# =========================
# RUN SERVER
# =========================

if __name__ == "__main__":
    app.run(debug=True, port=5000)