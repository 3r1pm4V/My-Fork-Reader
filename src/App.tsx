/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export default function App() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8 flex flex-col items-center justify-center font-sans">
      <div className="max-w-2xl w-full bg-slate-800 rounded-xl shadow-2xl p-8 border border-slate-700">
        <h1 className="text-3xl font-bold mb-4 text-blue-400">E-Reader Python Foundation</h1>
        <p className="text-lg text-slate-300 mb-6">
          Dự án E-Reader (Phần 1/8) đã được khởi tạo với cấu trúc mã nguồn Python chuyên nghiệp.
        </p>
        
        <div className="space-y-4">
          <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700">
            <h2 className="text-xl font-semibold mb-2 text-emerald-400">Các thành phần đã hoàn thành:</h2>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>Cấu trúc package <code className="text-pink-400">ereader/</code></li>
              <li>Quản lý cấu hình YAML (<code className="text-pink-400">config.py</code>)</li>
              <li>Cơ sở dữ liệu SQLite (<code className="text-pink-400">db.py</code>)</li>
              <li>Hệ thống Logging (<code className="text-pink-400">logger.py</code>)</li>
              <li>Khung ứng dụng PyQt6 (<code className="text-pink-400">app.py</code>)</li>
            </ul>
          </div>
          
          <p className="text-sm text-slate-500 italic">
            Lưu ý: Môi trường hiện tại là Web Preview. Để chạy ứng dụng PyQt6, vui lòng tải mã nguồn về máy local và cài đặt thư viện cần thiết (PyQt6, PyYAML).
          </p>
        </div>
      </div>
    </div>
  );
}

