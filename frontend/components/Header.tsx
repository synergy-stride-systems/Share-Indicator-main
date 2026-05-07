"use client";

import { useRouter, usePathname } from "next/navigation";
import Image from "next/image";

const NAV_LINKS = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Conditions", href: "/configure" },
];

export default function Header() {
  const router = useRouter();
  const pathname = usePathname();

  const handleLogout = () => {
    localStorage.clear();
    router.push("/");
  };

  return (
    <header className="bg-white border-b border-gray-300 top-0 w-full sticky z-50">
      <div className="max-w-full flex items-center justify-between px-4">

        {/* Brand */}
        <div
          className="flex items-center gap-3 cursor-pointer"
          onClick={() => router.push("/dashboard")}
        >
          {/* Logo mark: two chevron shapes suggesting forward momentum */}
          <div className="flex items-center" style={{ gap: "1px" }}>
            <Image src="/logo.png" alt="Synergy Stride" width={80} height={80} className="hidden sm:block" />
          </div>
          <div className="flex items-center gap-3">
            <span className=" font-bold tracking-widest uppercase text-sm select-none"
            style={{ background: "linear-gradient(90deg, #cc1f00, #ff6a00)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Synergy Stride
            </span>
            <span className="hidden sm:block text-gray-500 text-xs tracking-widest uppercase border-l border-gray-700 pl-3 select-none">
              F&amp;O Scanner
            </span>
          </div>
        </div>

        {/* Nav + Logout */}
        <div className="flex items-center gap-6">
          <nav className="hidden md:flex items-center gap-5">
            {NAV_LINKS.map(({ label, href }) => {
              const isActive = pathname === href;
              return (
                <button
                  key={href}
                  onClick={() => router.push(href)}
                  className={`text-xs tracking-widest uppercase transition-colors ${
                    isActive
                      ? "text-emerald-400 border-b border-emerald-500 pb-0.5"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </nav>

          {/* Mobile nav: show only active page label */}
          <div className="flex md:hidden items-center gap-3">
            {NAV_LINKS.filter(({ href }) => pathname !== href).map(({ label, href }) => (
              <button
                key={href}
                onClick={() => router.push(href)}
                className="text-sm text-gray-500 hover:text-gray-900  uppercase transition-colors"
              >
                {label}
              </button>
            ))}
          </div>

          <button
            onClick={handleLogout}
            className="text-xs text-gray-500 hover:text-red-400 transition-colors uppercase tracking-widest"
          >
            Logout
          </button>
        </div>

      </div>
    </header>
  );
}
