"""
src/firebase_service.py — Firebase Realtime Database Service

PURPOSE:
    Kết nối real-time với Firebase để lấy thông số sức khỏe mẹ bầu
    (nhiệt độ, nhịp tim, SpO2) từ thiết bị IoT.
    
    Dùng REST API thuần (requests) thay vì firebase-admin SDK
    để tiết kiệm RAM trên Orange Pi 5 MAX.
"""

import requests
from datetime import datetime
from typing import Optional
from loguru import logger

from src.config import get_settings


class FirebaseService:
    """
    Lấy dữ liệu sức khỏe real-time từ Firebase Realtime Database.
    
    Gọi REST API: GET {db_url}/devices/{device_id}/{path}.json
    Không cần auth (Firebase rules cho phép read public).
    """
    
    def __init__(self):
        settings = get_settings()
        self._db_url = settings.firebase_db_url.rstrip("/")
        self._device_id = settings.firebase_device_id
        self._timeout = 5  # seconds
    
    def _fetch(self, path: str) -> Optional[dict]:
        """Gọi Firebase REST API, trả về dict hoặc None nếu lỗi."""
        settings = get_settings()
        secret = getattr(settings, "firebase_secret", "")
        
        url = f"{self._db_url}/devices/{self._device_id}/{path}.json"
        if secret:
            url += f"?auth={secret}"
            
        try:
            resp = requests.get(url, timeout=self._timeout)
            resp.raise_for_status()
            data = resp.json()
            if data is None:
                logger.warning(f"Firebase trả về null cho path: {path}")
            return data
        except requests.RequestException as e:
            logger.error(f"Firebase request failed ({path}): {e}")
            return None
    
    def _format_timestamp(self, ts) -> str:
        """Chuyển timestamp milliseconds → chuỗi giờ đọc được, hoặc giữ nguyên nếu đã là chuỗi."""
        if isinstance(ts, str):
            # Nếu thiết bị đã gửi lên dạng chuỗi (vd: "12:00 16/05/2026")
            return ts.replace(" ", " ngày ")
        try:
            # Nếu là số milliseconds
            dt = datetime.fromtimestamp(int(ts) / 1000)
            return dt.strftime("%H:%M ngày %d/%m")
        except (ValueError, TypeError, OSError):
            return "không rõ"
    
    def _assess_level(self, alert_level: str) -> str:
        """Dịch alertLevel sang tiếng Việt."""
        mapping = {
            "normal": "bình thường ✅",
            "warning": "cảnh báo ⚠️",
            "danger": "nguy hiểm 🔴",
        }
        return mapping.get(str(alert_level).lower(), alert_level)
    
    def get_latest(self) -> Optional[dict]:
        """Lấy lần đo gần nhất."""
        return self._fetch("latest")
    
    def get_alerts(self) -> Optional[dict]:
        """Lấy danh sách cảnh báo."""
        return self._fetch("alerts")
    
    def get_recent_readings(self, limit: int = 10) -> list[dict]:
        """
        Lấy N lần đo gần nhất từ readings.
        Fetch tất cả rồi sort + slice local.
        """
        data = self._fetch("readings")
        if not data or not isinstance(data, dict):
            return []
        
        readings = list(data.values())
        # Sắp xếp theo timestampMs (ưu tiên) hoặc timestamp
        readings.sort(key=lambda x: x.get("timestampMs", x.get("timestamp", 0)) if isinstance(x.get("timestampMs", x.get("timestamp", 0)), (int, float)) else 0)
        return readings[-limit:]  # Lấy N phần tử cuối (gần nhất)
    
    def get_health_summary(self) -> str:
        """
        Tạo bản tóm tắt sức khỏe dạng text để inject vào LLM context.
        """
        lines = []
        
        # --- Thông số hiện tại ---
        latest = self.get_latest()
        if latest:
            ts_str = self._format_timestamp(latest.get("timestamp", 0))
            level = self._assess_level(latest.get("alertLevel", ""))
            
            lines.append(f"THÔNG SỐ SỨC KHỎE HIỆN TẠI CỦA MẸ (đo lúc {ts_str}):")
            lines.append(f"- Nhiệt độ cơ thể: {latest.get('temperature', '?')}°C")
            lines.append(f"- Nhịp tim: {latest.get('heartRate', '?')} bpm")
            lines.append(f"- Nồng độ oxy trong máu (SpO2): {latest.get('spo2', '?')}%")
            lines.append(f"- Trạng thái chung: {level}")
        else:
            lines.append("KHÔNG THỂ LẤY THÔNG SỐ SỨC KHỎE TỪ THIẾT BỊ ĐO.")
        
        # --- Cảnh báo gần đây ---
        alerts = self.get_alerts()
        if alerts and isinstance(alerts, dict):
            unresolved = [
                a for a in alerts.values() 
                if isinstance(a, dict) and not a.get("resolved", True)
            ]
            if unresolved:
                # Sắp xếp theo thời gian, lấy 5 cảnh báo gần nhất
                unresolved.sort(key=lambda x: x.get("timestampMs", x.get("timestamp", 0)) if isinstance(x.get("timestampMs", x.get("timestamp", 0)), (int, float)) else 0, reverse=True)
                lines.append("")
                lines.append("CẢNH BÁO CHƯA GIẢI QUYẾT GẦN ĐÂY:")
                for alert in unresolved[:5]:
                    ts = self._format_timestamp(alert.get("timestamp", 0))
                    msg = alert.get("message", "Không rõ")
                    val = alert.get("value", "?")
                    lines.append(f"- {msg}: {val} (lúc {ts})")
        
        # --- Xu hướng 10 lần đo gần nhất ---
        readings = self.get_recent_readings(10)
        if len(readings) >= 3:
            temps = [float(r.get("temperature", 0)) for r in readings if "temperature" in r]
            hrs = [float(r.get("heartRate", 0)) for r in readings if "heartRate" in r]
            spo2s = [float(r.get("spo2", 0)) for r in readings if "spo2" in r]
            
            if temps and hrs and spo2s:
                avg_temp = sum(temps) / len(temps)
                avg_hr = sum(hrs) / len(hrs)
                avg_spo2 = sum(spo2s) / len(spo2s)
                
                lines.append("")
                lines.append(f"XU HƯỚNG {len(readings)} LẦN ĐO GẦN NHẤT:")
                lines.append(f"- Nhiệt độ TB: {avg_temp:.1f}°C (dao động {min(temps):.1f}-{max(temps):.1f}°C)")
                lines.append(f"- Nhịp tim TB: {avg_hr:.0f} bpm (dao động {min(hrs):.0f}-{max(hrs):.0f} bpm)")
                lines.append(f"- SpO2 TB: {avg_spo2:.0f}% (dao động {min(spo2s):.0f}-{max(spo2s):.0f}%)")
        
        summary = "\n".join(lines)
        logger.info(f"Firebase health summary: {len(lines)} lines")
        return summary
