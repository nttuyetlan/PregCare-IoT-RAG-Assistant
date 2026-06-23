#!/bin/bash
# ============================================
# Mầm Nhỏ — Script triển khai trên Orange Pi 5
# ============================================
# Sử dụng:
#   chmod +x deploy_orangepi.sh
#   ./deploy_orangepi.sh
# ============================================

set -e  # Dừng nếu có lỗi

echo "============================================"
echo "🌱 Mầm Nhỏ — Triển khai trên Orange Pi 5"
echo "============================================"
echo ""

# ── Bước 0: Kiểm tra Docker ──
echo "🔍 Kiểm tra Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker chưa được cài đặt!"
    echo "   Cài đặt: curl -fsSL https://get.docker.com | sh"
    echo "   Thêm user: sudo usermod -aG docker \$USER"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose chưa được cài đặt!"
    echo "   Cài đặt: sudo apt-get install docker-compose-plugin"
    exit 1
fi

echo "✅ Docker $(docker --version | cut -d' ' -f3)"

# ── Bước 1: Tạo thư mục cần thiết ──
echo ""
echo "📁 Tạo thư mục..."
mkdir -p models logs vector_db data tts_cache
echo "✅ Thư mục đã sẵn sàng"

# ── Bước 2: Kiểm tra models ──
echo ""
echo "🔍 Kiểm tra mô hình AI..."
MISSING_MODELS=0

if [ ! -d "models/vietnamese-sbert" ]; then
    echo "❌ Thiếu: models/vietnamese-sbert (embedding)"
    MISSING_MODELS=1
fi

if [ ! -d "models/qwen2.5-1.5b" ]; then
    echo "❌ Thiếu: models/qwen2.5-1.5b (intent + RAG)"
    MISSING_MODELS=1
fi

if [ $MISSING_MODELS -eq 1 ]; then
    echo ""
    echo "⚠️  Cần tải models trước khi chạy:"
    echo "   pip install huggingface-hub sentence-transformers"
    echo "   python scripts/download_models.py --model sbert"
    echo "   python scripts/download_models.py --model qwen1.5b"
    echo ""
    read -p "Bạn có muốn tiếp tục build Docker không? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        exit 1
    fi
else
    echo "✅ Tất cả mô hình đã có"
fi

# ── Bước 3: Kiểm tra dữ liệu ──
echo ""
echo "🔍 Kiểm tra dữ liệu..."
if [ ! -f "data/thai_ky_data.jsonl" ]; then
    echo "❌ Thiếu: data/thai_ky_data.jsonl"
    exit 1
fi
RECORD_COUNT=$(wc -l < data/thai_ky_data.jsonl)
echo "✅ Dataset: ${RECORD_COUNT} records"

# ── Bước 4: Kiểm tra vector_db ──
echo ""
echo "🔍 Kiểm tra ChromaDB..."
if [ ! -d "vector_db/chroma.sqlite3" ] && [ -z "$(ls -A vector_db 2>/dev/null)" ]; then
    echo "⚠️  ChromaDB chưa được build"
    echo "   Sẽ build sau khi Docker container chạy"
    BUILD_DB=1
else
    echo "✅ ChromaDB đã có"
    BUILD_DB=0
fi

# ── Bước 5: Copy .env nếu chưa có ──
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Tạo file .env từ .env.example..."
    cp .env.example .env
    echo "✅ File .env đã tạo"
fi

# ── Bước 6: Build Docker image ──
echo ""
echo "🐳 Build Docker image (có thể mất 5-15 phút lần đầu)..."
docker compose build

echo "✅ Build hoàn tất!"

# ── Bước 7: Build ChromaDB nếu cần ──
if [ $BUILD_DB -eq 1 ]; then
    echo ""
    echo "📊 Build ChromaDB vector database..."
    docker compose run --rm mam-nho-ai python -m src.build_db --reset
    echo "✅ ChromaDB đã build xong"
fi

# ── Bước 8: Khởi chạy ──
echo ""
echo "🚀 Khởi chạy Mầm Nhỏ..."
docker compose up -d

echo ""
echo "============================================"
echo "✅ TRIỂN KHAI THÀNH CÔNG!"
echo "============================================"
echo ""
echo "📋 Các lệnh hữu ích:"
echo "  docker compose logs -f          # Xem logs"
echo "  docker compose exec mam-nho-ai bash  # Vào container"
echo "  docker compose down             # Dừng"
echo "  docker compose restart          # Khởi động lại"
echo ""
echo "🎤 Để sử dụng giọng nói:"
echo "  docker attach mam_nho_assistant"
echo "  (Nhấn ENTER để thu âm, gõ text rồi ENTER để chat)"
echo "  (Ctrl+P, Ctrl+Q để thoát mà không dừng container)"
echo ""
echo "🌐 Để chạy Gradio Web Demo:"
echo "  docker compose exec mam-nho-ai python -m src.demo_app"
echo "  → Mở http://<IP_ORANGEPI>:7860"
echo ""
