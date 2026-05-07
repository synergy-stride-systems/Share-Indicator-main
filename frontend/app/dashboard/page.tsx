"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import { apiUrl, scanUrl } from "../../lib/api";

interface StockResult {
  symbol: string;
  prev_close: number;
  prev_low: number;
  curr_open: number;
  curr_low: number;
  curr_close: number;
  volume: number;
  percent_gain: number;
  pe_ratio: number | null;
}

interface Summary {
  total_scanned: number;
  total_signals: number;
  max_gain?: { symbol: string; gain: number };
  min_gain?: { symbol: string; gain: number };
}

interface Condition {
  id: number;
  enabled: boolean;
  lhs: string;
  op: string;
  rhs: string;
}

const STORAGE_KEY = "scanner_conditions";

const DEFAULT_CONDITIONS: Condition[] = [
  { id: 1, enabled: true, lhs: "curr_open",  op: "<", rhs: "prev_close" },
  { id: 2, enabled: true, lhs: "curr_open",  op: ">", rhs: "prev_low"   },
  { id: 3, enabled: true, lhs: "curr_low",   op: "<", rhs: "prev_low"   },
  { id: 4, enabled: true, lhs: "curr_close", op: ">", rhs: "prev_close" },
];

function getActiveConditions(): Condition[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed: Condition[] = JSON.parse(stored);
      return parsed.filter(c => c.enabled);
    }
  } catch {
    // fall through to default
  }
  return DEFAULT_CONDITIONS.filter(c => c.enabled);
}

