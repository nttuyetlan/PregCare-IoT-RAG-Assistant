import os
from huggingface_hub import hf_hub_download, snapshot_download

def download_qwen():
    print("Downloading Qwen 1.5B GGUF...")
    os.makedirs("models/qwen2.5-1.5b", exist_ok=True)
    hf_hub_download(
        repo_id="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        filename="qwen2.5-1.5b-instruct-q4_k_m.gguf",
        local_dir="models/qwen2.5-1.5b"
    )

def download_sbert():
    print("Downloading Vietnamese SBERT...")
    snapshot_download(
        repo_id="keepitreal/vietnamese-sbert",
        local_dir="models/vietnamese-sbert"
    )

if __name__ == "__main__":
    download_qwen()
    download_sbert()
    print("Models downloaded successfully!")
