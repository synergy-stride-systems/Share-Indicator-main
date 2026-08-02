
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import { apiUrl, scanUrl } from "../../lib/api";

interface StockResult {
  symbol: string;
  market_date?: string;
  percent_gain?: number;
  curr_close?: number;
  curr_volume?: number;
  price_change?: number;
  volume_change?: number;
  rsi?: number;
  trend?: string;
  score?: number;
  market_structure?: string;
  signal?: string;
  confidence?: number;
  risk?: string;
  entry?: number;
  stoploss?: number;
  target?: number;
  oi_change?: number | null;
  oi_status?: string;
  strategy?: string;
}

interface Summary {
  total_scanned: number;
  total_signals: number;
  max_gain?: number;
  max_gain_symbol?: string;
  min_gain?: number;
  min_gain_symbol?: string;
  message?: string;
}

interface Condition {
  id: number;
  enabled: boolean;
  lhs: string;
  op: string;
  rhs: string | number;
}

const dash = "—";

function numberText(value: number | null | undefined, digits = 2) {
  return value === null || value === undefined ? dash : value.toFixed(digits);
}

export default function Dashboard() {
  const router = useRouter();
  const eventSourceRef = useRef<EventSource | null>(null);

  const [results, setResults] = useState<StockResult[]>([]);
  const [scannerMode, setScannerMode] = useState<"condition" | "strategy">("condition");
  const [selectedStrategy, setSelectedStrategy] = useState("Short Covering");
  const [minimumScore, setMinimumScore] = useState(70);
  const [scanning, setScanning] = useState(false);
  const [currentSymbol, setCurrentSymbol] = useState("");
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [summary, setSummary] = useState<Summary | null>(null);
  const [log, setLog] = useState<string[]>([]);

  useEffect(() => {
    if (!localStorage.getItem("token")) router.push("/");

    return () => eventSourceRef.current?.close();
  }, [router]);

  const addLog = (message: string) => {
    setLog((previous) => [...previous, message]);
  };

  const startScan = async () => {
    try {
      setResults([]);
      setSummary(null);
      setLog([]);
      setProgress({ current: 0, total: 0 });
      setCurrentSymbol("");
      setScanning(true);

      let conditions: Condition[] = [];

      if (scannerMode === "condition") {
        const user = JSON.parse(localStorage.getItem("user") || "{}");

        if (!user.id) {
          alert("User not found. Please sign in again.");
          setScanning(false);
          return;
        }

        const response = await fetch(apiUrl(`/api/strategy/get/${user.id}`));

        if (!response.ok) {
          throw new Error("Could not load scanner conditions");
        }

        const data = await response.json();

        conditions = (data.conditions || []).filter(
          (condition: Condition) => condition.enabled,
        );

        addLog(
          `Condition scanner started with ${conditions.length} condition(s).`,
        );
      } else {
        addLog(`${selectedStrategy} strategy scanner started.`);
        addLog(`Minimum score: ${minimumScore}`);
      }

      const query = new URLSearchParams({
        mode: scannerMode,
        strategy: selectedStrategy,
        minimumScore: String(minimumScore),
        conditions: JSON.stringify(conditions),
      });

      const eventSource = new EventSource(
        scanUrl(`/scan?${query.toString()}`),
      );

      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        try {
          const message = JSON.parse(
            event.data.replace(/\bNaN\b/g, "null"),
          );

          if (message.type === "progress") {
            setCurrentSymbol(message.symbol || "");
            setProgress({
              current: message.current || 0,
              total: message.total || 0,
            });

            addLog(`Scanning ${message.symbol}`);
          }

          if (message.type === "result") {
            setResults((previous) =>
              [...previous, message.data].sort((first, second) => {
                if (scannerMode === "strategy") {
                  return (second.score || 0) - (first.score || 0);
                }

                return (
                  (second.percent_gain || 0) -
                  (first.percent_gain || 0)
                );
              }),
            );

            addLog(`✓ Signal found: ${message.data.symbol}`);
          }

          if (message.type === "summary") {
            setSummary(message);

            if (message.message) {
              addLog(message.message);
            }
          }

          if (message.type === "stop") {
            setScanning(false);
            eventSource.close();
            addLog("Scan completed.");
          }
        } catch {
          addLog("Could not read a scanner update.");
        }
      };

      eventSource.onerror = () => {
        setScanning(false);
        eventSource.close();
        addLog("Scanner connection lost.");
      };
    } catch (error) {
      console.error(error);
      setScanning(false);
      addLog("Could not start the scan.");
    }
  };

  const stopScan = () => {
    eventSourceRef.current?.close();
    setScanning(false);
    addLog("Scan display stopped by user.");
  };

  const progressPercent =
    progress.total > 0
      ? Math.round((progress.current / progress.total) * 100)
      : 0;

  return (
    <>
      <Header />

      <main className="min-h-screen bg-gray-100 p-8 font-mono text-gray-900">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-xl font-bold uppercase tracking-widest">
            Share Indicator
          </h1>
        </div>

        <section className="mb-6 rounded-lg border bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-bold">
            Scanner Configuration
          </h2>

          <div className="flex flex-wrap gap-8">
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="radio"
                checked={scannerMode === "condition"}
                onChange={() => setScannerMode("condition")}
              />
              Condition Scanner
            </label>

            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="radio"
                checked={scannerMode === "strategy"}
                onChange={() => setScannerMode("strategy")}
              />
              Strategy Scanner
            </label>
          </div>

          {scannerMode === "strategy" && (
            <div className="mt-5 flex flex-wrap gap-4">
              <select
                className="rounded border px-3 py-2"
                value={selectedStrategy}
                onChange={(event) =>
                  setSelectedStrategy(event.target.value)
                }
              >
                <option>All Strategies</option>
                <option>Short Covering</option>
                <option>Long Build-up</option>
                <option>Short Build-up</option>
                <option>Long Unwinding</option>
                <option>Breakout with Volume</option>
                <option>Breakdown with Volume</option>
                <option>VWAP Momentum</option>
                <option>EMA 20/50 Crossover</option>
                <option>RSI Reversal</option>
                <option>Bollinger Band Breakout</option>
              </select>

              <label className="flex items-center gap-2 text-sm">
                Minimum score

                <input
                  type="number"
                  min="0"
                  max="100"
                  value={minimumScore}
                  onChange={(event) =>
                    setMinimumScore(Number(event.target.value))
                  }
                  className="w-24 rounded border px-3 py-2"
                />
              </label>
            </div>
          )}
        </section>

        <div className="mb-6 flex gap-3">
          <button
            onClick={startScan}
            disabled={scanning}
            className="rounded bg-emerald-600 px-5 py-2 text-sm text-white transition-colors hover:bg-emerald-500 disabled:opacity-40"
          >
            {scanning ? "Scanning..." : "Start Scan"}
          </button>

          <button
            onClick={stopScan}
            disabled={!scanning}
            className="rounded bg-red-500 px-5 py-2 text-sm text-white transition-colors hover:bg-red-400 disabled:opacity-40"
          >
            Stop
          </button>
        </div>

        {scanning && (
          <section className="mb-6">
            <div className="mb-1 flex justify-between text-xs text-gray-400">
              <span>{currentSymbol}</span>
              <span>
                {progress.current}/{progress.total} — {progressPercent}%
              </span>
            </div>

            <div className="h-1.5 w-full rounded bg-gray-200">
              <div
                className="h-1.5 rounded bg-emerald-500 transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </section>
        )}

        {summary && (
          <section className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatCard label="Scanned" value={summary.total_scanned} />
            <StatCard label="Signals" value={summary.total_signals} />

            <StatCard
              label="Best gain"
              value={
                summary.max_gain_symbol
                  ? `${summary.max_gain_symbol} +${numberText(summary.max_gain)}%`
                  : dash
              }
            />

            <StatCard
              label="Lowest gain"
              value={
                summary.min_gain_symbol
                  ? `${summary.min_gain_symbol} ${numberText(summary.min_gain)}%`
                  : dash
              }
            />
          </section>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section>
            <h2 className="mb-3 text-sm uppercase tracking-widest text-gray-800">
              {scannerMode === "strategy"
                ? `${selectedStrategy} Signals`
                : "Buy Signals"}{" "}
              ({results.length})
            </h2>

            {results.length === 0 ? (
              <p className="text-sm text-gray-400">No signals yet.</p>
            ) : (
              <div className="overflow-x-auto">
                {scannerMode === "strategy" ? (
                  <StrategyTable results={results} />
                ) : (
                  <ConditionTable results={results} />
                )}
              </div>
            )}
          </section>

          <section>
            <h2 className="mb-3 text-xs uppercase tracking-widest text-gray-800">
              Live Log
            </h2>

            <div className="h-80 overflow-y-auto rounded border border-gray-200 bg-white p-3 text-xs leading-relaxed text-gray-500 shadow-sm">
              {log.length === 0 && (
                <span className="text-gray-600">Waiting for scan...</span>
              )}

              {log.map((line, index) => (
                <div
                  key={`${line}-${index}`}
                  className={
                    line.startsWith("✓") ? "text-emerald-600" : ""
                  }
                >
                  {line}
                </div>
              ))}
            </div>
          </section>
        </div>
      </main>

      <Footer />
    </>
  );
}

function StatCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded border border-gray-200 bg-white p-3 shadow-sm">
      <p className="text-xs uppercase tracking-wider text-gray-400">
        {label}
      </p>

      <p className="mt-0.5 text-lg text-gray-900">{value}</p>
    </div>
  );
}

