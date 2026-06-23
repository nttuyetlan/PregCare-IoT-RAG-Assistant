#!/bin/bash
# Script tự động cấu hình Mầm Nhỏ chạy nền khi khởi động mạch Orange Pi 5

echo "🌱 Đang cài đặt Mầm Nhỏ chạy tự động (Autostart)..."

SERVICE_FILE="/etc/systemd/system/mamnho.service"
PROJECT_DIR=$(pwd)
USER_NAME=$USER

# Tạo file service
sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Mam Nho AI Voice Assistant
After=network.target sound.target

[Service]
# Chạy quyền root để truy cập GPIO và thiết bị âm thanh
User=root
WorkingDirectory=$PROJECT_DIR
Environment="PYTHONPATH=$PROJECT_DIR"
Environment="KMP_DUPLICATE_LIB_OK=TRUE"
Environment="DISPLAY=:0"

# Lệnh khởi chạy (Thêm --offline nếu muốn dùng Whisper offline)
ExecStart=/usr/bin/python3 src/cli_voice_app.py --offline

Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog

[Install]
WantedBy=multi-user.target
EOL

# Tải lại systemd và kích hoạt service
sudo systemctl daemon-reload
sudo systemctl enable mamnho.service
sudo systemctl restart mamnho.service

echo "✅ Cài đặt hoàn tất!"
echo "----------------------------------------"
echo "🛠️  Để xem log chạy ngầm, dùng lệnh:"
echo "    sudo journalctl -u mamnho.service -f"
echo "🛑 Để dừng chạy ngầm:"
echo "    sudo systemctl stop mamnho.service"
echo "▶️ Để chạy lại:"
echo "    sudo systemctl start mamnho.service"
echo "----------------------------------------"
