"use client";

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="bg-white border-t border-gray-300 mt-auto w-full sticky bottom-0">
      <div className="max-w-full flex flex-row md:flex-row items-center justify-between py-4 px-4 gap-6">

        {/* Brand + version */}
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span
            className="font-bold tracking-widest uppercase text-sm"
            style={{ background: "linear-gradient(90deg, #cc1f00, #ff6a00)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}
          >
            Synergy Stride
          </span>
          <span className="text-gray-300">·</span>
          <span>F&amp;O Scanner v1.0</span>
        </div>

        {/* Copyright */}
        <p className="text-xs text-gray-600 tracking-wide">
          © {year} Synergystride Systems. All rights reserved.
        </p>

        {/* Disclaimer */}
        <div className="max-w-7xl mx-auto px-8 py-3">
          <p className="text-xs text-gray-600 leading-relaxed text-center">
            <span
              className="font-semibold uppercase tracking-widest mr-2"
              style={{ color: "#cc1f00" }}
            >
              Disclaimer:
            </span>
            For informational purposes only. Not financial advice. F&amp;O trading involves substantial risk. Consult a qualified advisor before investing.
          </p>
        </div>

      </div>
    </footer>
  );
}