function StrategyTable({ results }: { results: StockResult[] }) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-gray-200 text-xs uppercase tracking-wider text-gray-700">
          <th className="py-2 pr-4 text-left">Symbol</th>
          <th className="py-2 pr-4 text-left">Market Date</th>
          <th className="py-2 pr-4 text-right">Score</th>
          <th className="py-2 pr-4 text-left">Setup</th>
          <th className="py-2 pr-4 text-right">Confidence</th>
          <th className="py-2 pr-4 text-right">Entry</th>
          <th className="py-2 pr-4 text-right">Stop Loss</th>
          <th className="py-2 pr-4 text-right">Target</th>
          <th className="py-2 text-right">OI Change</th>
          <th className="py-2 pl-4 text-left">OI Status</th>
        </tr>
      </thead>

      <tbody>
        {results.map((result) => (
          <tr
            key={`${result.symbol}-${result.strategy ?? result.market_structure}`}
            className="border-b border-gray-100 transition-colors hover:bg-gray-100"
          >
            <td className="py-2 pr-4 font-bold text-gray-900">
              {result.symbol}
            </td>

            <td className="py-2 pr-4 text-xs text-gray-500">
              {result.market_date ?? dash}
            </td>

            <td className="py-2 pr-4 text-right text-emerald-600">
              {result.score ?? dash}
            </td>

            <td className="py-2 pr-4 text-gray-700">
              {result.market_structure
                ? `${result.market_structure} (${result.signal ?? dash})`
                : result.signal ?? dash}
            </td>

            <td className="py-2 pr-4 text-right text-gray-700">
              {result.confidence === undefined
                ? dash
                : `${result.confidence}%`}
            </td>

            <td className="py-2 pr-4 text-right text-gray-700">
              {numberText(result.entry)}
            </td>

            <td className="py-2 pr-4 text-right text-red-500">
              {numberText(result.stoploss)}
            </td>

            <td className="py-2 pr-4 text-right text-emerald-600">
              {numberText(result.target)}
            </td>

            <td className="py-2 text-right text-gray-500">
              {result.oi_change === null ||
              result.oi_change === undefined
                ? dash
                : `${result.oi_change}%`}
            </td>

            <td className="py-2 pl-4 text-xs text-gray-500">
              {result.oi_status ?? dash}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ConditionTable({ results }: { results: StockResult[] }) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-gray-200 text-xs uppercase tracking-wider text-gray-700">
          <th className="py-2 pr-4 text-left">Symbol</th>
          <th className="py-2 pr-4 text-right">% Gain</th>
          <th className="py-2 pr-4 text-right">Close</th>
          <th className="py-2 pr-4 text-right">Volume</th>
          <th className="py-2 pr-4 text-right">RSI</th>
          <th className="py-2 text-right">Trend</th>
        </tr>
      </thead>

      <tbody>
        {results.map((result) => (
          <tr
            key={result.symbol}
            className="border-b border-gray-100 transition-colors hover:bg-gray-100"
          >
            <td className="py-2 pr-4 font-bold text-gray-900">
              {result.symbol}
            </td>

            <td className="py-2 pr-4 text-right text-emerald-600">
              {result.percent_gain === undefined
                ? dash
                : `+${result.percent_gain}%`}
            </td>

            <td className="py-2 pr-4 text-right text-gray-700">
              {numberText(result.curr_close)}
            </td>

            <td className="py-2 pr-4 text-right text-gray-500">
              {result.curr_volume?.toLocaleString() ?? dash}
            </td>

            <td className="py-2 pr-4 text-right text-gray-500">
              {numberText(result.rsi)}
            </td>

            <td className="py-2 text-right text-gray-500">
              {result.trend ?? dash}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
