import os
import requests
import subprocess
from loguru import logger
from src.config import get_settings

class YouTubeService:
    def __init__(self):
        self._settings = get_settings()
        self.current_process = None

    def search_video(self, query: str) -> str | None:
        # Xóa bớt các từ khóa không cần thiết để search chuẩn hơn
        query_clean = query.lower().replace("mở bài hát", "").replace("phát bài hát", "").replace("nghe nhạc", "").replace("mở nhạc", "").replace("bài hát", "").strip()
        
        api_key = self._settings.youtube_api_key or os.getenv("YOUTUBE_API_KEY", "")
        if not api_key:
            logger.error("YOUTUBE_API_KEY chưa được thiết lập trong .env")
            return None, None
        
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query_clean,
            "type": "video",
            "videoCategoryId": "10",  # Chỉ tìm trong danh mục m nhạc (Music)
            "maxResults": 1,
            "key": api_key
        }
        try:
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            if "items" in data and len(data["items"]) > 0:
                video_id = data["items"][0]["id"]["videoId"]
                title = data["items"][0]["snippet"]["title"]
                logger.info(f"Tìm thấy video: {title} (ID: {video_id})")
                return video_id, title
            else:
                logger.warning(f"Không tìm thấy video nào cho: {query_clean}")
                return None, None
        except Exception as e:
            logger.error(f"Lỗi tìm kiếm YouTube: {e}")
            return None, None

    def play_video(self, video_id: str):
        self.stop_video()
        url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info(f"Mở Chromium phát: {url}")
        
        # Lệnh mở chromium-browser chế độ kiosk, sử dụng profile của user orangepi
        cmd = [
            "chromium-browser",
            "--user-data-dir=/home/orangepi/.config/chromium",
            "--profile-directory=Default",
            "--kiosk",
            "--autoplay-policy=no-user-gesture-required",
            "--disable-infobars",
            "--disable-session-crashed-bubble",
            "--no-sandbox",
            url
        ]
        
        try:
            # Ép Chromium phát âm thanh qua card 2 (es8388 - cổng tai nghe)
            env = os.environ.copy()
            env["ALSA_CARD"] = "2"
            env["DISPLAY"] = ":0"
            
            # Chạy background process
            self.current_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env=env
            )
            return True
        except Exception as e:
            logger.error(f"Lỗi mở Chromium: {e}")
            return False
            
    def stop_video(self):
        if self.current_process and self.current_process.poll() is None:
            logger.info("Đang tắt Chromium...")
            self.current_process.terminate()
            try:
                self.current_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.current_process.kill()
            self.current_process = None
            # Force kill để đảm bảo không bị kẹt process
            os.system("pkill -f chromium-browser")
            return True
        return False

    def is_playing(self) -> bool:
        if self.current_process and self.current_process.poll() is None:
            return True
        return False     
