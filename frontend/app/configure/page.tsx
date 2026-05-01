"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";

const VARIABLES = [
  { value: "curr_open",  label: "Curr Open"  },
  { value: "curr_close", label: "Curr Close" },
  { value: "curr_low",   label: "Curr Low"   },
  { value: "curr_high",  label: "Curr High"  },
  { value: "prev_open",  label: "Prev Open"  },
  { value: "prev_close", label: "Prev Close" },
  { value: "prev_low",   label: "Prev Low"   },
  { value: "prev_high",  label: "Prev High"  },
];

const OPERATORS = [
  { value: "<",  label: "<"  },
  { value: ">",  label: ">"  },
  { value: "<=", label: "<=" },
  { value: ">=", label: ">=" },
  { value: "==", label: "==" },
];

interface Condition {
  id: number;
  enabled: boolean;
  lhs: string;
  op: string;
  rhs: string;
  conn: "and" | "or"; // connector to the NEXT condition
}

const DEFAULT_CONDITIONS: Condition[] = [
  { id: 1, enabled: true, lhs: "curr_open",  op: "<", rhs: "prev_close", conn: "and" },
];

const STORAGE_KEY = "scanner_conditions";
let nextId = 10;

export default function ConfigPage() {
  const router = useRouter();
  const [conditions, setConditions] = useState<Condition[]>(
    DEFAULT_CONDITIONS.map(c => ({ ...c }))
  );
  const [saved, setSaved] = useState(false);

  {/*useEffect(() => {
    if (!localStorage.getItem("token")) { router.push("/"); return; }
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try { setConditions(JSON.parse(stored)); } catch {
    
   [router]);*/}
  useEffect(() => {
  const userId = localStorage.getItem("userId");

  fetch(`http://localhost:4000/api/strategy/get/${userId}`)
    .then(res => res.json())
    .then(data => {
      if (data.conditions?.length) {
        setConditions(data.conditions);
      }
    });
}, []);

  const update = useCallback((id: number, field: keyof Condition, value: string | boolean) => {
    setConditions(prev => prev.map(c => c.id === id ? { ...c, [field]: value } : c));
    setSaved(false);
  }, []);

  const toggleConn = useCallback((id: number) => {
    setConditions(prev =>
      prev.map(c => c.id === id ? { ...c, conn: c.conn === "and" ? "or" : "and" } : c)
    );
    setSaved(false);
  }, []);

  const addCondition = () => {
    setConditions(prev => [
      ...prev,
      { id: nextId++, enabled: true, lhs: "curr_open", op: "<", rhs: "prev_close", conn: "and" },
    ]);
    setSaved(false);
  };

  const removeCondition = (id: number) => {
    setConditions(prev => prev.length > 1 ? prev.filter(c => c.id !== id) : prev);
    setSaved(false);
  };

  const resetToDefault = () => {
    setConditions(DEFAULT_CONDITIONS.map(c => ({ ...c })));
    setSaved(false);
  };

  {/*const saveConditions = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conditions));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };*/}

  const saveConditions = async () => {
  const userId = localStorage.getItem("userId");

  await fetch("http://localhost:4000/api/strategy/save", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      conditions,
      userId
    })
  });

  setSaved(true);
  setTimeout(() => setSaved(false), 2000);
};

  const activeConditions = conditions.filter(c => c.enabled);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8 font-mono">

      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div className="flex items-center gap-6">
          {/*<button onClick={() => router.push("/dashboard")}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors uppercase tracking-widest">
            ← Dashboard
          </button>*/}
          <h1 className="text-xl font-bold tracking-widest uppercase text-white">Scan Config</h1>
        </div>
        <button onClick={() => { localStorage.clear(); router.push("/"); }}
          className="text-xs text-gray-500 hover:text-red-400 transition-colors uppercase tracking-widest">
          Logout
        </button>
      </div>

      <div className="max-w-2xl">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-6">
          Conditions joined by and / or — chain evaluates top to bottom.
        </p>

        {/* Condition rows */}
        <div className="mb-4">
          {conditions.map((cond, idx) => (
            <div key={cond.id}>
              {/* Row */}
              <div className={`border rounded p-4 transition-colors ${
                cond.enabled ? "bg-gray-900 border-gray-800" : "bg-gray-950 border-gray-900 opacity-50"
              }`}>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-600 w-4 text-right flex-shrink-0">{idx + 1}</span>

                  {/* Toggle */}
                  {/*<button onClick={() => update(cond.id, "enabled", !cond.enabled)}
                    className={`w-8 h-5 rounded-full border flex-shrink-0 transition-colors relative ${
                      cond.enabled ? "bg-emerald-600 border-emerald-500" : "bg-gray-800 border-gray-700"
                    }`}>
                    <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${
                      cond.enabled ? "left-3" : "left-0.5"
                    }`} />
                  </button>*/}

                  {/* LHS */}
                  <select value={cond.lhs} disabled={!cond.enabled}
                    onChange={e => update(cond.id, "lhs", e.target.value)}
                    className="flex-1 bg-gray-800 border border-gray-700 text-gray-100 text-sm rounded px-2 py-1.5 focus:outline-none focus:border-gray-500 disabled:cursor-not-allowed">
                    {VARIABLES.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
                  </select>

                  {/* Operator */}
                  <select value={cond.op} disabled={!cond.enabled}
                    onChange={e => update(cond.id, "op", e.target.value)}
                    className="w-16 bg-gray-800 border border-gray-700 text-emerald-400 text-sm rounded px-2 py-1.5 text-center focus:outline-none focus:border-gray-500 disabled:cursor-not-allowed">
                    {OPERATORS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>

                  {/* RHS */}
                  <select value={cond.rhs} disabled={!cond.enabled}
                    onChange={e => update(cond.id, "rhs", e.target.value)}
                    className="flex-1 bg-gray-800 border border-gray-700 text-gray-100 text-sm rounded px-2 py-1.5 focus:outline-none focus:border-gray-500 disabled:cursor-not-allowed">
                    {VARIABLES.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
                  </select>

                  {/* Remove */}
                  {conditions.length > 1 && (
                    <button onClick={() => removeCondition(cond.id)}
                      className="text-gray-600 hover:text-red-400 text-lg leading-none px-1 transition-colors">
                      ×
                    </button>
                  )}
                </div>
              </div>

              {/* AND / OR connector between rows */}
              {idx < conditions.length - 1 && (
                <div className="flex items-center gap-2 py-1 px-2">
                  <div className="flex-1 border-t border-gray-800" />
                  <select
  value={cond.conn}
  onChange={(e) => update(cond.id, "conn", e.target.value as "and" | "or")}
  className="text-xs px-3 py-1 rounded border border-gray-700 bg-gray-900
             text-gray-400 focus:outline-none focus:border-emerald-500
             uppercase tracking-widest"
>
  <option value="and">AND</option>
  <option value="or">OR</option>
  <option value="not">NOT</option>
</select>
                  {/*<button onClick={() => toggleConn(cond.id)}
                    className="text-xs px-3 py-0.5 rounded border border-gray-700 bg-gray-900
                               text-gray-400 hover:border-emerald-600 hover:text-emerald-400
                               uppercase tracking-widest transition-colors">
                    {cond.conn}
                  </button>*/}
                  <div className="flex-1 border-t border-gray-800" />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Add row */}
        <button onClick={addCondition}
          className="mb-6 text-xs text-gray-500 hover:text-emerald-400 border border-gray-800
                     hover:border-emerald-700 rounded px-4 py-2 transition-colors uppercase tracking-widest">
          + Add condition
        </button>

        {/* Warning */}
        {activeConditions.length === 0 && (
          <div className="mb-4 px-4 py-2 bg-red-950 border border-red-900 rounded text-xs text-red-400">
            Warning: no conditions enabled — every stock will match.
          </div>
        )}

        {/* Preview */}
        <div className="bg-gray-900 border border-gray-800 rounded p-4 mb-6">
          <p className="text-xs text-gray-600 uppercase tracking-widest mb-3">Preview</p>
          {activeConditions.length === 0 ? (
            <span className="text-xs text-gray-600">No active conditions.</span>
          ) : (
            <div className="space-y-1">
              {activeConditions.map((cond, i) => {
                const lhsLabel = VARIABLES.find(v => v.value === cond.lhs)?.label ?? cond.lhs;
                const rhsLabel = VARIABLES.find(v => v.value === cond.rhs)?.label ?? cond.rhs;
                // find this condition's connector in the full list
                const origIdx = conditions.findIndex(c => c.id === cond.id);
                const conn = conditions[origIdx]?.conn ?? "and";
                return (
                  <div key={cond.id} className="flex items-center gap-2 text-sm flex-wrap">
                    <span className="text-gray-300">{lhsLabel}</span>
                    <span className="text-emerald-400 font-bold">{cond.op}</span>
                    <span className="text-gray-300">{rhsLabel}</span>
                    {i < activeConditions.length - 1 && (
                      <span className="text-gray-600 text-xs uppercase ml-1 border border-gray-700 rounded px-1.5 py-0.5">
                        {conn}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button onClick={saveConditions}
            className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm rounded transition-colors">
            {saved ? "Saved ✓" : "Save conditions"}
          </button>
          <button onClick={resetToDefault}
            className="px-5 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm rounded transition-colors">
            Reset to default
          </button>
          <button onClick={() => router.push("/dashboard")}
            className="px-5 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm rounded transition-colors">
            Back to dashboard
          </button>
        </div>
      </div>
    </div>
  );
}