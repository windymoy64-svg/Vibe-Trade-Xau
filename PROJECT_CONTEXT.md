# Project Context

## Tujuan Project
Membangun aplikasi **Production Strategy Diagnostics** terintegrasi di dalam ekosistem bot trading **Vibe-Trading** (fokus pada XAUUSD). Aplikasi ini bertujuan untuk mendiagnosis akar masalah teknis (seperti market regime mismatch, session bias, indicator false signals) saat bot mengalami kerugian (Loss/Stop Loss) berdasarkan bukti data nyata, bukan asumsi manual.

## Stack Teknologi
- **Frontend**: React 19 + Vite + TypeScript + Tailwind CSS (shadcn/ui layout tokens).
- **Backend API**: FastAPI (Python 3.13) yang terintegrasi secara modular dengan auth local/key.
- **Database**: SQLite dengan WAL mode untuk referential integrity dan user-scoped isolation.
- **Migration**: Schema versioning manual idempotent memanfaatkan `PRAGMA user_version` (tanpa ORM eksternal).
- **PDF Export**: PDF generation berbasis HTML menggunakan **WeasyPrint** yang telah menjadi standar project.

## Struktur Folder
- `/frontend`: Aplikasi client-side React.
  - `/src/pages`: Halaman utama (`DiagnosticsDashboard`, `DiagnosticTrades`, `DiagnosticTradeDetail`, `DiagnosticFilters`).
  - `/src/components/diagnostics`: Komponen reusable (`CommonCauseStats`, `SuspectedCauseChart`, `RecentTrades`, `QuickInsight`, `MarketRegimeFilter`, `TradingSessionFilter`, `TechnicalIndicatorFilter`).
  - `/src/data`: Modul fallback data tiruan (`diagnostics-dashboard`, `diagnostic-trades`).
- `/agent`: Service backend Python.
  - `/src/diagnostics`: Modul engine & SQLite store (`store.py`).
  - `/src/api`: Route API FastAPI (`diagnostics_routes.py`).
  - `/tests`: Test suite (`test_diagnostics_store.py`, `test_diagnostics_api.py`).

## Keputusan Teknis Penting
1. **Pemisahan Layer (Frontend-First)**: UI dibangun lengkap terlebih dahulu dengan modular stub data tiruan yang memiliki visualisasi responsif, disusul dengan implementasi API backend yang mengikat data riil tersebut.
2. **Konektivitas Fleksibel**: Frontend menggunakan callback fetch async yang otomatis mendeteksi ketersediaan API backend. Jika offline/error, UI akan secara halus menggunakan Preview Data dan menandainya dengan badge agar testing frontend tidak terhambat.
3. **Penyimpanan SQLite Sederhana**: Database diagnostics menggunakan file SQLite terpisah (`diagnostics.db`) yang dialokasikan di folder home user `.vibe-trading` agar portabel dan aman.
4. **Idempotensi Migrasi**: Migrasi database ditulis dalam script SQL terisolasi yang naik bertahap berdasarkan cek versi `user_version` saat inisialisasi class `DiagnosticsStore`.
