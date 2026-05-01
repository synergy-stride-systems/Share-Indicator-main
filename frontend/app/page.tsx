"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [focused, setFocused] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("token");
      if (token) router.push("/dashboard");
    }
  }, [router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      alert("Please fill all fields");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch("http://localhost:4000/api/users/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Login failed");
      localStorage.setItem("token", data.token);
      localStorage.setItem("user", JSON.stringify(data.user));
      localStorage.setItem("userId", data.user.id);
      router.push("/dashboard");
    } catch (error: any) {
      alert(error.message || "Something went wrong");
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#080b0f] flex items-center justify-center font-mono relative overflow-hidden">

      {/* Grid background */}
      <div
        className="absolute inset-0 opacity-100"
        style={{
          backgroundImage:
            "linear-gradient(rgba(16,185,129,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(16,185,129,0.04) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      {/* Corner accents */}
      <div className="absolute top-0 left-0 w-40 h-40 border-t border-l border-emerald-500 opacity-15" />
      <div className="absolute bottom-0 right-0 w-40 h-40 border-b border-r border-emerald-500 opacity-15" />

      {/* Card */}
      <div
        className={`relative w-[380px] bg-[#0d1117] border border-[#1e2d24] px-10 py-12 transition-all duration-500 ${
          mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-3"
        }`}
      >
        {/* Top glow line */}
        <div
          className="absolute top-0 left-0 right-0 h-px"
          style={{
            background: "linear-gradient(90deg, transparent, #10b981, transparent)",
          }}
        />

        {/* Header */}
        <p className="text-[10px] tracking-[0.2em] uppercase text-emerald-500 opacity-80 mb-7">
          F&amp;O Scanner
        </p>
        <h1 className="text-[22px] font-medium text-[#e6edf3] tracking-tight mb-1">
          Access Terminal
        </h1>
        <p className="text-[13px] text-[#4a5568] font-light mb-9">
          Sign in to your account
        </p>

        <form onSubmit={handleLogin}>
          {/* Email */}
          <div className="mb-4">
            <label
              className={`block text-[10px] tracking-[0.15em] uppercase mb-2 transition-colors duration-200 ${
                focused === "email" ? "text-emerald-500" : "text-[#4a5568]"
              }`}
            >
              Email address
            </label>
            <input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onFocus={() => setFocused("email")}
              onBlur={() => setFocused(null)}
              className="w-full bg-[#0a0e13] border border-[#1e2d24] text-[#e6edf3] text-[13px] px-3.5 py-3 outline-none placeholder-[#2d3748] focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/20 transition-all duration-200"
            />
          </div>

          {/* Password */}
          <div className="mb-4">
            <label
              className={`block text-[10px] tracking-[0.15em] uppercase mb-2 transition-colors duration-200 ${
                focused === "password" ? "text-emerald-500" : "text-[#4a5568]"
              }`}
            >
              Password
            </label>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onFocus={() => setFocused("password")}
              onBlur={() => setFocused(null)}
              className="w-full bg-[#0a0e13] border border-[#1e2d24] text-[#e6edf3] text-[13px] px-3.5 py-3 outline-none placeholder-[#2d3748] focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/20 transition-all duration-200"
            />
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full mt-7 py-3 bg-transparent border border-emerald-500 text-emerald-500 text-[12px] tracking-[0.2em] uppercase hover:bg-emerald-500 hover:text-[#080b0f] hover:shadow-[0_0_20px_rgba(16,185,129,0.2)] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-1">
                Authenticating
                <span className="flex gap-0.5 ml-1">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="animate-bounce text-base leading-none"
                      style={{ animationDelay: `${i * 0.15}s` }}
                    >
                      .
                    </span>
                  ))}
                </span>
              </span>
            ) : (
              "Sign In →"
            )}
          </button>
        </form>

        {/* Footer */}
        <div className="mt-7 pt-5 border-t border-[#1a2332] flex justify-between text-[10px] text-[#2d3748] tracking-widest">
          <span>SECURE CONNECTION</span>
          <span>v1.0.0</span>
        </div>
      </div>
    </div>
  );
}