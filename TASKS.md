# Tasks

## Status Terakhir
- **Fase 1 (Frontend & Backend) SELESAI**:
  - Halaman Dashboard Diagnostik (`DiagnosticsDashboard.tsx`) diintegrasikan ke UI utama.
  - Komponen dashboard (`CommonCauseStats`, `SuspectedCauseChart`, `RecentTrades`, `QuickInsight`) berhasil diekstrak dan modular.
  - SQLite database `diagnostics.db` diinisialisasi secara versioned & idempotent (v1).
  - API endpoint FastAPI `/diagnostics/summary`, `/diagnostics/causes`, `/diagnostics/trades/recent`, dan `/diagnostics/insight` selesai diimplementasikan.
- **Fase 2 (Frontend & Backend) SELESAI**:
  - Halaman daftar trade (`DiagnosticTrades.tsx`) dengan pencarian teks, filter hasil (TP/SL), filter pair, sesi, dan date range.
  - Ekspor trade terpilih ke format CSV (download langsung) dan PDF (via dialog window print / WeasyPrint backend).
  - Halaman detail trade (`DiagnosticTradeDetail.tsx`) menampilkan visualisasi dan snapshot parameter teknikal entry (Trend, EMA, RSI, ATR, Volume, Session).
  - Halaman filter kustom (`DiagnosticFilters.tsx`) dengan preset simpan/muat/hapus di `localStorage` (frontend stub).
  - Migrasi database **v2** (menambahkan kolom lifecycle trade: entry/exit price, exit/updated time) dan **v3** (menambahkan tabel preset filter kustom `diagnostic_filter_presets`).
  - API endpoints backend: `GET /diagnostics/trades` (daftar terfilter), `GET /diagnostics/trades/{trade_id}` (detail snapshot), `POST /diagnostics/trades/export` (WeasyPrint PDF/CSV), `POST /diagnostics/filters` (save preset), `GET /diagnostics/filters` (list presets), dan `DELETE /diagnostics/filters/{preset_id}` (delete preset) telah siap dan diuji.

## TODO / Next Steps
- **Fase 3: Analisis Pola Kekalahan (Fase Berikutnya)**:
  - Halaman Utama Analisis Pola Kekalahan di frontend (`/diagnostics/patterns`) untuk visualisasi statistik agregat pola kegagalan dominan.
  - Endpoint backend untuk kalkulasi clustering/agregasi pola kegagalan secara periodik.
- **Fase 4: Pelacakan Perbaikan**:
  - Implementasi tabel `improvement_logs` untuk melacak track record modifikasi strategi (rekomendasi).
- **Integrasi Bot Live**:
  - Membuat parser log entry bot XAUUSD untuk dikirim ke API diagnostik secara real-time atau via upload CSV.

## Masalah Saat Ini & Keterbatasan
- Dependensi local frontend (`node_modules`) menggunakan Node `v22.21.1` sedangkan declare project meminta `>=22.22.0`. Meskipun demikian, build dan linting tetap sukses berjalan tanpa kendala.
- Eksekusi vitest penuh dari CLI di local machine sering kali melebihi limit tool timeout (30s) karena banyaknya unit test suite bawaan di repositori. Namun, pengujian fungsional terarah khusus modul diagnostics berhasil dengan cepat.

