# ============================================
# Mầm Nhỏ — Dockerfile cho Orange Pi 5 (ARM64)
# ============================================
# Build:  docker build -f Dockerfile.arm64 -t momcare:arm64 .
# Hoặc cross-build từ Windows/x86:
#   docker buildx build --platform linux/arm64 -f Dockerfile.arm64 -t momcare:arm64 .
#
# Run:    docker-compose up -d
# ============================================

# --- Stage 1: Builder (cài đặt dependencies) ---
FROM python:3.12-slim-bookworm AS builder

# 1. CÀI ĐẶT CÔNG CỤ BIÊN DỊCH TRƯỚC (Đây là bước fix lỗi)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# 2. Copy requirements
COPY requirements.txt .

# 3. Chạy pip install (Dòng này sẽ không còn lỗi nữa vì đã có Cmake và GCC ở trên)
RUN CMAKE_ARGS="-DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH=armv8.2-a+dotprod" \
    pip install --no-cache-dir --default-timeout=1000 --retries 10 --prefix=/install -r requirements.txt

# 4. Cài thêm các thư viện runtime cho CLI Voice App
RUN pip install --no-cache-dir --default-timeout=1000 --retries 10 --prefix=/install \
    SpeechRecognition \
    pygame \
    gtts \
    PyAudio


# --- Stage 2: Runtime (image nhẹ, chỉ chứa runtime) ---
FROM python:3.12-slim-bookworm AS runtime

# Thư viện hệ thống runtime cho audio + ALSA
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    libasound2 \
    libasound2-plugins \
    alsa-utils \
    portaudio19-dev \
    libportaudio2 \
    ffmpeg \
    pulseaudio-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages từ builder stage
COPY --from=builder /install /usr/local
