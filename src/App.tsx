/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useEffect } from "react";
import {
  Sun,
  Moon,
  BookOpen,
  BookMarked,
  Layers,
  Cpu,
  Database,
  Sliders,
  Terminal,
  FileCode2,
  CheckCircle2,
  Bookmark,
  Eye,
  Type
} from "lucide-react";

type ThemeMode = "dark" | "light" | "sepia";

export default function App() {
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem("ereader_theme_mode");
    if (saved === "light" || saved === "dark" || saved === "sepia") {
      return saved;
    }
    if (typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: light)").matches) {
      return "light";
    }
    return "dark";
  });

  const [fontSize, setFontSize] = useState<"sm" | "base" | "lg">("base");

  useEffect(() => {
    localStorage.setItem("ereader_theme_mode", theme);
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
      root.classList.remove("sepia");
    } else if (theme === "sepia") {
      root.classList.remove("dark");
      root.classList.add("sepia");
    } else {
      root.classList.remove("dark");
      root.classList.remove("sepia");
    }
  }, [theme]);

  // Color theme palettes tailored for reading comfort
  const themeStyles = {
    dark: {
      bg: "bg-slate-950",
      text: "text-slate-100",
      cardBg: "bg-slate-900/90",
      cardBorder: "border-slate-800",
      innerBg: "bg-slate-900/50",
      subText: "text-slate-400",
      accent: "text-blue-400",
      accentBg: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      highlight: "bg-slate-800 border-slate-700",
      codeText: "text-pink-400",
      bookPage: "bg-slate-900 text-slate-200 border-slate-800"
    },
    light: {
      bg: "bg-slate-50",
      text: "text-slate-900",
      cardBg: "bg-white",
      cardBorder: "border-slate-200 shadow-sm",
      innerBg: "bg-slate-50",
      subText: "text-slate-600",
      accent: "text-blue-600",
      accentBg: "bg-blue-50 text-blue-700 border-blue-200",
      highlight: "bg-slate-100 border-slate-200",
      codeText: "text-pink-600",
      bookPage: "bg-white text-slate-800 border-slate-200 shadow-sm"
    },
    sepia: {
      bg: "bg-[#fbf0d9]",
      text: "text-[#433422]",
      cardBg: "bg-[#f4e4c1]",
      cardBorder: "border-[#e2ce9f] shadow-sm",
      innerBg: "bg-[#ebd9b1]/60",
      subText: "text-[#6b583f]",
      accent: "text-[#8c4b18]",
      accentBg: "bg-[#e5cda0] text-[#713910] border-[#d4b986]",
      highlight: "bg-[#ebd9b1] border-[#ddc695]",
      codeText: "text-[#9c3224]",
      bookPage: "bg-[#fef9eb] text-[#3f2f1e] border-[#e2cf9f]"
    }
  };

  const currentTheme = themeStyles[theme];

  return (
    <div className={`min-h-screen ${currentTheme.bg} ${currentTheme.text} transition-colors duration-300 font-sans p-4 sm:p-8 flex flex-col items-center justify-center`}>
      {/* Top Navigation & Controls */}
      <header className="max-w-3xl w-full mb-6 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <BookOpen className={`w-7 h-7 ${currentTheme.accent}`} />
          <div>
            <h1 className="text-xl font-bold tracking-tight">E-Reader Python Foundation</h1>
            <p className={`text-xs ${currentTheme.subText}`}>Kiến trúc foliate-js & PyQt6 Reader</p>
          </div>
        </div>

        {/* Theme & Comfort Toggles */}
        <div className="flex items-center gap-2">
          {/* Quick font sizing preview for reading */}
          <div className={`flex items-center rounded-lg border p-1 ${currentTheme.highlight}`}>
            <button
              type="button"
              onClick={() => setFontSize("sm")}
              className={`px-2 py-1 text-xs rounded font-medium transition ${
                fontSize === "sm" ? "bg-blue-500 text-white" : currentTheme.subText
              }`}
              title="Cỡ chữ nhỏ"
            >
              A-
            </button>
            <button
              type="button"
              onClick={() => setFontSize("base")}
              className={`px-2 py-1 text-xs rounded font-medium transition ${
                fontSize === "base" ? "bg-blue-500 text-white" : currentTheme.subText
              }`}
              title="Cỡ chữ vừa"
            >
              A
            </button>
            <button
              type="button"
              onClick={() => setFontSize("lg")}
              className={`px-2 py-1 text-xs rounded font-medium transition ${
                fontSize === "lg" ? "bg-blue-500 text-white" : currentTheme.subText
              }`}
              title="Cỡ chữ lớn"
            >
              A+
            </button>
          </div>

          {/* Mode Selector */}
          <div className={`flex items-center rounded-lg border p-1 gap-1 ${currentTheme.highlight}`}>
            <button
              type="button"
              onClick={() => setTheme("light")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition ${
                theme === "light"
                  ? "bg-amber-500 text-white shadow-xs"
                  : `${currentTheme.subText} hover:opacity-80`
              }`}
              aria-label="Light mode"
              title="Chế độ Sáng"
            >
              <Sun className="w-4 h-4" />
              <span className="hidden sm:inline">Sáng</span>
            </button>

            <button
              type="button"
              onClick={() => setTheme("sepia")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition ${
                theme === "sepia"
                  ? "bg-[#8c4b18] text-white shadow-xs"
                  : `${currentTheme.subText} hover:opacity-80`
              }`}
              aria-label="Sepia mode"
              title="Chế độ Sepia (Dịu mắt khi đọc)"
            >
              <Eye className="w-4 h-4" />
              <span className="hidden sm:inline">Sepia</span>
            </button>

            <button
              type="button"
              onClick={() => setTheme("dark")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition ${
                theme === "dark"
                  ? "bg-slate-700 text-white shadow-xs"
                  : `${currentTheme.subText} hover:opacity-80`
              }`}
              aria-label="Dark mode"
              title="Chế độ Tối"
            >
              <Moon className="w-4 h-4" />
              <span className="hidden sm:inline">Tối</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Card */}
      <main className={`max-w-3xl w-full ${currentTheme.cardBg} rounded-2xl p-6 sm:p-8 border ${currentTheme.cardBorder} transition-colors duration-300`}>
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border mb-3 ${currentTheme.accentBg}`}>
              <BookMarked className="w-3.5 h-3.5" />
              Phần 1/8: Python & foliate-js Core
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Hệ Thống Đọc Sách E-Reader</h2>
          </div>
          <div className="flex items-center gap-1">
            <span className={`text-xs px-2 py-1 rounded border ${currentTheme.highlight} ${currentTheme.subText}`}>
              Theme: <span className="font-semibold capitalize">{theme}</span>
            </span>
          </div>
        </div>

        <p className={`text-sm sm:text-base ${currentTheme.subText} mb-6 leading-relaxed`}>
          Nền tảng ứng dụng đọc sách điện tử được tối ưu hiệu năng bộ nhớ và tích hợp engine hiển thị <span className="font-semibold text-blue-500">foliate-js</span> chuẩn W3C EPUB qua cầu nối <code className={currentTheme.codeText}>QWebChannel</code>.
        </p>

        {/* Reading Preview Container */}
        <section className={`mb-6 p-5 rounded-xl border ${currentTheme.bookPage} transition-all`}>
          <div className="flex items-center justify-between border-b pb-3 mb-3 border-current/10">
            <div className="flex items-center gap-2">
              <Type className="w-4 h-4 opacity-70" />
              <span className="text-xs uppercase font-semibold tracking-wider opacity-70">Khung giả lập đọc sách (Comfort Reading Preview)</span>
            </div>
            <span className="text-xs opacity-60">Trang 42 / 318</span>
          </div>

          <div className={`space-y-3 leading-relaxed ${
            fontSize === "sm" ? "text-sm" : fontSize === "lg" ? "text-lg" : "text-base"
          }`}>
            <p>
              "Một cuốn sách hay không chỉ mang lại tri thức mà còn đòi hỏi một không gian hiển thị thoải mái cho thị giác. Màu nền dịu nhẹ và độ tương phản phù hợp giúp người đọc tập trung trọn vẹn vào từng trang sách mà không lo mỏi mắt suốt hàng giờ liền."
            </p>
            <p className="opacity-90">
              Giao thức đồng bộ đã được tích hợp cơ chế <code className={`text-xs px-1.5 py-0.5 rounded ${currentTheme.highlight}`}>ReaderBridge.cleanup()</code> nhằm triệt tiêu hoàn toàn listener trùng lặp và rò rỉ RAM khi điều hướng trang.
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-current/10 flex items-center justify-between text-xs opacity-75">
            <span>Tiến độ đọc: 13.2% (CFI: /6/4[chap02]!/4/2/10)</span>
            <span className="flex items-center gap-1 text-emerald-500 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" /> Bridge Active
            </span>
          </div>
        </section>

        {/* Technical Modules Finished */}
        <div className="space-y-4">
          <div className={`${currentTheme.innerBg} p-5 rounded-xl border ${currentTheme.cardBorder}`}>
            <h3 className={`text-base font-semibold mb-3 flex items-center gap-2 ${currentTheme.accent}`}>
              <Layers className="w-4 h-4" />
              Các thành phần kiến trúc đã hoàn thiện:
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs sm:text-sm">
              <div className={`flex items-start gap-2.5 p-2.5 rounded-lg border ${currentTheme.highlight}`}>
                <Cpu className="w-4 h-4 mt-0.5 text-blue-500 shrink-0" />
                <div>
                  <div className="font-semibold">foliate-js Bridge & QWebChannel</div>
                  <div className={currentTheme.subText}>Cơ chế dọn dẹp và quản lý listener đơn nhất</div>
                </div>
              </div>

              <div className={`flex items-start gap-2.5 p-2.5 rounded-lg border ${currentTheme.highlight}`}>
                <Database className="w-4 h-4 mt-0.5 text-emerald-500 shrink-0" />
                <div>
                  <div className="font-semibold">SQLite Storage (<code className={currentTheme.codeText}>db.py</code>)</div>
                  <div className={currentTheme.subText}>Lưu trữ tiến độ, bookmarks, annotations và cache</div>
                </div>
              </div>

              <div className={`flex items-start gap-2.5 p-2.5 rounded-lg border ${currentTheme.highlight}`}>
                <Sliders className="w-4 h-4 mt-0.5 text-purple-500 shrink-0" />
                <div>
                  <div className="font-semibold">Quản lý cấu hình (<code className={currentTheme.codeText}>config.py</code>)</div>
                  <div className={currentTheme.subText}>Load YAML tự động, hỗ trợ đa profile & theme</div>
                </div>
              </div>

              <div className={`flex items-start gap-2.5 p-2.5 rounded-lg border ${currentTheme.highlight}`}>
                <Terminal className="w-4 h-4 mt-0.5 text-amber-500 shrink-0" />
                <div>
                  <div className="font-semibold">Giao diện PyQt6 (<code className={currentTheme.codeText}>app.py</code>)</div>
                  <div className={currentTheme.subText}>Quản lý vòng đời WebEngineView & Thread Runner</div>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs opacity-70 p-3 rounded-lg border border-dashed border-current/20">
            <Bookmark className="w-4 h-4 shrink-0" />
            <span>
              Tùy chọn giao diện (Sáng / Tối / Sepia) được lưu tự động trong <strong>localStorage</strong> (khóa: <code className={currentTheme.codeText}>ereader_theme_mode</code>) và đồng bộ ngay lập tức.
            </span>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className={`max-w-3xl w-full mt-6 text-center text-xs ${currentTheme.subText}`}>
        E-Reader Python Project &copy; 2026. Tối ưu trải nghiệm đọc sách đa nền tảng.
      </footer>
    </div>
  );
}
