"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import { apiUrl } from "../../lib/api";

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
  conn: "and" | "or";
}

const DEFAULT_CONDITIONS: Condition[] = [
  { id: 1, enabled: true, lhs: "curr_open", op: "<", rhs: "prev_close", conn: "and" },
];

const STORAGE_KEY = "scanner_conditions";
let nextId = 10;

export default function ConfigPage() {
  const router = useRouter();
  const [conditions, setConditions] = useState<Condition[]>(
    DEFAULT_CONDITIONS.map(c => ({ ...c }))
  );
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const userId = localStorage.getItem("userId");

  fetch(apiUrl(`/api/strategy/get/${userId}`))
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

  const saveConditions = async () => {
    const userId = localStorage.getItem("userId");

  await fetch(apiUrl("/api/strategy/save"), {
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
    <>
      <Header />
      <div className="min-h-screen bg-gray-100 text-gray-900 p-8 font-mono">

        {/* Header */}
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-6">
            <h1 className="text-xl font-bold tracking-widest uppercase text-gray-900">Configurations</h1>
          </div>
          
        </div>

        <div className="max-w-2xl">
          <p className="text-xs text-gray-700 uppercase tracking-wider mb-6">
            Conditions joined by and / or — chain evaluates top to bottom.
          </p>

          {/* Condition rows */}
          <div className="mb-4">
            {conditions.map((cond, idx) => (
              <div key={cond.id}>
                {/* Row */}
                <div className={`border rounded p-4 transition-colors ${
                  cond.enabled
                    ? "bg-white border-gray-300"
                    : "bg-gray-300 border-gray-300 "
                }`}>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-600 w-4 text-right flex-shrink-0">{idx + 1}</span>

                    {/* LHS */}
                    <select
                      value={cond.lhs}
                      disabled={!cond.enabled}
                      onChange={e => update(cond.id, "lhs", e.target.value)}
                      className="flex-1 bg-gray-100 border border-gray-200 text-gray-800 text-sm rounded px-2 py-1.5 focus:outline-none focus:border-gray-400 disabled:cursor-not-allowed"
                    >
                      {VARIABLES.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
                    </select>

                    {/* Operator */}
                    <select
                      value={cond.op}
                      disabled={!cond.enabled}
                      onChange={e => update(cond.id, "op", e.target.value)}
                      className="w-16 bg-gray-100 border border-gray-200 text-emerald-600 text-sm rounded px-2 py-1.5 text-center focus:outline-none focus:border-gray-400 disabled:cursor-not-allowed"
                    >
                      {OPERATORS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>

                    {/* RHS */}
                    <select
                      value={cond.rhs}
                      disabled={!cond.enabled}
                      onChange={e => update(cond.id, "rhs", e.target.value)}
                      className="flex-1 bg-gray-100 border border-gray-200 text-gray-800 text-sm rounded px-2 py-1.5 focus:outline-none focus:border-gray-400 disabled:cursor-not-allowed"
                    >
                      {VARIABLES.map(v => <option key={v.value} value={v.value}>{v.label}</option>)}
                    </select>

                    {/* Remove */}
                    {conditions.length > 1 && (
                      <button
                        onClick={() => removeCondition(cond.id)}
                        className="text-gray-300 hover:text-red-500 text-lg leading-none px-1 transition-colors"
                      >
                        ×
                      </button>
                    )}
                  </div>
                </div>

                {/* AND / OR connector between rows */}
                {idx < conditions.length - 1 && (
                  <div className="flex items-center gap-2 py-1 px-2">
                    <div className="flex-1 border-t border-gray-200" />
                    <select
                      value={cond.conn}
                      onChange={(e) => update(cond.id, "conn", e.target.value as "and" | "or")}
                      className="text-xs px-3 py-1 rounded border border-gray-200 bg-white
                                 text-gray-500 focus:outline-none focus:border-emerald-400
                                 uppercase tracking-widest"
                    >
                      <option value="and">AND</option>
                      <option value="or">OR</option>
                      <option value="not">NOT</option>
                    </select>
                    <div className="flex-1 border-t border-gray-200" />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Add row */}
          <button
            onClick={addCondition}
            className="mb-6 text-xs text-gray-700 hover:text-emerald-600 border border-gray-200
                       hover:border-emerald-400 rounded px-4 py-2 transition-colors uppercase tracking-widest bg-white"
          >
            + Add condition
          </button>

          {/* Warning */}
          {activeConditions.length === 0 && (
            <div className="mb-4 px-4 py-2 bg-red-50 border border-red-200 rounded text-xs text-red-500">
              Warning: no conditions enabled — every stock will match.
            </div>
          )}

          {/* Preview */}
          <div className="bg-white border border-gray-200 rounded p-4 mb-6 shadow-sm">
            <p className="text-sm text-gray-800 uppercase tracking-widest mb-3">Preview</p>
            {activeConditions.length === 0 ? (
              <span className="text-xs text-gray-300">No active conditions.</span>
            ) : (
              <div className="space-y-1">
                {activeConditions.map((cond, i) => {
                  const lhsLabel = VARIABLES.find(v => v.value === cond.lhs)?.label ?? cond.lhs;
                  const rhsLabel = VARIABLES.find(v => v.value === cond.rhs)?.label ?? cond.rhs;
                  const origIdx = conditions.findIndex(c => c.id === cond.id);
                  const conn = conditions[origIdx]?.conn ?? "and";
                  return (
                    <div key={cond.id} className="flex items-center gap-2 text-sm flex-wrap">
                      <span className="text-gray-700">{lhsLabel}</span>
                      <span className="text-emerald-600 font-bold">{cond.op}</span>
                      <span className="text-gray-700">{rhsLabel}</span>
                      {i < activeConditions.length - 1 && (
                        <span className="text-gray-400 text-xs uppercase ml-1 border border-gray-200 rounded px-1.5 py-0.5">
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
            <button
              onClick={saveConditions}
              className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm rounded transition-colors"
            >
              {saved ? "Saved ✓" : "Save conditions"}
            </button>
            {/*<button
              onClick={resetToDefault}
              className="px-5 py-2 bg-white hover:bg-gray-100 text-gray-600 text-sm rounded border border-gray-200 transition-colors"
            >
              Reset to default
            </button>*/
}
            <button
              onClick={() => router.push("/dashboard")}
              className="px-5 py-2 bg-white hover:bg-gray-100 text-gray-600 text-sm rounded border border-gray-200 transition-colors"
            >
              Back to dashboard
            </button>
          </div>
        </div>
      </div>
      <Footer />
    </>
  );
}
