# 🌱 Mầm Nhỏ — Trợ lý Sản khoa AI (Edge AI)

> Trợ lý ảo sản khoa chạy 100% offline trên Orange Pi 5,
> hỗ trợ trao đổi bằng giọng nói tiếng Việt.

---

## 🚀 Hướng dẫn cài đặt và chạy nhanh

### Bước 1: Cài đặt dependencies

```bash
# Clone project (nếu chưa có)
cd d:\HK2-Year4\IoT\PROJECT_MOMCARE

# Cài đặt thư viện Python
pip install -r requirements.txt

# Cài thêm cho demo web (Gradio + gTTS fallback)
pip install gradio gtts soundfile
```

### Bước 2: Tải mô hình lượng tử hóa

```bash
# Cài thư viện tải model
pip install huggingface-hub sentence-transformers

# Tải TẤT CẢ mô hình (~6.3 GB tổng)
python scripts/download_models.py

# Hoặc tải từng mô hình:
python scripts/download_models.py --model sbert     # Vietnamese-SBERT (400MB)
python scripts/download_models.py --model qwen1.5b  # Qwen 1.5B (1GB)
python scripts/download_models.py --model qwen7b    # Qwen 7B (4.4GB)
python scripts/download_models.py --model whisper   # Faster-Whisper (500MB)

# Kiểm tra trạng thái
python scripts/download_models.py --model status
```

### Bước 3: Xây dựng vector database

```bash
python -m src.build_db
# Hoặc reset và xây lại:
python -m src.build_db --reset
```

### Bước 4: Chạy Demo Chatbot

```bash
# 🌐 Chạy giao diện web (có mic + chat)
python -m src.demo_app

# Mở trình duyệt: http://localhost:7860
```

Hoặc test nhanh bằng terminal (không cần mic):
```bash
python -m src.voice_pipeline
```

---

## 🎤 Cách sử dụng Demo Web

1. Mở `http://localhost:7860` trên trình duyệt
2. Chọn **giai đoạn thai kỳ** phù hợp (dropdown bên trái)
3. Có 2 cách nhập:
   - **Tab "Văn bản"**: Gõ câu hỏi → nhấn "Gửi"
   - **Tab "Giọng nói"**: Nhấn 🎤 thu âm → nói → nhấn lại để dừng → nhấn "Gửi giọng nói"
4. Câu trả lời hiển thị trong khung chat + phát audio tự động

---

## 📂 Cấu trúc dự án

```
PROJECT_MOMCARE/
├── data/
│   └── thai_ky_data.jsonl       # Dữ liệu y khoa (47 chunks từ Cẩm Nang Thai Kỳ)
├── models/                       # Mô hình AI (tải bằng script)
│   ├── qwen2.5-7b-instruct/     # LLM chính (RAG)
│   ├── qwen2.5-1.5b/            # LLM phụ (phân loại ý định)
│   ├── faster-whisper-small/    # STT tiếng Việt
│   └── vietnamese-sbert/        # Nhúng vector
├── vector_db/                    # ChromaDB (tạo bằng build_db.py)
├── logs/                         # Audit logs
├── scripts/
│   └── download_models.py       # Tải mô hình
├── src/
│   ├── config.py                # Cấu hình tập trung
│   ├── build_db.py              # JSONL → ChromaDB
│   ├── rag_engine.py            # RAG + Dual LLM
│   ├── intent_classifier.py     # Phân loại ý định (Qwen 1.5B)
│   ├── safety_checker.py        # Phát hiện nguy hiểm
│   ├── conversation_memory.py   # Bộ nhớ hội thoại (3 lượt)
│   ├── stt_service.py           # Nhận diện giọng nói
│   ├── tts_service.py           # Tổng hợp giọng nói
│   ├── voice_pipeline.py        # Pipeline âm thanh
│   └── demo_app.py              # Giao diện Gradio demo
├── tests/
│   ├── test_rag.py              # Test RAG + utilities
│   └── test_safety.py           # Test an toàn y tế
├── Dockerfile                    # Docker ARM64
├── docker-compose.yml            # Deploy Orange Pi 5
├── requirements.txt              # Dependencies
└── .env.example                  # Biến môi trường mẫu
```

---

## 🔧 Mô hình lượng tử hóa

| Mô hình | Lượng tử | Kích thước | Mục đích |
|---|---|---|---|
| Qwen2.5-7B-Instruct | Q4_K_M | ~4.4 GB | Sinh câu trả lời y khoa |
| Qwen2.5-1.5B-Instruct | Q4_K_M | ~1.0 GB | Phân loại ý định + viết lại câu hỏi |
| Faster-Whisper small | int8 | ~500 MB | Nhận diện giọng nói tiếng Việt |
| Vietnamese-SBERT | FP32 | ~400 MB | Nhúng vector cho ChromaDB |

> **Q4_K_M** giữ lại ~95% chất lượng so với FP16.
> Các layer quan trọng (attention) được giữ ở Q6_K.

---

## ⚡ Deploy trên Orange Pi 5

### Cách 1: Script tự động (khuyến nghị)

```bash
# Copy project vào Orange Pi 5 (qua SCP hoặc USB)
scp -r PROJECT_MOMCARE/ orangepi@<IP>:~/

# SSH vào Orange Pi 5
ssh orangepi@<IP>
cd ~/PROJECT_MOMCARE

# Tải models trước (~6GB)
pip install huggingface-hub sentence-transformers
python scripts/download_models.py

# Chạy script deploy
chmod +x deploy_orangepi.sh
./deploy_orangepi.sh
```

### Cách 2: Thủ công

```bash
# Build image ARM64
docker compose build

# Build ChromaDB (47 records)
docker compose run --rm mam-nho-ai python -m src.build_db --reset

# Chạy container
docker compose up -d

# Attach để sử dụng giọng nói
docker attach mam_nho_assistant
# → Nhấn ENTER để thu âm, gõ text rồi ENTER để chat
# → Ctrl+P, Ctrl+Q để thoát mà không dừng container

# Xem logs
docker compose logs -f
```

### Cấu trúc Docker

| File | Mô tả |
|---|---|
| `Dockerfile.arm64` | Multi-stage build tối ưu cho ARM64 |
| `docker-compose.yml` | Orchestration với volume mounts |
| `.dockerignore` | Loại trừ models/logs khỏi build context |
| `deploy_orangepi.sh` | Script triển khai tự động |

> **Lưu ý**: Models (~6GB) được mount qua volume, KHÔNG bake vào image.


---

## 🧪 Chạy tests

```bash
python -m pytest tests/ -v
```

---

## ⚠️ Lưu ý quan trọng

- Mầm Nhỏ **KHÔNG** thay thế tư vấn y khoa chuyên nghiệp
- Mọi hội thoại được **ghi log** phục vụ audit y tế
- Dữ liệu y khoa phải được **bác sĩ sản khoa ký duyệt**
- Hệ thống chạy **100% offline**, không gửi dữ liệu ra ngoài
