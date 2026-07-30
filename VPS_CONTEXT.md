# VPS Context

## Info Deployment VPS
- **IP Server**: `[REDACTED_IP]`
- **OS**: Linux (Ubuntu Server/Debian)
- **Status Port**: FastAPI Backend berjalan di port `8000`, Web UI Frontend disajikan lewat build dist atau reverse proxy Nginx.

## Path Project di Server
- **Production Directory**: `/var/www/vibe-trading` atau `/home/deploy/vibe-trading`

## Service yang Digunakan
- **Web Server / Reverse Proxy**: Nginx (menangani TLS/SSL dan merutekan `/api` ke backend).
- **Process Manager**: Systemd service (misalnya `vibe-trading-backend.service`) atau Docker Compose untuk menjaga uptime runtime python api_server.
- **Database File**: Tersimpan di path `/root/.vibe-trading/` atau `/home/deploy/.vibe-trading/`.

## Command Penting
- **Melihat log backend**: `journalctl -u vibe-trading-backend.service -f --no-tail`
- **Restart service backend**: `sudo systemctl restart vibe-trading-backend.service`
- **Membangun build frontend**: `npm run build --prefix frontend`
- **Menjalankan server secara manual**: `python agent/api_server.py --port 8000 --host 127.0.0.1`