export default function Dashboard() {
  const [results, setResults]             = useState<StockResult[]>([]);
  const [scanning, setScanning]           = useState(false);
  const [currentSymbol, setCurrentSymbol] = useState("");
  const [progress, setProgress]           = useState({ current: 0, total: 0 });
  const [summary, setSummary]             = useState<Summary | null>(null);
  const [log, setLog]                     = useState<string[]>([]);
  const eventSourceRef                    = useRef<EventSource | null>(null);
  const logEndRef                         = useRef<HTMLDivElement>(null);
  const router                            = useRouter();

  useEffect(() => {
    if (!localStorage.getItem("token")) router.push("/");
  }, [router]);


  const addLog = (msg: string) =>
    setLog(prev => [...prev, msg]);

  const startScan = async () => {
  try {
    setResults([]);
    setSummary(null);
    setLog([]);
    setProgress({ current: 0, total: 0 });
    setScanning(true);

    const user = JSON.parse(localStorage.getItem("user") || "{}");
    const userId = user.id;

    if (!userId) {
      alert("User not found");
      setScanning(false);
      return;
    }

    // Get conditions from backend
    const res = await fetch(apiUrl(`/api/strategy/get/${userId}`));
    const data = await res.json();

    const conditions = (data.conditions || []).filter(
      (c: any) => c.enabled
    );

    addLog(`Starting scan with ${conditions.length} condition(s)...`);

    // Start SSE connection
    const es = new EventSource(
      scanUrl(
        `/scan?conditions=${encodeURIComponent(
          JSON.stringify(conditions)
        )}`
      )
    );

    eventSourceRef.current = es;

    es.onmessage = (e) => {
      const safeData = e.data.replace(/\bNaN\b/g, "null");
      const msg = JSON.parse(safeData);

      if (msg.type === "progress") {
        setCurrentSymbol(msg.symbol || "");
        setProgress({
          current: msg.current,
          total: msg.total,
        });

        addLog(`Scanning (${msg.current}/${msg.total})`);
      }

      if (msg.type === "result") {
        setResults((prev) =>
          [...prev, msg.data].sort(
            (a, b) => b.percent_gain - a.percent_gain
          )
        );

        addLog(
          `✓ BUY: ${msg.data.symbol} +${msg.data.percent_gain}%`
        );
      }

      if (msg.type === "summary") {
        setSummary(msg.data);
      }

      if (msg.type === "stop") {
        setScanning(false);
        es.close();
        addLog("Scan complete");
      }
    };

    es.onerror = () => {
      addLog("Connection error");
      setScanning(false);
      es.close();
    };

  } catch (err) {
    console.error(err);
    setScanning(false);
    addLog("Error starting scan");
  }
};

  {/*const startScan = async () => {
    try {
      setResults([]);
      setSummary(null);
      setLog([]);
      setProgress({ current: 0, total: 0 });
      setScanning(true);

      const user = JSON.parse(localStorage.getItem("user") || "{}");
      const userId = user.id;

    if (!userId) {
      alert("User not found");
      return;
    }

    // ✅ get conditions from backend
    const res = await fetch(apiUrl(`/api/strategy/get/${userId}`));
    const data = await res.json();

    const conditions = (data.conditions || []).filter((c: any) => c.enabled);

    addLog(`Starting scan with ${conditions.length} condition(s)...`);

    // ✅ ONLY THIS (no POST, no /stream)
    const es = new EventSource(
      `${scanUrl(`/scan?conditions=${encodeURIComponent(JSON.stringify(conditions))}`)}`
    );

    eventSourceRef.current = es;

    es.onmessage = (e) => {
      const safeData = e.data.replace(/\bNaN\b/g, "null");
      const msg = JSON.parse(safeData);

      if (msg.type === "progress") {
        setCurrentSymbol(msg.symbol || "");
        setProgress({ current: msg.current, total: msg.total });
        addLog(`Scanning (${msg.current}/${msg.total})`);
      }

      const res = await fetch(`http://localhost:4000/api/strategy/get/${userId}`);
      const data = await res.json();

      const conditions = (data.conditions || []).filter((c: any) => c.enabled);

      addLog(`Starting scan with ${conditions.length} condition(s)...`);

      const es = new EventSource(
        `http://localhost:5000/scan?conditions=${encodeURIComponent(JSON.stringify(conditions))}`
      );

      eventSourceRef.current = es;

      es.onmessage = (e) => {
        const msg = JSON.parse(e.data);

        if (msg.type === "progress") {
          setCurrentSymbol(msg.symbol || "");
          setProgress({ current: msg.current, total: msg.total });
          addLog(`Scanning (${msg.current}/${msg.total})`);
        }

        if (msg.type === "result") {
          setResults(prev =>
            [...prev, msg.data].sort((a, b) => b.percent_gain - a.percent_gain)
          );
          addLog(`✓ BUY: ${msg.data.symbol} +${msg.data.percent_gain}%`);
        }

        if (msg.type === "stop") {
          setScanning(false);
          es.close();
          addLog("Scan complete");
        }
      };

      es.onerror = () => {
        addLog("Connection error");
        setScanning(false);
        es.close();
      };

    } catch (err) {
      console.error(err);
      setScanning(false);
      addLog("Error starting scan");
    }
  };*/}

  const stopScan = async () => {
    await fetch(apiUrl("/scan/stop"), { method: "POST" });
    eventSourceRef.current?.close();
    setScanning(false);
    addLog("Scan stopped by user.");
  };

  const handleLogout = () => {
    localStorage.clear();
    router.push("/");
  };

  const pct = progress.total > 0
    ? Math.round((progress.current / progress.total) * 100)
    : 0;

  return (
    <>
      <Header />
      <div className="min-h-screen bg-gray-100 text-gray-900 p-8 font-mono">

        {/* Header */}
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-xl font-bold tracking-widest uppercase text-gray-900">
            Share Indicator
          </h1>
          {/*<button
            onClick={handleLogout}
            className="text-xs text-gray-400 hover:text-red-500 transition-colors uppercase tracking-widest"
          >
            Logout
          </button>*/}
        </div>

        {/* Controls */}
        <div className="flex gap-3 mb-6">
          <button
            onClick={startScan}
            disabled={scanning}
            className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-sm rounded transition-colors"
          >
            {scanning ? "Scanning..." : "Start Scan"}
          </button>
          <button
            onClick={stopScan}
            disabled={!scanning}
            className="px-5 py-2 bg-red-500 hover:bg-red-400  text-white text-sm rounded transition-colors"
          >
            Stop
          </button>
         
        </div>

        {/* Progress bar */}
        {scanning && (
          <div className="mb-6">
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>{currentSymbol}</span>
              <span>{progress.current}/{progress.total} — {pct}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded h-1.5">
              <div
                className="bg-emerald-500 h-1.5 rounded transition-all duration-300"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        )}

        {/* Summary */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {[
              { label: "Scanned", value: summary.total_scanned },
              { label: "Signals", value: summary.total_signals },
              summary.max_gain && { label: "Best gain", value: `${summary.max_gain.symbol} +${summary.max_gain.gain}%` },
              summary.min_gain && { label: "Min gain",  value: `${summary.min_gain.symbol} +${summary.min_gain.gain}%` },
            ].filter(Boolean).map((stat: any) => (
              <div key={stat.label} className="bg-white border border-gray-200 rounded p-3 shadow-sm">
                <p className="text-xs text-gray-400 uppercase tracking-wider">{stat.label}</p>
                <p className="text-lg text-gray-900 mt-0.5">{stat.value}</p>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Results table */}
          <div>
            <h2 className="text-sm uppercase tracking-widest text-gray-800 mb-3">
              Buy Signals ({results.length})
            </h2>
            {results.length === 0 ? (
              <p className="text-gray-400 text-sm">No signals yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="text-xs text-gray-700 uppercase tracking-wider border-b border-gray-200">
                      <th className="text-left py-2 pr-4">Symbol</th>
                      <th className="text-right py-2 pr-4">% Gain</th>
                      <th className="text-right py-2 pr-4">Close</th>
                      <th className="text-right py-2 pr-4">Volume</th>
                      <th className="text-right py-2">P/E</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r, i) => (
                      <tr key={i} className="border-b border-gray-100 hover:bg-gray-100 transition-colors">
                        <td className="py-2 pr-4 text-gray-900 font-bold">{r.symbol}</td>
                        <td className="py-2 pr-4 text-right text-emerald-600">+{r.percent_gain}%</td>
                        <td className="py-2 pr-4 text-right text-gray-700">{r.curr_close}</td>
                        <td className="py-2 pr-4 text-right text-gray-500">{r.volume?.toLocaleString()}</td>
                        <td className="py-2 text-right text-gray-400">{r.pe_ratio ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Live log */}
          <div>
            <h2 className="text-xs uppercase tracking-widest text-gray-800 mb-3">Live Log</h2>
            <div className="bg-white border border-gray-200 rounded p-3 h-80 overflow-y-auto text-xs text-gray-500 leading-relaxed shadow-sm">
              {log.length === 0 && <span className="text-gray-600">Waiting for scan...</span>}
              {log.map((line, i) => (
                <div
                  key={i}
                  className={line.startsWith("✓") ? "text-emerald-600" : ""}
                >
                  {line}
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>

        </div>
      </div>
      <Footer />
    </>
  );
}
