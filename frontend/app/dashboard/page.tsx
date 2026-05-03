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

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [log]);

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
};

  /*const startScan = async () => {
  try {
    setResults([]);
    setSummary(null);
    setLog([]);
    setProgress({ current: 0, total: 0 });
    setScanning(true);

    const user = JSON.parse(localStorage.getItem("user") || "{}");
    const userId = user.id;

    if (!userId) {
      alert("User not found. Please login again.");
      return;
    }

    // ✅ 1. Get conditions from backend DB
    const res = await fetch(`http://localhost:4000/api/strategy/get/${userId}`);
    const data = await res.json();

    const conditions = (data.conditions || []).filter((c: any) => c.enabled);

    console.log("Using conditions:", conditions);

    addLog(`Starting scan with ${conditions.length} condition(s)...`);

    // ✅ 2. Send conditions to Flask (IMPORTANT)
    await fetch("http://127.0.0.1:5000/scan", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ conditions })
    });

    // ✅ 3. Start SSE stream
    const es = new EventSource("http://127.0.0.1:5000/scan/stream");
    eventSourceRef.current = es;

    es.onmessage = (e) => {
      const msg = JSON.parse(e.data);

      console.log("STREAM:", msg);

      // ✅ PROGRESS
      if (msg.type === "progress") {
        setCurrentSymbol(msg.symbol);
        setProgress({ current: msg.current, total: msg.total });
        addLog(`Scanning ${msg.symbol} (${msg.current}/${msg.total})`);
      }

      // ✅ RESULT
      if (msg.type === "result") {
        setResults(prev =>
          [...prev, msg.data].sort((a, b) => b.percent_gain - a.percent_gain)
        );
        addLog(`✓ BUY: ${msg.data.symbol} +${msg.data.percent_gain}%`);
      }

      // ✅ SUMMARY
      if (msg.type === "summary") {
        setSummary(msg);
        addLog(`Scan complete — ${msg.total_signals} signals`);
      }

      // ✅ STOP
      if (msg.type === "stop") {
        setScanning(false);
        setCurrentSymbol("");
        es.close();
      }
    };

    es.onerror = () => {
      addLog("Connection error.");
      setScanning(false);
      es.close();
    };

  } catch (err) {
    console.error(err);
    setScanning(false);
    addLog("Error starting scan");
  }
};*/
  /*const startScan = async () => {
  const userId = localStorage.getItem("userId");

  // 1. Fetch strategy from DB
  const res = await fetch(`http://localhost:4000/api/strategy/get/${userId}`);
  const data = await res.json();

  const conditions = data.conditions.filter((c: any) => c.enabled);

  console.log("Using conditions:", conditions);

  // 2. Send to backend controller
  await fetch("http://localhost:4000/api/scanner", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ conditions })
  });

  // 3. Start streaming
  const eventSource = new EventSource("http://127.0.0.1:5000/scan/stream");

  eventSource.onmessage = (event) => {
    const msg = JSON.parse(event.data);

    console.log("STREAM:", msg);

    if (msg.type === "result") {
      // update table
    }

    if (msg.type === "summary") {
      // show summary
    }

    if (msg.type === "stop") {
      eventSource.close();
    }
  };
};*/


  /*const startScan = async () => {
    setResults([]);
    setSummary(null);
    setLog([]);
    setProgress({ current: 0, total: 0 });
    setScanning(true);

    await fetch("http://localhost:5000/scan/start", { method: "POST" });

    // Load active conditions from localStorage (set on config page)
    const activeConditions = getActiveConditions();
    const conditionsParam = encodeURIComponent(JSON.stringify(activeConditions));

    const es = new EventSource(
      `http://localhost:5000/scan/stream?conditions=${conditionsParam}`
    );
    eventSourceRef.current = es;

    addLog(`Starting scan with ${activeConditions.length} condition(s)...`);

    es.onmessage = (e) => {
      const msg = JSON.parse(e.data);

      if (msg.type === "progress") {
        setCurrentSymbol(msg.symbol);
        setProgress({ current: msg.current, total: msg.total });
        addLog(`Scanning ${msg.symbol}... (${msg.current}/${msg.total})`);
      }

      if (msg.type === "result") {
        setResults(prev =>
          [...prev, msg.data].sort((a, b) => b.percent_gain - a.percent_gain)
        );
        addLog(`✓ BUY signal: ${msg.data.symbol} +${msg.data.percent_gain}%`);
      }

      if (msg.type === "summary") {
        setSummary(msg);
        addLog(`\nScan complete — ${msg.total_signals} signals found.`);
      }

      if (msg.type === "stop") {
        setScanning(false);
        setCurrentSymbol("");
        es.close();
      }
    };

    es.onerror = () => {
      addLog("Connection error.");
      setScanning(false);
      es.close();
    };
  };*/

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
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8 font-mono">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-xl font-bold tracking-widest uppercase text-white">
          F&O Scanner
        </h1>
        <button
          onClick={handleLogout}
          className="text-xs text-gray-500 hover:text-red-400 transition-colors uppercase tracking-widest"
        >
          Logout
        </button>
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
          className="px-5 py-2 bg-red-700 hover:bg-red-600 disabled:opacity-40 text-white text-sm rounded transition-colors"
        >
          Stop
        </button>
        {/* Config shortcut */}
        <button
          onClick={() => router.push("/configure")}
          disabled={scanning}
          className="px-5 py-2 bg-gray-800 hover:bg-gray-700 disabled:opacity-40 text-gray-300 text-sm rounded transition-colors"
        >
          ⚙ Conditions
        </button>
      </div>

      {/* Progress bar */}
      {scanning && (
        <div className="mb-6">
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>{currentSymbol}</span>
            <span>{progress.current}/{progress.total} — {pct}%</span>
          </div>
          <div className="w-full bg-gray-800 rounded h-1.5">
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
            <div key={stat.label} className="bg-gray-900 border border-gray-800 rounded p-3">
              <p className="text-xs text-gray-500 uppercase tracking-wider">{stat.label}</p>
              <p className="text-lg text-white mt-0.5">{stat.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Results table */}
        <div>
          <h2 className="text-xs uppercase tracking-widest text-gray-500 mb-3">
            Buy Signals ({results.length})
          </h2>
          {results.length === 0 ? (
            <p className="text-gray-600 text-sm">No signals yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="text-xs text-gray-500 uppercase tracking-wider border-b border-gray-800">
                    <th className="text-left py-2 pr-4">Symbol</th>
                    <th className="text-right py-2 pr-4">% Gain</th>
                    <th className="text-right py-2 pr-4">Close</th>
                    <th className="text-right py-2 pr-4">Volume</th>
                    <th className="text-right py-2">P/E</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r, i) => (
                    <tr key={i} className="border-b border-gray-900 hover:bg-gray-900 transition-colors">
                      <td className="py-2 pr-4 text-white font-bold">{r.symbol}</td>
                      <td className="py-2 pr-4 text-right text-emerald-400">+{r.percent_gain}%</td>
                      <td className="py-2 pr-4 text-right text-gray-300">{r.curr_close}</td>
                      <td className="py-2 pr-4 text-right text-gray-400">{r.volume?.toLocaleString()}</td>
                      <td className="py-2 text-right text-gray-500">{r.pe_ratio ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Live log */}
        <div>
          <h2 className="text-xs uppercase tracking-widest text-gray-500 mb-3">Live Log</h2>
          <div className="bg-gray-900 border border-gray-800 rounded p-3 h-80 overflow-y-auto text-xs text-gray-400 leading-relaxed">
            {log.length === 0 && <span className="text-gray-600">Waiting for scan...</span>}
            {log.map((line, i) => (
              <div
                key={i}
                className={line.startsWith("✓") ? "text-emerald-400" : ""}
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
