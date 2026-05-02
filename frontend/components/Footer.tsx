"use client";

const FOOTER_LINKS = [
  { label: "Support", href: "#" },
  { label: "Privacy", href: "#" },
  { label: "Terms", href: "#" },
];

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="bg-gray-900 border-gray-800 mt-auto w-full sticky bottom-0">
      <div className="max-w-full flex flex-row md:flex-row items-center justify-between py-4 px-4 gap-8">

        {/* Brand + version */}
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span className="text-emerald-500 font-bold tracking-widest uppercase">
            SynergyStride
          </span>
          <span className="text-gray-700">·</span>
          <span>F&amp;O Scanner v1.0</span>
        </div>

        {/* Copyright */}
        <p className="text-xs text-gray-600 tracking-wide">
          © {year} Synergy Stride. All rights reserved.
        </p>

         <div className="">
        <div className="max-w-7xl mx-auto px-8 py-3">
          <p className="text-xs text-gray-700 leading-relaxed text-center">
            <span className="text-gray-600 font-semibold uppercase tracking-widest mr-2">Disclaimer:</span>
            For informational purposes only. Not financial advice. F&amp;O trading involves substantial risk. Consult a qualified advisor before investing.
          </p>
        </div>
      </div>

        {/* Links */}
        {/*<div className="flex items-center gap-2">
          {FOOTER_LINKS.map(({ label, href }) => (
            <a
              key={label}
              href={href}
              className="text-xs text-gray-600 hover:text-gray-400  uppercase"
            >
              {label}
            </a>
          ))}
        </div>*/}

      </div>

     

    </footer>
  );
}
