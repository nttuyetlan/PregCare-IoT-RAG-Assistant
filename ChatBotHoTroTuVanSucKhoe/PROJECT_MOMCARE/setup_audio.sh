#!/bin/bash
# ============================================
# setup_audio.sh - Cài đặt toàn bộ Audio Stack
# ============================================
# 
# Chức năng:
#   1. Cài dependencies hệ thống (ALSA, PortAudio)
#   2. Cài Python packages từ requirements.txt
#   3. Kiểm tra audio devices bằng check_audio.py
#   4. Tạo template .env nếu chưa có
#
# Sử dụng:
#   bash setup_audio.sh
#   
# Chạy trên: Orange Pi 5 (Debian/Ubuntu-based)
# ============================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🎵 SETUP AUDIO STACK - Mầm Nhỏ (Orange Pi 5)           ║"
echo "╚════════════════════════════════════════════════════════════╝"

# ──────────────────────────────────────────
# BƯỚC 1: Cài Dependencies Hệ Thống
# ──────────────────────────────────────────

echo ""
echo "📦 BƯỚC 1: Cài Dependencies Hệ Thống..."
echo "   (Cần quyền sudo)"
echo ""

# Kiểm tra sudo
if ! sudo -n true 2>/dev/null; then
    echo "⚠️  Cần quyền sudo để cài dependencies hệ thống"
    echo "   Nhập mật khẩu:"
    sudo -v
fi

# Cập nhật package list
echo "🔄 Cập nhật package list..."
sudo apt-get update -qq

# Cài PortAudio (cần thiết cho PyAudio)
echo "📥 Cài PortAudio19..."
sudo apt-get install -y -qq portaudio19-dev python3-dev

# Cài ALSA tools (để kiểm tra audio)
echo "📥 Cài ALSA tools..."
sudo apt-get install -y -qq alsa-utils alsa-tools libsndfile1

# Cài pygame dependencies
echo "📥 Cài pygame dependencies..."
sudo apt-get install -y -qq libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev

echo "✅ Dependencies hệ thống cài xong!"

# ──────────────────────────────────────────
# BƯỚC 2: Cài Python Packages
# ──────────────────────────────────────────

echo ""
echo "🐍 BƯỚC 2: Cài Python Packages từ requirements.txt..."
echo ""

cd "$PROJECT_ROOT"

# Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Không tìm thấy Python3!"
    exit 1
fi

# Kiểm tra pip
if ! python3 -m pip --version &> /dev/null; then
    echo "❌ Không tìm thấy pip!"
    exit 1
fi

# Cập nhật pip
echo "🔄 Cập nhật pip..."
python3 -m pip install --quiet --upgrade pip

# Cài từ requirements.txt
echo "📥 Cài Python packages..."
python3 -m pip install --quiet -r requirements.txt

echo "✅ Python packages cài xong!"

# ──────────────────────────────────────────
# BƯỚC 3: Kiểm tra PyAudio
# ──────────────────────────────────────────

echo ""
echo "🔍 BƯỚC 3: Kiểm tra PyAudio..."
echo ""

if python3 -c "import pyaudio; print('✅ PyAudio imported successfully')" 2>/dev/null; then
    echo "✅ PyAudio cài đặt thành công!"
else
    echo "❌ PyAudio không thể import!"
    echo "   Có thể PyAudio compilation thất bại"
    echo "   Thử: pip install --upgrade --force-reinstall PyAudio"
    exit 1
fi

# ──────────────────────────────────────────
# BƯỚC 4: Chạy check_audio.py
# ──────────────────────────────────────────

echo ""
echo "🎧 BƯỚC 4: Phát hiện Audio Devices..."
echo ""

python3 "$PROJECT_ROOT/scripts/check_audio.py"

# ──────────────────────────────────────────
# BƯỚC 5: Tạo .env template
# ──────────────────────────────────────────

echo ""
echo "📝 BƯỚC 5: Kiểm tra .env file..."
echo ""

ENV_FILE="$PROJECT_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    echo "✅ .env file đã tồn tại"
    echo "   Nếu cần cập nhật AUDIO_INPUT_DEVICE_INDEX:"
    echo "   - Chạy: python scripts/check_audio.py"
    echo "   - Sửa .env theo kết quả"
else
    echo "📝 Tạo .env file template..."
    cat > "$ENV_FILE" << 'EOF'
# ============================================
# Mầm Nhỏ Environment Configuration
# ============================================

# --- Audio Hardware (Orange Pi 5 / es8388) ---
# Tìm giá trị đúng bằng: python scripts/check_audio.py
AUDIO_INPUT_DEVICE_INDEX=-1     # -1 = hệ thống mặc định, hoặc 2 cho es8388
AUDIO_OUTPUT_DEVICE_INDEX=-1    # -1 = hệ thống mặc định, hoặc 2 cho es8388

# --- Voice Pipeline ---
VAD_SILENCE_TIMEOUT_MS=1800
WHISPER_COMPUTE_TYPE=int8
WHISPER_NUM_THREADS=4

# --- Logging ---
LOG_LEVEL=INFO
EOF
    echo "✅ .env template tạo thành công tại: $ENV_FILE"
fi

# ──────────────────────────────────────────
# BƯỚC 6: Test Audio Playback
# ──────────────────────────────────────────

echo ""
echo "🎵 BƯỚC 6: Test Audio Playback..."
echo ""

# Test speaker trực tiếp
read -p "Bạn có muốn test phát âm thanh không? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔊 Đang phát test audio qua es8388 (hw:2,0)..."
    
    if speaker-test -D hw:2,0 -c 2 -t sine -f 1000 -l 1 2>/dev/null; then
        echo "✅ Test audio thành công!"
        echo "   Nếu bạn nghe tiếng, audio setup hoàn tất!"
    else
        echo "⚠️  speaker-test không thành công"
        echo "   Có thể es8388 chưa hoạt động hoặc device index sai"
        echo "   Thử: speaker-test -D default  # Test thiết bị mặc định"
    fi
fi

# ──────────────────────────────────────────
# Hoàn tất
# ──────────────────────────────────────────

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    ✅ SETUP HOÀN TẤT!                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 BƯỚC TỊP THEO:"
echo ""
echo "1️⃣  Sửa .env file (nếu cần):"
echo "    nano .env"
echo "    # Cập nhật AUDIO_INPUT_DEVICE_INDEX và OUTPUT_DEVICE_INDEX"
echo ""
echo "2️⃣  Test CLI voice app (Offline mode):"
echo "    python -m src.cli_voice_app --offline"
echo ""
echo "3️⃣  Hoặc test web demo:"
echo "    python -m src.demo_app"
echo "    # Mở http://localhost:7860"
echo ""
echo "4️⃣  Nếu audio vẫn không có:"
echo "    • Kiểm tra: aplay -L  (liệt kê output devices)"
echo "    • Test speaker: speaker-test -D hw:2,0 -t sine -l 1"
echo "    • Tăng volume: amixer -D hw:2,0 sset 'Speaker' 100%"
echo ""
