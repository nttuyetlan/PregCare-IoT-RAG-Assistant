//CodeChinhThuc

#include <AudioFileSource.h>
#include <AudioFileSourceBuffer.h>
#include <AudioFileSourceFATFS.h>
#include <AudioFileSourceFS.h>
#include <AudioFileSourceFunction.h>
#include <AudioFileSourceHTTPStream.h>
#include <AudioFileSourceICYStream.h>
#include <AudioFileSourceID3.h>
#include <AudioFileSourceLittleFS.h>
#include <AudioFileSourcePROGMEM.h>
#include <AudioFileSourceSD.h>
#include <AudioFileSourceSPIFFS.h>
#include <AudioFileSourceSPIRAMBuffer.h>
#include <AudioFileSourceSTDIO.h>
#include <AudioFileStream.h>
#include <AudioGenerator.h>
#include <AudioGeneratorAAC.h>
#include <AudioGeneratorFLAC.h>
#include <AudioGeneratorMIDI.h>
#include <AudioGeneratorMOD.h>
#include <AudioGeneratorMP3.h>
#include <AudioGeneratorMP3a.h>
#include <AudioGeneratorOpus.h>
#include <AudioGeneratorRTTTL.h>
#include <AudioGeneratorTalkie.h>
#include <AudioGeneratorWAV.h>
#include <AudioLogger.h>
#include <AudioOutput.h>
#include <AudioOutputBuffer.h>
#include <AudioOutputFilterBiquad.h>
#include <AudioOutputFilterDecimate.h>
#include <AudioOutputI2S.h>
#include <AudioOutputI2SNoDAC.h>
#include <AudioOutputMixer.h>
#include <AudioOutputNull.h>
#include <AudioOutputPWM.h>
#include <AudioOutputSPDIF.h>
#include <AudioOutputSPIFFSWAV.h>
#include <AudioOutputSTDIO.h>
#include <AudioOutputSerialWAV.h>
#include <AudioOutputULP.h>
#include <AudioStatus.h>
#include <ESP8266Audio.h>
#include <spiram-fast.h>




// /*
// ╔══════════════════════════════════════════════════════════════╗
// ║     HUONG DAN TOAN BO — PREGCARE v5.1                       ║
// ╠══════════════════════════════════════════════════════════════╣
// ║                                                              ║
// ║  1. TOGGLE REAL ↔ SIM MODE                                   ║
// ║  ────────────────────────────────────────────────────────    ║
// ║  Giu BTN1 (GPIO2) trong 3 giay → nghe 3 tieng beep           ║
// ║  OLED goc phai hien thi [REAL] hoac [SIM] nhay nhap           ║
// ║  Serial Monitor: go "sim" + Enter                             ║
// ║                                                              ║
// ║  Trong Sim Mode:                                              ║
// ║  • Man hinh Heart hien thi du lieu gia lap                    ║
// ║  • Man hinh 3 (Motion) → Sim Control Screen                  ║
// ║  • Serial: s0/s1/s2/s3 chon scenario canh bao                 ║
// ║  • MPU fall detection TAT (khong gia lap duoc vat ly)         ║
// ║  • Serial: "fall" → mo phong te nga                           ║
// ║                                                              ║
// ║  2. DO NGON TAY — THAY DOI SO VOI CO TAY                     ║
// ║  ────────────────────────────────────────────────────────    ║
// ║  Cach dat ngon tay DUNG:                                      ║
// ║  • Dat dau ngon tay (khong phai mong) len cam bien            ║
// ║  • Khong an qua manh (cat mach mau → sai so)                  ║
// ║  • Khong an qua nhe (tiep xuc kem → mat tin hieu)             ║
// ║  • Ap luc trung binh: nhu khi bam phim keyboard               ║
// ║  • Giu yen it nhat 30 giay de co ket qua on dinh              ║
// ║                                                              ║
// ║  Nguong IR (ngon tay cao hon co tay):                         ║
// ║  • IR_CONTACT_THRESH  = 50000 (co tay: 8000)                  ║
// ║  • RED_CONTACT_THRESH = 5000  (co tay: 800)                   ║
// ║  • Neu IR < 50000: an nganngon tay xuat hien them             ║
// ║  • Neu IR > 200000: an qua manh → giam ap luc                 ║
// ║                                                              ║
// ║  3. HE THONG CANH BAO 3 TANG — PHAN CUNG                     ║
// ║  ────────────────────────────────────────────────────────    ║
// ║                                                              ║
// ║  SO DO DAU DAY MOTOR RUNG (Coin Motor 3V):                    ║
// ║                                                              ║
// ║  ESP32-C3          MOSFET IRLZ44N          Motor             ║
// ║  GPIO10 ─R10kΩ─── Gate (G)                  (+)             ║
// ║                    Drain (D) ─────────── Day do              ║
// ║  3V3 ──────────────────────────────────── Day do             ║
// ║                    Source (S) ─── GND                        ║
// ║  GND ──────────────────────────────────── Day den (-)        ║
// ║                                                              ║
// ║  • MOSFET: IRLZ44N (logic-level, 5A, TO-220)                 ║
// ║    hoac 2N7000 (100mA, TO-92) — 2N7000 du cho motor 60-80mA  ║
// ║  • R10kΩ: han vao giua GPIO10 va Gate de chong dong ngược     ║
// ║  • Diot Flyback: 1N4148 song song voi motor                   ║
// ║    Cathode → Day do (+), Anode → Day den (-)                  ║
// ║    Bao ve ESP32 khoi xung dien nguoc khi motor dung           ║
// ║                                                              ║
// ║  KIEM TRA:                                                    ║
// ║  Serial: "breath" → Motor rung 4s-dung 2s-rung 6s            ║
// ║  Serial: "test1"  → Tang 1: rung theo ho hap                 ║
// ║  Serial: "test2"  → Tang 2: rung manh theo nhip              ║
// ║  Serial: "test3"  → Tang 3: rung lien tuc + SOS              ║
// ║                                                              ║
// ║  4. 3 TANG CANH BAO — LOGIC                                   ║
// ║  ────────────────────────────────────────────────────────    ║
// ║  TANG 1 (Warning) — Motor rung theo ho hap 4-2-6s:           ║
// ║   Dieu kien: BPM > 105  OR  SpO2 94-95%  OR  Temp > 37.5°C   ║
// ║   Tac dong: breathing assist + am thanh nhe                   ║
// ║   OLED: huong dan tho sau, progress bar pha ho hap            ║
// ║   Ket thuc: BTN2 xac nhan  OR  chi so on dinh 20s             ║
// ║                                                              ║
// ║  TANG 2 (Danger) — Motor rung manh 400ms-200ms:              ║
// ║   Dieu kien: BPM > 120  OR  SpO2 < 93%  OR  Temp > 38°C      ║
// ║   Tac dong: rung nhip manh + am thanh canh bao                ║
// ║   OLED: yeu cau nghi ngoi, hien thi li do                     ║
// ║   Ket thuc: BTN2 ha tang 1 bac OR  chi so on dinh 20s         ║
// ║                                                              ║
// ║  TANG 3 (Emergency) — Motor rung lien tuc:                   ║
// ║   Dieu kien: BPM>140 OR BPM<45 OR SpO2<90 OR te nga          ║
// ║   Tac dong: rung max + SOS sound + Telegram + OLED khan cap   ║
// ║   Ket thuc: Chi khi user BTN2 xac nhan + chi so on dinh      ║
// ║                                                              ║
// ║  5. NUT BAM TONG HOP v5.1                                     ║
// ║  ────────────────────────────────────────────────────────    ║
// ║  BTN1 (GPIO2):                                                ║
// ║  ┌──────────┬───────────────────────────────────────────┐    ║
// ║  │ Ngan     │ Chuyen man hinh (0→1→2→3→0, bo qua 4)     │    ║
// ║  │ Giu 2s   │ Bat/tat beep tick theo nhip tim            │    ║
// ║  │ Giu 3s   │ Toggle REAL ↔ SIM mode           ← MOI    │    ║
// ║  │ Giu 5s   │ Gui SOS Telegram thu cong                  │    ║
// ║  └──────────┴───────────────────────────────────────────┘    ║
// ║                                                              ║
// ║  BTN2 (GPIO3):                                                ║
// ║  ┌──────────┬───────────────────────────────────────────┐    ║
// ║  │ 1 lan    │ Xac nhan OK / Ha tang canh bao 1 bac       │    ║
// ║  │ 2 lan    │ Mo man hinh Alert Status (screen 4)         │    ║
// ║  │ Giu 3s   │ SOS khan cap + Telegram ngay lap tuc        │    ║
// ║  └──────────┴───────────────────────────────────────────┘    ║
// ║                                                              ║
// ║  6. SERIAL COMMANDS (115200 baud)                             ║
// ║  ────────────────────────────────────────────────────────    ║
// ║  help        Hien thi toan bo lenh                           ║
// ║  sim         Toggle Real/Sim mode                            ║
// ║  s0/s1/s2/s3 Chon scenario (khi dang sim)                    ║
// ║  fall        Mo phong te nga (chi trong sim)                 ║
// ║  test1/2/3   Kich hoat canh bao tang 1/2/3                   ║
// ║  reset       Reset tat ca canh bao                           ║
// ║  sos         Test gui Telegram                               ║
// ║  breath      Test breathing assist motor                     ║
// ║  info        Hien thi trang thai day du                      ║
// ║                                                              ║
// ╚══════════════════════════════════════════════════════════════╝
// */



/*
  PREGCARE BAND v5.4 — ESP32-C3 Super Mini
  =========================================
  THAY ĐỔI SO VỚI v5.3:
  [1] Xóa hoàn toàn Google TTS realtime (AudioFileSourceHTTPStream, MP3)
      → Thay bằng LittleFS WAV local — zero lag, không cần WiFi để phát âm
  [2] Thay AudioGeneratorMP3 → AudioGeneratorWAV
  [3] Thay AudioFileSourceHTTPStream → AudioFileSourceLittleFS
  [4] ttsSpeak(String) → playClip(AudioClip) — enum-based, type-safe
  [5] Xóa buildTTSUrl(), TTS_BUFFER_SIZE, wifiOK check trong TTS
  [6] Thêm LittleFS.begin() trong setup()
  [7] WiFi vẫn dùng cho NTP + Telegram SOS (không ảnh hưởng audio)
  [8] updateTTSStateMachine() hoàn toàn dùng playClip()
  [9] Tất cả ttsSpeak() call trong code được thay bằng playClip()

  CẤU TRÚC THƯ MỤC SKETCH:
  PregCare/
  ├── PregCare_v5_4.ino
  └── data/                  ← upload bằng LittleFS Data Upload Tool
      ├── warn1.wav           (Cảnh báo cấp một. Hãy thở đều theo hướng dẫn.)
      ├── danger1.wav         (Nguy hiểm cấp hai! Ngồi nghỉ ngay, gọi người thân!)
      ├── emer1.wav           (Khẩn cấp! Gọi một một lăm ngay lập tức!)
      ├── breath_in.wav       (Hít vào, bốn giây)
      ├── breath_hold.wav     (Giữ lại, bảy giây)
      ├── breath_out.wav      (Thở ra, tám giây)
      ├── breath_done.wav     (Bạn đã thở xong ba vòng. Cảm giác tốt hơn chưa?)
      ├── danger_rest.wav     (Hãy ngồi nghỉ ngay. Gọi người thân bên cạnh bạn.)
      ├── emer_call.wav       (Khẩn cấp! Gọi một một lăm ngay!)
      ├── fall.wav            (Phát hiện té ngã! Gọi cấp cứu ngay!)
      ├── sos_sent.wav        (Đã gửi tin nhắn SOS.)
      ├── sos_fail.wav        (Gửi SOS thất bại. Kiểm tra WiFi.)
      ├── confirmed.wav       (Đã xác nhận. Tiếp tục theo dõi.)
      ├── normal.wav          (Các chỉ số đã trở về bình thường. Nghỉ ngơi nhé.)
      ├── sim_on.wav          (Chuyển sang chế độ mô phỏng.)
      ├── real_on.wav         (Chuyển sang chế độ đo thực.)
      ├── ready.wav           (Mầm nhỏ đã sẵn sàng. Chúc bạn sức khỏe tốt.)
      ├── spo2_low.wav        (Cảnh báo! SpO2 thấp!)
      ├── bpm_bad.wav         (Cảnh báo! Nhịp tim bất thường!)
      ├── sos_manual.wav      (Đang gửi SOS khẩn cấp!)
      ├── confirm_warn.wav    (Đã xác nhận cảnh báo. Cảm ơn bạn.)
      └── confirm_fall.wav    (Đã xác nhận bình thường sau té ngã.)

  FORMAT WAV: 16kHz, mono, 16-bit PCM (hoặc 8-bit để tiết kiệm flash)
  TOOL UPLOAD: https://github.com/earlephilhower/arduino-littlefs-upload

  PARTITION: chọn "No OTA (2MB APP/2MB SPIFFS)" trong Arduino IDE
             Tools → Partition Scheme → No OTA (2MB APP/2MB SPIFFS)

  SERIAL COMMANDS:
   test1/2/3  sim  s0-s3  fall  sos  reset
   breath  clip <n>  ttson  ttsoff  vol+  vol-  info  lsfs

  BTN1: Ngắn=màn / 3s=SIM toggle / 5s=SOS
  BTN2 (REAL): 1x=xác nhận / 2x=Alert / 3s=SOS
  BTN2 (SIM):  1x=đổi Scenario / 3s=SOS
*/

// =====================================================================
// INCLUDES
// =====================================================================
#include <Wire.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <time.h>
#include <LittleFS.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <Adafruit_MLX90614.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include "MAX30105.h"
#include <math.h>


// ── ESP8266Audio (LittleFS + WAV) ────────────────────────────────────
#include "AudioGeneratorWAV.h"
#include "AudioFileSourceLittleFS.h"
#include "AudioOutputI2S.h"



// =====================================================================
// ENUMS
// =====================================================================
#define BODY_TEMP_OFFSET 2.0f

enum AlertLevel {
  ALERT_NORMAL    = 0,
  ALERT_WARNING   = 1,
  ALERT_DANGER    = 2,
  ALERT_EMERGENCY = 3
};

enum VibeMode {
  VIBE_OFF = 0, VIBE_BREATH_INHALE, VIBE_BREATH_PAUSE,
  VIBE_BREATH_EXHALE, VIBE_PULSE, VIBE_STRONG, VIBE_CONTINUOUS
};

enum BreathPhase { BP_IN, BP_HOLD, BP_OUT };

enum TTSState {
  TTS_IDLE,
  TTS_ANNOUNCE,
  TTS_BREATHING,
  TTS_DANGER_MSG,
  TTS_EMERGENCY
};

enum FallState { FALL_IDLE, FALL_FREEFALL, FALL_IMPACT, FALL_POSTURE };
FallState fallState = FALL_IDLE;
// ── Enum clip audio ───────────────────────────────────────────────────
enum AudioClip {
  CLIP_NONE = 0,
  CLIP_WARN1,         // Cảnh báo cấp một...
  CLIP_DANGER1,       // Nguy hiểm cấp hai!...
  CLIP_EMER1,         // Khẩn cấp! Gọi 115...
  CLIP_BREATH_IN,     // Hít vào, bốn giây
  CLIP_BREATH_HOLD,   // Giữ lại, bảy giây
  CLIP_BREATH_OUT,    // Thở ra, tám giây
  CLIP_BREATH_DONE,   // Bạn đã thở xong ba vòng...
  CLIP_DANGER_REST,   // Hãy ngồi nghỉ ngay...
  CLIP_EMER_CALL,     // Khẩn cấp! Gọi 115 ngay!
  CLIP_FALL,          // Phát hiện té ngã!...
  CLIP_SOS_SENT,      // Đã gửi tin nhắn SOS.
  CLIP_SOS_FAIL,      // Gửi SOS thất bại...
  CLIP_CONFIRMED,     // Đã xác nhận. Tiếp tục...
  CLIP_NORMAL,        // Các chỉ số đã trở về bình thường...
  CLIP_SIM_ON,        // Chuyển sang chế độ mô phỏng.
  CLIP_REAL_ON,       // Chuyển sang chế độ đo thực.
  CLIP_READY,         // Mầm nhỏ đã sẵn sàng...
  CLIP_SPO2_LOW,      // Cảnh báo! SpO2 thấp!
  CLIP_BPM_BAD,       // Cảnh báo! Nhịp tim bất thường!
  CLIP_SOS_MANUAL,    // Đang gửi SOS khẩn cấp!
  CLIP_CONFIRM_WARN,  // Đã xác nhận cảnh báo. Cảm ơn bạn.
  CLIP_CONFIRM_FALL,  // Đã xác nhận bình thường sau té ngã.
  CLIP_COUNT
};

// =====================================================================
// FORWARD DECLARATIONS
// =====================================================================
void resetHeart();
bool sendTelegramSOS(String reason);
void motorOff();
void updateHeartBeatTiming();
void updateAlertSystem(float bpm, float spo2, float temp, bool fall);
void activateAlert(AlertLevel newLevel, String reason, float bpm, float spo2, float temp);
float getBodyTempDisplay();
void triggerFallAlert();
void startBreathingAssist();
void checkAlertRecovery(float bpm, float spo2, float temp);
String buildAlertReason(float bpm, float spo2, float temp, bool fall, AlertLevel lv);
void playClip(AudioClip clip);
void playClipQueued(AudioClip clip);
void updateTTSAudio();
void ttsStop();
void fetchFirebaseData();
bool firebaseSignIn();
void showDueDateScreen();
void calcPregnancyWeek();
// =====================================================================
// PIN CONFIG
// =====================================================================
#define SDA_PIN         8
#define SCL_PIN         9
#define BTN1_PIN        2
#define BTN2_PIN        3
#define BTN3_PIN        21
#define MPU_INT_PIN     7
#define MOTOR_PIN       10

#define I2S_BCLK_PIN    4
#define I2S_LRC_PIN     5
#define I2S_DIN_PIN     6

#define SLIDE_MAX_SAMPLES  60
#define SLIDE_SAMPLE_HZ     1
#define SLIDE_MIN_VALID    15
#define SLIDE_UPDATE_MS  60000UL

struct SlidingWindow {
  float bpmBuf[SLIDE_MAX_SAMPLES];
  float spo2Buf[SLIDE_MAX_SAMPLES];
  bool  validBpm[SLIDE_MAX_SAMPLES];
  bool  validSpo2[SLIDE_MAX_SAMPLES];
  int   head, count;
  float avgBpm, avgSpo2;
  int   validBpmCount, validSpo2Count;
  bool  hasResult;
  unsigned long lastSampleMs, lastUpdateMs;
};
SlidingWindow sw;
// =====================================================================
// GLOBAL SENSOR VALUES
// =====================================================================
float bpmDisplay  = 0;
float spo2Display = 0;
float bodySmooth  = 36.5f;
float roomSmooth  = 28.0f;
unsigned long lastBeatTime = 0;

AlertLevel alertLevel     = ALERT_NORMAL;
AlertLevel prevAlertLevel = ALERT_NORMAL;

// =====================================================================
// WIFI / NTP / TELEGRAM
// =====================================================================
const char* WIFI_SSID = "YOUR_WIFI_SSID_HERE";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD_HERE";

const char* TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE";
const char* TELEGRAM_CHAT_ID   = "YOUR_CHAT_ID_HERE";
const char* TELEGRAM_API_HOST  = "api.telegram.org";
#define TELEGRAM_SOS_COOLDOWN  60000UL

bool   telegramEnabled    = true;
bool   telegramConfigured = false;
unsigned long lastTelegramSOS = 0;

const long  GMT_OFFSET_SEC      = 7 * 3600;
const int   DAYLIGHT_OFFSET_SEC = 0;
const char* NTP_SERVER_1 = "pool.ntp.org";
const char* NTP_SERVER_2 = "time.google.com";
const char* NTP_SERVER_3 = "time.cloudflare.com";

bool   wifiOK         = false;
bool   timeOK         = false;
unsigned long lastWiFiTry   = 0;
unsigned long lastTimeCheck = 0;
int    wifiStatusCode = WL_IDLE_STATUS;
String wifiStatusText = "IDLE";
int    wifiRSSI       = 0;
bool   ntpStarted     = false;

// =====================================================================
// FIREBASE FIRESTORE — CẤU HÌNH
// =====================================================================
#define FB_PROJECT_ID    "YOUR_FIREBASE_PROJECT_ID"       // VD: "pregcare-abc12"
#define FB_API_KEY       "YOUR_FIREBASE_API_KEY"           // Lấy từ Project Settings → Web API Key
#define FB_USER_EMAIL    "YOUR_FIREBASE_AUTH_EMAIL"        // Email tài khoản Firebase Auth
#define FB_USER_PASS     "YOUR_FIREBASE_AUTH_PASSWORD"     // Mật khẩu tài khoản Firebase Auth

// UID của document cần đọc — lấy từ Firestore console
// Ví dụ từ hình: "gN2Vb8obIIRU8h37xXiZ5zzUTbk2"
#define FB_DOC_UID       "YOUR_FIRESTORE_DOC_UID"

// Collection name
#define FB_COLLECTION    "users"

// Dữ liệu lấy từ Firebase
struct PregnancyInfo {
  bool  valid;           // đã fetch thành công chưa
  long  daysLeft;        // số ngày còn lại đến EDD
  int   pregnancyWeek;   // tuần thai (tính từ ngày hiện tại & EDD)
  float weightKg;        // cân nặng (trường weight trong Firestore)
  int   heightCm;        // chiều cao
  char  eddStr[12];      // chuỗi ngày dự sinh "DD/MM/YYYY"
  time_t eddEpoch;       // EDD dưới dạng Unix timestamp
};
PregnancyInfo pregInfo = {false, 0, 0, 0.0f, 0, "--/--/----", 0};

unsigned long lastFirebaseFetch = 0xFFFFFFFF - 10000UL; // không fetch ngay khi boot
#define FIREBASE_FETCH_INTERVAL  300000UL  // fetch mỗi 5 phút
bool firebaseFetchPending = false;

// Token xác thực Firebase
char fbIdToken[1200] = "";
unsigned long fbTokenExpiry = 0;
// =====================================================================
// FIREBASE REALTIME HEALTH UPLOAD
// =====================================================================
unsigned long lastHealthUpload = 0;
#define HEALTH_UPLOAD_INTERVAL 60000UL   // 1 phút
#undef RTDB_URL
#define RTDB_URL "https://YOUR_PROJECT_ID-default-rtdb.asia-southeast1.firebaseio.com"
#define DEVICE_ID "demo_device_001"

unsigned long highBpmStart = 0;

#define DEMO_FALL_MODE   true   // true = ngưỡng thấp để demo; false = thực tế

#if DEMO_FALL_MODE
  // Demo: lắc nhẹ là trigger
  #define FALL_IMPACT_G        1.4f   // thực tế: 2.5f
  #define FALL_IMPACT_WINDOW   500UL
  #define FALL_TILT_DEG        30.0f  // thực tế: 55.0f
  #define FALL_TILT_WINDOW     800UL
  #define FALL_STILL_SEC      1500UL  // thực tế: 3000UL
  #define FALL_STILL_GYRO      0.8f   // thực tế: 0.3f
  #define FALL_STILL_ACC_VAR   0.4f   // thực tế: 0.15f
  #define FALL_COOLDOWN       4000UL  // thực tế: 8000UL
#else
  #define FALL_IMPACT_G        2.5f
  #define FALL_IMPACT_WINDOW   300UL
  #define FALL_TILT_DEG        55.0f
  #define FALL_TILT_WINDOW     500UL
  #define FALL_STILL_SEC      3000UL
  #define FALL_STILL_GYRO      1.5f
  #define FALL_STILL_ACC_VAR   0.6f
  #define FALL_COOLDOWN       8000UL
#endif

bool demoFallMode = DEMO_FALL_MODE;
float fallImpactG       = FALL_IMPACT_G;
float fallTiltDeg       = FALL_TILT_DEG;
unsigned long fallStillMs = FALL_STILL_SEC;
// =====================================================================
// AUDIO ENGINE — LittleFS WAV
// =====================================================================
AudioGeneratorWAV      *wavGen  = nullptr;
AudioFileSourceLittleFS *fsSrc  = nullptr;
AudioOutputI2S         *i2sOut  = nullptr;

bool      ttsPlaying  = false;
bool      ttsEnabled  = true;
float     ttsVolume   = 1.0f;
bool      littleFsOK  = false;

// Queue đơn: lưu 1 clip chờ phát sau clip hiện tại
AudioClip ttsQueuedClip = CLIP_NONE;
bool      ttsQueued     = false;

// Map enum → tên file trong LittleFS
const char* clipFilename(AudioClip clip) {
  switch (clip) {
    case CLIP_WARN1:        return "/warn1.wav";
    case CLIP_DANGER1:      return "/danger1.wav";
    case CLIP_EMER1:        return "/emer1.wav";
    case CLIP_BREATH_IN:    return "/breath_in.wav";
    case CLIP_BREATH_HOLD:  return "/breath_hold.wav";
    case CLIP_BREATH_OUT:   return "/breath_out.wav";
    case CLIP_BREATH_DONE:  return "/breath_done.wav";
    case CLIP_DANGER_REST:  return "/danger_rest.wav";
    case CLIP_EMER_CALL:    return "/emer_call.wav";
    case CLIP_FALL:         return "/fall.wav";
    case CLIP_SOS_SENT:     return "/sos_sent.wav";
    case CLIP_SOS_FAIL:     return "/sos_fail.wav";
    case CLIP_CONFIRMED:    return "/confirmed.wav";
    case CLIP_NORMAL:       return "/normal.wav";
    case CLIP_SIM_ON:       return "/sim_on.wav";
    case CLIP_REAL_ON:      return "/real_on.wav";
    case CLIP_READY:        return "/ready.wav";
    case CLIP_SPO2_LOW:     return "/spo2_low.wav";
    case CLIP_BPM_BAD:      return "/bpm_bad.wav";
    case CLIP_SOS_MANUAL:   return "/sos_manual.wav";
    case CLIP_CONFIRM_WARN: return "/confirm_warn.wav";
    case CLIP_CONFIRM_FALL: return "/confirm_fall.wav";
    default:                return nullptr;
  }
}

void initAudioOutput() {

  i2sOut = new AudioOutputI2S();

  i2sOut->SetPinout(
    I2S_BCLK_PIN,
    I2S_LRC_PIN,
    I2S_DIN_PIN
  );

  i2sOut->SetGain(ttsVolume);

  i2sOut->SetRate(8000);
}

// Phát ngay (ngắt clip hiện tại nếu có)
void playClip(AudioClip clip) {
  if (!ttsEnabled || !littleFsOK || clip == CLIP_NONE) return;
  const char* fname = clipFilename(clip);
  if (!fname) return;

  // Dừng clip đang chạy
  if (wavGen)  { wavGen->stop();  delete wavGen;  wavGen  = nullptr; }
  if (fsSrc)   { delete fsSrc;    fsSrc   = nullptr; }

  if (!LittleFS.exists(fname)) {
    Serial.printf("[AUDIO] File not found: %s\n", fname);
    ttsPlaying = false;
    return;
  }

  fsSrc  = new AudioFileSourceLittleFS(fname);
  wavGen = new AudioGeneratorWAV();
  if (!wavGen->begin(fsSrc, i2sOut)) {
    Serial.printf("[AUDIO] WAV begin FAIL: %s\n", fname);
    delete wavGen; wavGen = nullptr;
    delete fsSrc;  fsSrc  = nullptr;
    ttsPlaying = false;
    return;
  }
  ttsPlaying = true;
  ttsQueued  = false;  // clip mới phát → xóa queue
  Serial.printf("[AUDIO] Playing: %s\n", fname);
}

// Phát sau clip hiện tại (nếu đang bận thì queue)
void playClipQueued(AudioClip clip) {
  if (!ttsEnabled || !littleFsOK || clip == CLIP_NONE) return;
  if (ttsPlaying) {
    ttsQueuedClip = clip;
    ttsQueued     = true;
    Serial.printf("[AUDIO] Queued: %s\n", clipFilename(clip));
  } else {
    playClip(clip);
  }
}

void updateTTSAudio() {
  if (!ttsPlaying) {
    if (ttsQueued) {
      ttsQueued = false;
      AudioClip next = ttsQueuedClip;
      ttsQueuedClip = CLIP_NONE;
      playClip(next);
    }
    return;
  }
  if (wavGen && wavGen->isRunning()) {
    if (!wavGen->loop()) {
      wavGen->stop();
      ttsPlaying = false;
      Serial.println("[AUDIO] Done");
    }
  } else {
    ttsPlaying = false;
  }
}

void ttsStop() {
  if (wavGen) { wavGen->stop(); delete wavGen; wavGen = nullptr; }
  if (fsSrc)  { delete fsSrc;  fsSrc = nullptr; }
  ttsPlaying    = false;
  ttsQueued     = false;
  ttsQueuedClip = CLIP_NONE;
}

// =====================================================================
// ALERT ANNOUNCE SCREEN
// =====================================================================
bool          alertAnnounceActive = false;
unsigned long alertAnnounceStart  = 0;
#define ALERT_ANNOUNCE_MS  3000UL
AlertLevel    announceLevel  = ALERT_NORMAL;
String        announceReason = "";

// =====================================================================
// TTS STATE MACHINE
// =====================================================================
TTSState ttsState   = TTS_IDLE;
int      ttsStep    = 0;
unsigned long ttsStepMs = 0;

BreathPhase breathPhase    = BP_IN;
unsigned long breathPhaseEnd = 0;
bool breathGuideActive    = false;
bool waitingBreathDoneRecovery = false;
int  breathCycleCount     = 0;
#define BREATH_CYCLES_MAX  3
#define BREATH_IN_MS    4000UL
#define BREATH_HOLD_MS  7000UL
#define BREATH_OUT_MS   8000UL

// =====================================================================
// CHẾ ĐỘ MÔ PHỎNG
// =====================================================================
bool simulationMode = false;
unsigned long simLastUpdate   = 0;
float simBPM   = 75.0f;
float simSpO2  = 98.0f;
float simTemp  = 36.8f;
bool  simFall  = false;
unsigned long simModeToggleMs = 0;
bool simModeJustChanged = false;

float simBPMDir  =  1.0f;
float simSpO2Dir = -0.1f;
float simTempDir =  0.05f;
int   simScenario = 0;

String wifiStatusToText(int s) {
  switch (s) {
    case WL_CONNECTED:       return "CONNECTED";
    case WL_NO_SSID_AVAIL:   return "NO SSID";
    case WL_CONNECT_FAILED:  return "BAD PASS";
    case WL_CONNECTION_LOST: return "LOST";
    case WL_DISCONNECTED:    return "DISCONNECTED";
    default:                 return "IDLE";
  }
}

void toggleSimulationMode() {
  simulationMode = !simulationMode;
  simModeJustChanged = true;
  simModeToggleMs = millis();
  if (simulationMode) {
    simBPM = 75.0f; simSpO2 = 98.0f; simTemp = 36.5f;
    simFall = false; simScenario = 0;
    playClip(CLIP_SIM_ON);
    Serial.println("[SIM] ON");
  } else {
    resetHeart(); alertLevel = ALERT_NORMAL; motorOff();
    ttsStop();
    playClip(CLIP_REAL_ON);
    Serial.println("[REAL] ON");
  }
}

void updateSimulation() {
  if (!simulationMode) return;
  unsigned long now = millis();
  if (now - simLastUpdate < 500UL) return;
  simLastUpdate = now;

  switch (simScenario) {
    case 0:
      simBPM  += simBPMDir  * 0.5f;
      simSpO2 += simSpO2Dir * 0.05f;
      simTemp += simTempDir * 0.02f;
      if (simBPM  > 85 || simBPM  < 65) simBPMDir  *= -1;
      if (simSpO2 > 99 || simSpO2 < 96) simSpO2Dir *= -1;
      if (simTemp > 37.0f || simTemp < 36.4f) simTempDir *= -1;
      break;
    case 1:
      simBPM  = 108.0f + sinf(now / 3000.0f) * 3.0f;
      simSpO2 = 94.5f  + sinf(now / 4000.0f) * 0.5f;
      simTemp = 37.6f;
      break;
    case 2:
      simBPM  = 125.0f + sinf(now / 2000.0f) * 5.0f;
      simSpO2 = 91.5f  + sinf(now / 3000.0f) * 1.0f;
      simTemp = 38.3f;
      break;
    case 3:
      simBPM  = 148.0f + sinf(now / 1500.0f) * 8.0f;
      simSpO2 = 88.0f  + sinf(now / 2500.0f) * 2.0f;
      simTemp = 39.5f;
      break;
  }

  bpmDisplay  = simBPM;
  spo2Display = simSpO2;
  bodySmooth  = simTemp - BODY_TEMP_OFFSET;
  updateHeartBeatTiming();
  lastBeatTime = now;
  updateAlertSystem(bpmDisplay, spo2Display, simTemp, simFall);
  simFall = false;
}

// =====================================================================
// NGƯỠNG CẢM BIẾN
// =====================================================================
#define SPO2_LOW_THRESHOLD   94.0f
#define BPM_LOW_THRESHOLD    50.0f
#define BPM_HIGH_THRESHOLD  160.0f
#define IR_CONTACT_THRESH  50000L
#define RED_CONTACT_THRESH  5000L
#define CONTACT_SCORE_LOCK     5
#define CONTACT_RESET_MS    3000UL
#define AGC_TARGET_LO    50000L
#define AGC_TARGET_HI   120000L
#define AGC_INTERVAL      400UL
#define MOTION_THRESH_HR    0.30f
#define MOTION_THRESH_SPO2  0.12f
#define SPO2_FINGER_OFFSET   0.0f

// =====================================================================
// NGƯỠNG CẢNH BÁO 3 TẦNG
// =====================================================================
#define ALERT1_BPM_HIGH   120.0f
#define ALERT1_SPO2_HIGH   90.0f
#define ALERT1_TEMP        37.5f
#define ALERT2_BPM_HIGH   135.0f
#define ALERT2_SPO2_LOW    88.0f
#define ALERT2_TEMP        38.0f
#define ALERT3_BPM_HIGH   155.0f
#define ALERT3_BPM_LOW     45.0f
#define ALERT3_SPO2_LOW    85.0f
#define ALERT3_TEMP        39.0f
#define ALERT1_RECHECK_MS   30000UL
#define ALERT2_RECHECK_MS   60000UL
#define ALERT_RECOVERY_MS   20000UL
#define HIGH_BPM_CONFIRM_MS 300000UL

// =====================================================================
// AGC
// =====================================================================
uint8_t       ledPower = 0x5F;
unsigned long lastAGC  = 0;
bool          agcLocked = false;

// =====================================================================
// MOTOR RUNG (GPIO10)
// =====================================================================
unsigned long breathWaitUntil = 0;
VibeMode  vibeMode = VIBE_OFF;
VibeMode lastBreathVibe = VIBE_OFF;
bool      motorOn  = false;
unsigned long vibePhaseEnd = 0;

#define BREATH_INHALE_MS  4000UL
#define BREATH_PAUSE_MS   7000UL
#define BREATH_EXHALE_MS  8000UL
#define MOTOR_LEVEL_LIGHT    80
#define MOTOR_LEVEL_MEDIUM  160
#define MOTOR_LEVEL_STRONG  255

void motorSet(bool on, int level = 255) {
  if (on) { analogWrite(MOTOR_PIN, level); motorOn = true;  }
  else    { analogWrite(MOTOR_PIN, 0);     motorOn = false; }
}
void motorOff() { motorSet(false); vibeMode = VIBE_OFF; }

void updateMotor() {
  unsigned long now = millis();
  switch (vibeMode) {
    case VIBE_OFF:
      motorSet(false); break;
    case VIBE_BREATH_INHALE: {

    unsigned long elapsed =
      BREATH_INHALE_MS - (vibePhaseEnd - now);

    // tăng dần
    int level = map(
      elapsed,
      0,
      BREATH_INHALE_MS,
      40,
      180
    );

    motorSet(true, level);

    if (now >= vibePhaseEnd) {

      vibeMode = VIBE_BREATH_PAUSE;

      vibePhaseEnd = now + BREATH_PAUSE_MS;
    }

    break;
    }

    case VIBE_BREATH_PAUSE:

        // rung nhẹ đều
        motorSet(true, 55);

        if (now >= vibePhaseEnd) {

          vibeMode = VIBE_BREATH_EXHALE;

          vibePhaseEnd = now + BREATH_EXHALE_MS;
        }

        break;

    case VIBE_BREATH_EXHALE: {

        unsigned long elapsed =
          BREATH_EXHALE_MS - (vibePhaseEnd - now);

        // giảm dần
        int level = map(
          elapsed,
          0,
          BREATH_EXHALE_MS,
          180,
          40
        );

        motorSet(true, level);

        if (now >= vibePhaseEnd) {

          vibeMode = VIBE_BREATH_INHALE;

          vibePhaseEnd = now + BREATH_INHALE_MS;
        }

        break;
    }
    case VIBE_PULSE:
      if (now % 1000 < 200) motorSet(true, MOTOR_LEVEL_MEDIUM);
      else motorSet(false);
      break;
    case VIBE_STRONG:
      if (now % 600 < 400) motorSet(true, MOTOR_LEVEL_MEDIUM);
      else motorSet(false);
      break;
    case VIBE_CONTINUOUS:
      motorSet(true, MOTOR_LEVEL_STRONG); break;
  }
}
bool  fallConfirmed = false;
unsigned long fallAlertEnd = 0, fallCooldownEnd = 0;
void updateFallSOSMotor() {
  if (!fallConfirmed || vibeMode != VIBE_CONTINUOUS) return;
  static int    sosStep    = 0;
  static unsigned long sosTimer = 0;
  unsigned long now = millis();
  // Pattern: [ON 200ms, OFF 200ms] x3, [ON 600ms, OFF 200ms] x3, [ON 200ms, OFF 200ms] x3, OFF 1500ms
  static const unsigned long pattern[] = {
    200, 200, 200, 200, 200, 200,   // 3 ngắn
    600, 200, 600, 200, 600, 200,   // 3 dài
    200, 200, 200, 200, 200, 200,   // 3 ngắn
    1500                             // nghỉ
  };
  static const int patternLen = 19;
  if (now - sosTimer >= pattern[sosStep]) {
    sosTimer = now;
    sosStep  = (sosStep + 1) % patternLen;
    // chẵn = ON, lẻ = OFF (trừ bước nghỉ cuối)
    if (sosStep < patternLen - 1) {
      if (sosStep % 2 == 0) motorSet(true, MOTOR_LEVEL_STRONG);
      else                  motorSet(false);
    } else {
      motorSet(false);
    }
  }
}

void startBreathingAssist() {

  breathCycleCount = 0;

  breathPhase = BP_OUT;

  breathWaitUntil = 0;

  lastBreathVibe = VIBE_OFF;

  vibeMode = VIBE_BREATH_INHALE;

  vibePhaseEnd = millis() + BREATH_INHALE_MS;
}

// =====================================================================
// HỆ THỐNG CẢNH BÁO 3 TẦNG
// =====================================================================
unsigned long alertStartMs     = 0;
unsigned long lastAlertCheckMs = 0;
unsigned long highBpmStartMs   = 0;
bool          highBpmTracking  = false;
unsigned long alertRecheckMs   = 0;
bool          alertConfirmed   = false;
String        alertReason      = "";
unsigned long recoveryStartMs  = 0;
bool          inRecovery       = false;
unsigned long danger_restStart = 0;
#define DANGER_REST_MS  300000UL
unsigned long sos_lastRetry = 0;
bool          sos_sent      = false;

float getBodyTempDisplay() { return bodySmooth + BODY_TEMP_OFFSET; }

AlertLevel evaluateAlertLevel(float bpm, float spo2, float temp, bool fall) {
  if (fall) return ALERT_EMERGENCY;
  if (bpm > 0 && (bpm > ALERT3_BPM_HIGH || bpm < ALERT3_BPM_LOW)) return ALERT_EMERGENCY;
  if (spo2 > 0 && spo2 < ALERT3_SPO2_LOW) return ALERT_EMERGENCY;
  if (temp > 0 && temp > ALERT3_TEMP)      return ALERT_EMERGENCY;
  if (bpm > 0 && bpm > ALERT2_BPM_HIGH)   return ALERT_DANGER;
  if (spo2 > 0 && spo2 < ALERT2_SPO2_LOW) return ALERT_DANGER;
  if (temp > 0 && temp > ALERT2_TEMP)      return ALERT_DANGER;
  if (bpm > 0 && bpm > ALERT1_BPM_HIGH)   return ALERT_WARNING;
  if (spo2 > 0 && spo2 >= 94.0f && spo2 < ALERT1_SPO2_HIGH) return ALERT_WARNING;
  if (temp > 0 && temp > ALERT1_TEMP)      return ALERT_WARNING;
  return ALERT_NORMAL;
}

String buildAlertReason(float bpm, float spo2, float temp, bool fall, AlertLevel lv) {
  String r = "";
  if (fall) r += "Te nga! ";
  if (bpm > 0) {
    if      (bpm > ALERT3_BPM_HIGH) r += "Nhip:" + String((int)bpm) + "! ";
    else if (bpm < ALERT3_BPM_LOW)  r += "Nhip:" + String((int)bpm) + " thap! ";
    else if (bpm > ALERT2_BPM_HIGH) r += "Nhip:" + String((int)bpm) + " cao. ";
    else if (bpm > ALERT1_BPM_HIGH) r += "Nhip:" + String((int)bpm) + " hoi cao. ";
  }
  if (spo2 > 0) {
    if      (spo2 < ALERT3_SPO2_LOW) r += "O2:" + String((int)spo2) + "% nguy! ";
    else if (spo2 < ALERT2_SPO2_LOW) r += "O2:" + String((int)spo2) + "% thap. ";
    else if (spo2 < ALERT1_SPO2_HIGH) r += "O2:" + String((int)spo2) + "% hoi thap. ";
  }
  if (temp > 0) {
    if      (temp > ALERT3_TEMP) r += "Sot:" + String(temp, 1) + "C! ";
    else if (temp > ALERT2_TEMP) r += "Sot:" + String(temp, 1) + "C. ";
    else if (temp > ALERT1_TEMP) r += "Nhiet:" + String(temp, 1) + "C. ";
  }
  return r;
}

// Map alert level → clip phát khi announce
AudioClip alertToClip(AlertLevel lv) {
  switch (lv) {
    case ALERT_WARNING:   return CLIP_WARN1;
    case ALERT_DANGER:    return CLIP_DANGER1;
    case ALERT_EMERGENCY: return CLIP_EMER1;
    default:              return CLIP_NONE;
  }
}

void triggerAnnounce(AlertLevel lv, String reason) {
  alertAnnounceActive = true;
  alertAnnounceStart  = millis();
  announceLevel  = lv;
  announceReason = reason;
  ttsStop();
  AudioClip clip = alertToClip(lv);
  if (clip != CLIP_NONE) playClip(clip);
  ttsStep   = 0;
  ttsStepMs = millis();
  switch (lv) {
    case ALERT_WARNING:
    case ALERT_DANGER:
    case ALERT_EMERGENCY: ttsState = TTS_ANNOUNCE; break;
    default: ttsState = TTS_IDLE; break;
  }
}
void updateTTSStateMachine() {
  unsigned long now = millis();
  switch (ttsState) {
    case TTS_IDLE:
      break;

    case TTS_ANNOUNCE:
      // Chờ clip announce xong rồi chuyển sang bước tiếp
      if (!alertAnnounceActive && !ttsPlaying) {
        switch (announceLevel) {
      case ALERT_WARNING:

          ttsState  = TTS_BREATHING;

          ttsStepMs = now;

          // reset phase để bắt đầu từ inhale
          breathPhase = BP_OUT;

          lastBreathVibe = VIBE_OFF;

          vibeMode = VIBE_BREATH_INHALE;

          breathWaitUntil = 0;

          // KHÔNG play ở đây nữa

          break;
          case ALERT_DANGER:
            ttsState  = TTS_DANGER_MSG;
            ttsStepMs = now;
            playClip(CLIP_DANGER_REST);
            break;
          case ALERT_EMERGENCY:
            ttsState  = TTS_EMERGENCY;
            ttsStepMs = now;
            playClip(CLIP_EMER_CALL);
            break;
          default:
            ttsState = TTS_IDLE; break;
        }
      }
      break;

  //   case TTS_BREATHING:
  // if (alertLevel != ALERT_WARNING) {
  //   ttsState = TTS_IDLE;
  //   break;
  // }

  // {
  //   static VibeMode lastVibe = VIBE_OFF;

  //   if (vibeMode != lastVibe) {

  //     lastVibe = vibeMode;

  //     switch (vibeMode) {

  //       case VIBE_BREATH_INHALE:
  //         if (breathPhase != BP_IN) {
  //           breathPhase = BP_IN;
  //           playClip(CLIP_BREATH_IN);
  //         }
  //         break;

  //       case VIBE_BREATH_PAUSE:
  //         if (breathPhase != BP_HOLD) {
  //           breathPhase = BP_HOLD;
  //           playClip(CLIP_BREATH_HOLD);
  //         }
  //         break;

  //       case VIBE_BREATH_EXHALE:
  //         if (breathPhase != BP_OUT) {

  //           breathPhase = BP_OUT;

  //           playClip(CLIP_BREATH_OUT);

  //           breathCycleCount++;

  //           Serial.printf("[BREATH] cycle = %d\n", breathCycleCount);

  //           if (breathCycleCount >= BREATH_CYCLES_MAX) {

  //             ttsQueuedClip = CLIP_BREATH_DONE;
  //             ttsQueued     = true;

  //             breathGuideActive = false;

  //             ttsState = TTS_IDLE;
  //           }
  //         }
  //         break;

  //       default:
  //         break;
  //     }
  //   }
  // }
  // break;

  case TTS_BREATHING:

  if (alertLevel != ALERT_WARNING) {
    ttsState = TTS_IDLE;
    break;
  }

  // Đang chờ hết thời gian phase
  if (millis() < breathWaitUntil) {
    break;
  }

  {

    if (vibeMode != lastBreathVibe) {

      lastBreathVibe = vibeMode;

      switch (vibeMode) {

        // ===== HÍT VÀO =====
        case VIBE_BREATH_INHALE:

          if (breathPhase != BP_IN) {

            breathPhase = BP_IN;

            Serial.println("[BREATH] INHALE");

            playClip(CLIP_BREATH_IN);

            // Audio 2s + chờ thêm 2s = 4s
            breathWaitUntil = millis() + 4000;
          }

          break;

        // ===== GIỮ =====
        case VIBE_BREATH_PAUSE:

          if (breathPhase != BP_HOLD) {

            breathPhase = BP_HOLD;

            Serial.println("[BREATH] HOLD");

            playClip(CLIP_BREATH_HOLD);

            // Audio 2s + chờ thêm 5s = 7s
            breathWaitUntil = millis() + 7000;
          }

          break;

        // ===== THỞ RA =====
        case VIBE_BREATH_EXHALE:

          if (breathPhase != BP_OUT) {

            breathPhase = BP_OUT;

            Serial.println("[BREATH] EXHALE");

            playClip(CLIP_BREATH_OUT);

            breathCycleCount++;

            Serial.printf("[BREATH] cycle = %d\n", breathCycleCount);

            // Audio 2s + chờ thêm 6s = 8s
            breathWaitUntil = millis() + 8000;

            if (breathCycleCount >= BREATH_CYCLES_MAX) {

              ttsQueuedClip = CLIP_BREATH_DONE;
              ttsQueued     = true;

              breathGuideActive = false;

              waitingBreathDoneRecovery = true;

              ttsState = TTS_IDLE;
            }
          }

          break;

        default:
          break;
      }
    }
  }

  break;

  case TTS_DANGER_MSG:
      if (alertLevel != ALERT_DANGER) { ttsState = TTS_IDLE; break; }
      // Nhắc lại mỗi 30 giây
      if (now - ttsStepMs > 30000UL && !ttsPlaying) {
        ttsStepMs = now;
        playClip(CLIP_DANGER_REST);
      }
      break;

    case TTS_EMERGENCY:
      if (alertLevel != ALERT_EMERGENCY) { ttsState = TTS_IDLE; break; }
      // Nhắc lại mỗi 15 giây
      if (now - ttsStepMs > 15000UL && !ttsPlaying) {
        ttsStepMs = now;
        playClip(CLIP_EMER_CALL);
      }
      break;
  }
}

void checkAlertRecovery(float bpm, float spo2, float temp) {
  AlertLevel needed = evaluateAlertLevel(bpm, spo2, temp, false);
  if (needed < alertLevel) {
    if (!inRecovery) { inRecovery = true; recoveryStartMs = millis(); }
    else if (millis() - recoveryStartMs >= ALERT_RECOVERY_MS) {
      String r = buildAlertReason(bpm, spo2, temp, false, needed);
      activateAlert(needed, r, bpm, spo2, temp);
      inRecovery = false;
    }
  } else inRecovery = false;
}

void activateAlert(AlertLevel newLevel, String reason, float bpm, float spo2, float temp) {
  bool isNew = (newLevel != alertLevel);
  prevAlertLevel = alertLevel;
  alertLevel     = newLevel;
  alertReason    = reason;
  alertConfirmed = false;
  inRecovery     = false;
  if (!isNew && newLevel == prevAlertLevel) return;
  alertStartMs = millis();

  if (isNew && newLevel > ALERT_NORMAL) {
    triggerAnnounce(newLevel, reason);
  }
  if (isNew && newLevel == ALERT_NORMAL) {
    ttsStop();
    playClip(CLIP_NORMAL);
  }

  switch (newLevel) {
    case ALERT_NORMAL:
      motorOff();
      breathGuideActive = false;
      ttsState = TTS_IDLE;
      break;
    case ALERT_WARNING:

      startBreathingAssist();

      alertRecheckMs = millis() + ALERT1_RECHECK_MS;

      breathGuideActive = true;

      // ÉP khác BP_IN để vòng đầu phát inhale
      breathPhase = BP_OUT;

      breathPhaseEnd = millis() + BREATH_IN_MS;

      breathCycleCount = 0;

      break;
    case ALERT_DANGER:
      vibeMode = VIBE_STRONG;
      alertRecheckMs = millis() + ALERT2_RECHECK_MS;
      if (isNew) danger_restStart = millis();
      breathGuideActive = false;
      break;
    case ALERT_EMERGENCY:
      vibeMode = VIBE_CONTINUOUS;
      motorSet(true, MOTOR_LEVEL_STRONG);
      if (isNew) {
        sendTelegramSOS(reason);
        sos_sent = true;
        sos_lastRetry = millis();
      }
      breathGuideActive = false;
      break;
  }
  if (isNew)
    Serial.printf("[ALERT] %d->%d: %s\n", (int)prevAlertLevel, (int)newLevel, reason.c_str());
}
static unsigned long lowSpo2Start = 0;
void updateAlertSystem(float bpm, float spo2, float temp, bool fall) {
  if (millis() - lastAlertCheckMs < 2000UL) return;
  lastAlertCheckMs = millis();

  // ── Dùng trung bình 1 phút từ sliding window ──────────────────────
  // Chỉ dùng giá trị trung bình khi đã có đủ mẫu hợp lệ.
  // Nếu chưa đủ mẫu, không cảnh báo BPM/SpO2 (tránh báo sai khi mới đeo)
  float avgBpm  = 0;
  float avgSpo2 = 0;

  if (sw.validBpmCount >= SLIDE_MIN_VALID) {
    avgBpm = sw.avgBpm;
  }
  if (sw.validSpo2Count >= SLIDE_MIN_VALID) {
    avgSpo2 = sw.avgSpo2;
  }

  // ── Emergency: không cần đợi trung bình, phản ứng ngay ───────────
  // Fall và SpO2 cực thấp là tình huống khẩn cấp tức thì
  if (fall) {
    AlertLevel lv = ALERT_EMERGENCY;
    String r = buildAlertReason(bpm, spo2, temp, true, lv);
    if (lv > alertLevel) activateAlert(lv, r, bpm, spo2, temp);
    return;
  }

  // SpO2 dưới ngưỡng emergency — dùng giá trị real-time vì nguy hiểm tức thì
  if (spo2 > 0 && spo2 < ALERT3_SPO2_LOW) {
    AlertLevel lv = ALERT_EMERGENCY;
    String r = buildAlertReason(avgBpm, spo2, temp, false, lv);
    if (lv > alertLevel) activateAlert(lv, r, avgBpm, spo2, temp);
    return;
  }

  // ── Đánh giá cảnh báo dựa trên TRUNG BÌNH 1 phút ─────────────────
  AlertLevel needed = ALERT_NORMAL;

  // BPM — chỉ cảnh báo khi có trung bình đủ tin cậy
  if (avgBpm > 0) {
    if      (avgBpm > ALERT3_BPM_HIGH) needed = ALERT_EMERGENCY;
    else if (avgBpm < ALERT3_BPM_LOW)  needed = ALERT_EMERGENCY;
    else if (avgBpm > ALERT2_BPM_HIGH) needed = (AlertLevel)max((int)needed, (int)ALERT_DANGER);
    else if (avgBpm > ALERT1_BPM_HIGH) {

    if (highBpmStart == 0)
        highBpmStart = millis();

    // phải cao liên tục 2 phút
    if (millis() - highBpmStart > 120000UL) {

        needed = ALERT_WARNING;
    }

    } else {

        highBpmStart = 0;
}
  }

  // SpO2 — dùng trung bình
  if (avgSpo2 > 0) {

      // Danger nếu dưới 88
      if (avgSpo2 < ALERT2_SPO2_LOW) {

          needed = (AlertLevel)max(
              (int)needed,
              (int)ALERT_DANGER
          );
      }

      // Warning nếu dưới 90 liên tục 30s
      else if (avgSpo2 < 90.0f) {

          if (lowSpo2Start == 0)
              lowSpo2Start = millis();

          if (millis() - lowSpo2Start > 30000UL) {

              needed = (AlertLevel)max(
                  (int)needed,
                  (int)ALERT_WARNING
              );
          }
      }

      else {

          lowSpo2Start = 0;
      }
  }

  // Nhiệt độ — phản ứng ngay (không cần trung bình, thay đổi chậm)
  if (temp > ALERT3_TEMP)      needed = (AlertLevel)max((int)needed, (int)ALERT_EMERGENCY);
  else if (temp > ALERT2_TEMP) needed = (AlertLevel)max((int)needed, (int)ALERT_DANGER);
  else if (temp > ALERT1_TEMP) needed = (AlertLevel)max((int)needed, (int)ALERT_WARNING);

  String reason = buildAlertReason(avgBpm, avgSpo2, temp, false, needed);

  if (needed > alertLevel) {
    activateAlert(needed, reason, avgBpm, avgSpo2, temp);
  } else if (needed < alertLevel && alertLevel > ALERT_NORMAL) {
    checkAlertRecovery(avgBpm, avgSpo2, temp);
  }
}

// =====================================================================
// TELEGRAM SOS
// =====================================================================
bool sendTelegramSOS(String reason) {
  if (!wifiOK) return false;
  if (millis() - lastTelegramSOS < TELEGRAM_SOS_COOLDOWN) return false;
  lastTelegramSOS = millis();

  struct tm t;
  String timeStr = "--:--";
  if (getLocalTime(&t, 100)) {
    char buf[10];
    sprintf(buf, "%02d:%02d", t.tm_hour, t.tm_min);
    timeStr = String(buf);
  }
  float bd = getBodyTempDisplay();
  String simTag = simulationMode ? " [SIM]" : "";
  String msg = "";
  bool isFall = reason.indexOf("Te nga") >= 0 || reason.indexOf("te nga") >= 0;
  if (isFall) {
    msg  = "CANH BAO TE NGA - PREGCARE" + simTag + "\n\n";
    msg  += "Phat hien nguoi than cua ban te nga vao " + timeStr + "\n";
    msg  += "Hay kiem tra nguoi than ngay!\n\n";
    msg  += "Nhip tim: " + (bpmDisplay > 0 ? String((int)bpmDisplay) + " bpm" : "--") + "\n";
    msg  += "SpO2: "     + (spo2Display > 0 ? String((int)spo2Display) + "%" : "--") + "\n";
    msg  += "Nhiet do: " + String(bd, 1) + "C\n";
    msg  += "Goi 115 neu can thiet!";
  } else {
    msg  = "SOS PREGCARE" + simTag + "\n\n";
    msg  += "Ly do: " + reason + "\n\n";
    msg  += "Nhip tim: " + (bpmDisplay > 0 ? String((int)bpmDisplay) + " bpm" : "--") + "\n";
    msg  += "SpO2: "     + (spo2Display > 0 ? String((int)spo2Display) + "%" : "--") + "\n";
    msg  += "Nhiet do: " + String(bd, 1) + "C\n";
    msg  += "Gio: " + timeStr + "\n";
    msg  += "Kiem tra nguoi than ngay!";
  }

  String enc = "";
  for (int i = 0; i < (int)msg.length(); i++) {
    char c = msg[i];
    if (c == ' ')  enc += '+';
    else if (c == '\n') enc += "%0A";
    else enc += c;
  }
  String url = "https://" + String(TELEGRAM_API_HOST) + "/bot" + TELEGRAM_BOT_TOKEN;
  url += "/sendMessage?chat_id=" + String(TELEGRAM_CHAT_ID) + "&text=" + enc;

  WiFiClientSecure client; client.setInsecure();
  HTTPClient http; http.begin(client, url); http.setTimeout(8000);
  int code = http.GET();
  bool ok = (code == 200);
  Serial.printf("[TELEGRAM] HTTP %d\n", code);
  http.end();
  return ok;
}

// =====================================================================
// SLIDING WINDOW
// =====================================================================
// #define SLIDE_MAX_SAMPLES  60
// #define SLIDE_SAMPLE_HZ     1
// #define SLIDE_MIN_VALID    15
// #define SLIDE_UPDATE_MS  60000UL


void sw_init() { memset(&sw, 0, sizeof(sw)); }

float iqrMean(float *arr, bool *valid, int total, int *outCount) {
  float tmp[SLIDE_MAX_SAMPLES]; int n = 0;
  for (int i = 0; i < total; i++) if (valid[i]) tmp[n++] = arr[i];
  *outCount = n; if (n < 4) return 0;
  for (int i = 0; i < n - 1; i++)
    for (int j = 0; j < n - i - 1; j++)
      if (tmp[j] > tmp[j + 1]) { float t = tmp[j]; tmp[j] = tmp[j + 1]; tmp[j + 1] = t; }
  int lo = n / 4, hi = n - n / 4;
  float sum = 0; int cnt = 0;
  for (int i = lo; i < hi; i++) { sum += tmp[i]; cnt++; }
  return cnt > 0 ? sum / cnt : 0;
}

void sw_addSample(float bpm, float spo2, bool bpmOK, bool spo2OK) {
  int i = sw.head;
  sw.bpmBuf[i]    = bpm;   sw.spo2Buf[i]   = spo2;
  sw.validBpm[i]  = bpmOK && bpm >= 40 && bpm <= 200;
  sw.validSpo2[i] = spo2OK && spo2 >= 85 && spo2 <= 100;
  sw.head = (sw.head + 1) % SLIDE_MAX_SAMPLES;
  if (sw.count < SLIDE_MAX_SAMPLES) sw.count++;
}

void sw_updateAvg() {
  int used = min(sw.count, SLIDE_MAX_SAMPLES), cb = 0, cs = 0;
  float ab  = iqrMean(sw.bpmBuf,  sw.validBpm,  used, &cb);
  float as2 = iqrMean(sw.spo2Buf, sw.validSpo2, used, &cs);
  sw.validBpmCount = cb; sw.validSpo2Count = cs;
  if (cb  >= SLIDE_MIN_VALID) sw.avgBpm  = ab;
  if (cs  >= SLIDE_MIN_VALID) sw.avgSpo2 = as2;
  sw.hasResult = (cb >= SLIDE_MIN_VALID || cs >= SLIDE_MIN_VALID);
}

// =====================================================================
// OBJECTS
// =====================================================================
Adafruit_SH1106G   display(128, 64, &Wire, -1);
Adafruit_MLX90614  mlx;
MAX30105            particleSensor;
Adafruit_MPU6050   mpu;

bool mlxOK = false, maxOK = false, mpuOK = false;
int  screenMode = 0;

// =====================================================================
// WIFI + NTP
// =====================================================================
bool scanSSID() {
  int n = WiFi.scanNetworks(false, true); bool found = false;
  for (int i = 0; i < n; i++) if (WiFi.SSID(i) == String(WIFI_SSID)) found = true;
  WiFi.scanDelete(); return found;
}

bool connectWiFiBlocking(unsigned long tms) {
  WiFi.persistent(false); WiFi.mode(WIFI_STA); WiFi.setSleep(false);
  WiFi.disconnect(true, true); delay(500);
  if (!scanSSID()) { wifiOK = false; wifiStatusText = "NO SSID"; return false; }
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < tms) delay(300);
  wifiStatusCode = WiFi.status();
  wifiStatusText = wifiStatusToText(wifiStatusCode);
  wifiOK = (wifiStatusCode == WL_CONNECTED);
  if (wifiOK) { wifiRSSI = WiFi.RSSI(); Serial.printf("WiFi OK! IP=%s\n", WiFi.localIP().toString().c_str()); }
  return wifiOK;
}

void connectWiFiNonBlocking() {
  if (WiFi.status() == WL_CONNECTED) { wifiOK = true; wifiRSSI = WiFi.RSSI(); wifiStatusText = "CONNECTED"; return; }
  wifiOK = false;
  if (lastWiFiTry != 0 && millis() - lastWiFiTry < 15000UL) return;
  lastWiFiTry = millis();
  connectWiFiBlocking(10000UL);
}

void initNTP() {
  if (!wifiOK) return;
  if (!ntpStarted) {
    configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, NTP_SERVER_1, NTP_SERVER_2, NTP_SERVER_3);
    ntpStarted = true;
  }
  struct tm t; timeOK = getLocalTime(&t, 7000);
}

void maintainTime() {
  if (WiFi.status() == WL_CONNECTED) { wifiOK = true; wifiRSSI = WiFi.RSSI(); wifiStatusText = "CONNECTED"; }
  else { wifiOK = false; connectWiFiNonBlocking(); }
  if (wifiOK && !timeOK) initNTP();
  if (millis() - lastTimeCheck > 30000UL) {
    lastTimeCheck = millis();
    struct tm t;
    if (getLocalTime(&t, 100)) timeOK = true;
    else if (wifiOK) initNTP();
  }
}

// =====================================================================
// TEMPERATURE
// =====================================================================
unsigned long lastTempRead = 0;
#define TEMP_INTERVAL 1000UL

void updateTemperatureSmooth() {
  if (!mlxOK || simulationMode) return;
  if (millis() - lastTempRead < TEMP_INTERVAL) return;
  lastTempRead = millis();
  float bn = mlx.readObjectTempC(), rn = mlx.readAmbientTempC();
  if (bn > 10.0f && bn < 50.0f) bodySmooth = bodySmooth * 0.65f + bn * 0.35f;
  if (rn > 5.0f  && rn < 50.0f) roomSmooth = roomSmooth * 0.75f + rn * 0.25f;
}

// =====================================================================
// MPU6050 — PHÁT HIỆN TÉ NGÃ
// =====================================================================
// ── Biến fall detection ───────────────────────────────────────────────
float motionLevel = 0, motionHistory[5] = {0}, motionSmooth = 0;
int   motionHistIdx = 0;
float lastAx = 0, lastAy = 0, lastAz = 1.0f, lastMag = 1.0f, lastDA = 0.0f;
unsigned long lastMPURead = 0;

// Trạng thái máy phát hiện té ngã — 3 giai đoạn rõ ràng
enum FallFSM { FF_IDLE, FF_IMPACT_WAIT, FF_TILT_CHECK, FF_STILL_WAIT };
FallFSM fallFSM = FF_IDLE;
unsigned long fallFSMStart = 0;   // thời điểm bắt đầu giai đoạn hiện tại

// Ngưỡng 3 giai đoạn
#define FALL_IMPACT_G        2.5f   // gia tốc tổng coi là va chạm (g)
#define FALL_IMPACT_WINDOW   300UL  // window tìm va chạm sau lần đầu (ms)
#define FALL_TILT_DEG        55.0f  // góc nghiêng tối thiểu để xác nhận (độ)
#define FALL_TILT_WINDOW     500UL  // thời gian tối đa kiểm tra góc (ms)
#define FALL_STILL_SEC      3000UL  // nằm yên ít nhất 3 giây (ms)
#define FALL_STILL_GYRO     0.3f    // gyro max khi "yên" (rad/s)
#define FALL_STILL_ACC_VAR  0.15f   // độ biến thiên acc tối đa khi "yên"
#define FALL_COOLDOWN       8000UL  // không phát hiện lại sau khi confirm (ms)
#define MPU_INTERVAL_MS       20UL

// Biến theo dõi giai đoạn nằm yên
float stillAccPrev = 0;
int   stillCounter = 0;
#define STILL_SAMPLES_NEEDED  20    // ~400ms tại 20ms/sample × 3s ≈ 150 mẫu — dùng 20ms loop

float angleX_deg = 0, angleY_deg = 0;

float median5(float *a) {
  float t[5]; memcpy(t, a, sizeof(t));
  for (int i = 0; i < 4; i++)
    for (int j = 0; j < 4 - i; j++)
      if (t[j] > t[j + 1]) { float x = t[j]; t[j] = t[j + 1]; t[j + 1] = x; }
  return t[2];
}

void triggerFallAlert() {
  vibeMode     = VIBE_CONTINUOUS;
  vibePhaseEnd = millis() + 3000UL;
  motorSet(true, MOTOR_LEVEL_STRONG);
}


unsigned long fallBeepStart    = 0;
bool          fallBeepActive   = false;
#define FALL_BEEP_DURATION_MS  10000UL  // Beep trong 10 giây

void startFallBeep() {
  fallBeepStart  = millis();
  fallBeepActive = true;
}

void updateFallBeep() {
  if (!fallBeepActive) return;
  if (millis() - fallBeepStart > FALL_BEEP_DURATION_MS) {
    fallBeepActive = false;
    return;
  }
  // Rung motor theo nhịp SOS: 3 ngắn - 3 dài - 3 ngắn
  // (Motor đã được xử lý trong updateMotor(), hàm này chỉ quản lý cờ)
}

void startFallAlert() {
  fallConfirmed = true;
  fallAlertEnd  = millis() + 15000UL;
  fallFSM       = FF_IDLE;
  fallFSMStart  = 0;
  stillCounter  = 0;

  // Gọi activateAlert TRƯỚC (nó sẽ ttsStop + playClip EMER1)
  activateAlert(ALERT_EMERGENCY, "Te nga duoc phat hien!",
                bpmDisplay, spo2Display, getBodyTempDisplay());
  triggerFallAlert();

  // Sau đó override: play CLIP_FALL ngay, queue CLIP_EMER_CALL tiếp theo
  ttsStop();
  playClip(CLIP_FALL);
  ttsQueuedClip = CLIP_EMER_CALL;
  ttsQueued     = true;

  Serial.println("[FALL] Audio: fall.wav → emer_call.wav");
}

void updateMPU() {
  if (!mpuOK) return;
  unsigned long now = millis();

  // Giải phóng sau thời gian cảnh báo
  if (fallConfirmed && now > fallAlertEnd) {
    fallConfirmed   = false;
    fallCooldownEnd = now + FALL_COOLDOWN;
  }

  if (now - lastMPURead < MPU_INTERVAL_MS) return;
  lastMPURead = now;

  sensors_event_t accel, gyro, temp;
  mpu.getEvent(&accel, &gyro, &temp);

  // Đổi sang đơn vị g
  float ax = accel.acceleration.x / 9.81f;
  float ay = accel.acceleration.y / 9.81f;
  float az = accel.acceleration.z / 9.81f;
  float mag = sqrtf(ax*ax + ay*ay + az*az);

  // Tính góc nghiêng từ acc (đơn vị độ)
  angleX_deg = atan2f(ay, sqrtf(ax*ax + az*az)) * 57.2957795f;
  angleY_deg = atan2f(ax, sqrtf(ay*ay + az*az)) * 57.2957795f;

  // Cập nhật motion level để hiển thị màn Motion
  float dA = fabsf(mag - lastMag);
  motionLevel = motionLevel * 0.88f + dA * 0.12f;
  motionHistory[motionHistIdx % 5] = motionLevel;
  motionHistIdx++;
  motionSmooth = median5(motionHistory);

  lastAx = ax; lastAy = ay; lastAz = az;
  lastMag = mag; lastDA = dA;

  // Gyro magnitude (rad/s)
  float gx = gyro.gyro.x, gy = gyro.gyro.y, gz = gyro.gyro.z;
  float gyroMag = sqrtf(gx*gx + gy*gy + gz*gz);

  // ── Không phát hiện trong cooldown ────────────────────────────────
  if (now < fallCooldownEnd || fallConfirmed) return;

  // ──────────────────────────────────────────────────────────────────
  // MÁY TRẠNG THÁI 3 GIAI ĐOẠN
  // ──────────────────────────────────────────────────────────────────
  switch (fallFSM) {

    // ── GIAI ĐOẠN 0: Chờ va chạm ────────────────────────────────────
    case FF_IDLE:
      if (mag > fallImpactG) {
        // Va chạm phát hiện! Chuyển sang kiểm tra góc nghiêng
        fallFSM      = FF_TILT_CHECK;
        fallFSMStart = now;
        Serial.printf("[FALL] Impact! mag=%.2fg angle=%.1f/%.1f\n",
                      mag, angleX_deg, angleY_deg);
      }
      break;

    // ── GIAI ĐOẠN 1: Kiểm tra góc nghiêng trong FALL_TILT_WINDOW ───
    case FF_TILT_CHECK:
      if (now - fallFSMStart > FALL_TILT_WINDOW) {
        // Hết thời gian mà góc chưa đủ → không phải té ngã
        Serial.println("[FALL] Tilt timeout — reset");
        fallFSM = FF_IDLE;
        break;
      }
      if (fabsf(angleX_deg) > fallTiltDeg || fabsf(angleY_deg) > fallTiltDeg) {
        // Góc nghiêng đủ lớn → chuyển sang theo dõi nằm yên
        fallFSM      = FF_STILL_WAIT;
        fallFSMStart = now;
        stillCounter = 0;
        stillAccPrev = mag;
        Serial.printf("[FALL] Tilt confirmed! angle=%.1f/%.1f — watching stillness\n",
                      angleX_deg, angleY_deg);
      }
      break;

    // ── GIAI ĐOẠN 2: Theo dõi nằm yên 3 giây ───────────────────────
    case FF_STILL_WAIT:
      if (now - fallFSMStart > FALL_STILL_SEC + 1000UL) {
        // Quá timeout → reset (người đã đứng dậy trước khi confirm)
        Serial.println("[FALL] Still timeout — reset");
        fallFSM = FF_IDLE;
        stillCounter = 0;
        break;
      }
      {
        float accVar = fabsf(mag - stillAccPrev);
        stillAccPrev = mag;

        bool stillNow = (gyroMag < FALL_STILL_GYRO && accVar < FALL_STILL_ACC_VAR);

        if (stillNow) {
          stillCounter++;
        } else {
          // Cử động → reset bộ đếm (phải nằm yên liên tục)
          stillCounter = 0;
        }

        // Nằm yên đủ số mẫu trong FALL_STILL_SEC
        int samplesNeeded = (int)(fallStillMs / MPU_INTERVAL_MS);
        if (stillCounter >= samplesNeeded) {
          Serial.println("[FALL] CONFIRMED — Te nga!");
          startFallAlert();
        }
      }
      break;
  }
}
// =====================================================================
// BPM — Peak Valley
// =====================================================================
#define PV_HISTORY 24
float pvBuf[PV_HISTORY]; int pvIdx = 0;
float pvDC = 0, pvMin = 1e9f, pvMax = -1e9f, pvThresh = 0;
bool pvWasBelow = true;
unsigned long pvRefractEnd = 0;
int pvWarmup = 30;
#define BPM_BUF 8
float bpmRaw[BPM_BUF]; int bpmBufIdx = 0, bpmBufCount = 0;
unsigned long lastBeatMs = 0;
bool beatAnim = false; unsigned long beatAnimEnd = 0;
unsigned long heartBeatInterval = 750, nextHeartBeat = 0;
bool heartBig = false;

void updateHeartBeatTiming() {
  if (bpmDisplay > 30 && bpmDisplay < 220)
    heartBeatInterval = (unsigned long)(60000.0f / bpmDisplay);
}

void bubbleSort(float *a, int n) {
  for (int i = 0; i < n - 1; i++)
    for (int j = 0; j < n - i - 1; j++)
      if (a[j] > a[j + 1]) { float t = a[j]; a[j] = a[j + 1]; a[j + 1] = t; }
}

float medianBPM(float *arr, int n) {
  float tmp[BPM_BUF];
  for (int i = 0; i < n; i++) tmp[i] = arr[i];
  bubbleSort(tmp, n);
  if (n % 2 == 0) return (tmp[n / 2 - 1] + tmp[n / 2]) / 2.0f;
  return tmp[n / 2];
}

void addBeat(unsigned long nowMs) {
  if (lastBeatMs == 0) { lastBeatMs = nowMs; return; }
  unsigned long delta = nowMs - lastBeatMs;
  lastBeatMs = nowMs; lastBeatTime = nowMs;
  if (delta < 380 || delta > 1580) return;
  float bpm = 60000.0f / (float)delta;
  if (bpm < 38 || bpm > 180) return;
  bpmRaw[bpmBufIdx % BPM_BUF] = bpm; bpmBufIdx++;
  if (bpmBufCount < BPM_BUF) bpmBufCount++;
  int n = min(bpmBufCount, BPM_BUF);
  if (n < 2) { bpmDisplay = bpm; return; }
  float med = medianBPM(bpmRaw, n);
  bpmDisplay = (bpmDisplay == 0) ? med : (bpmDisplay * 0.75f + med * 0.25f);
  updateHeartBeatTiming();
}

bool peakValleyBeat(float rawIR) {
  if (pvDC == 0) pvDC = rawIR;
  pvDC = pvDC * 0.97f + rawIR * 0.03f;
  float ac = rawIR - pvDC;
  if (pvWarmup > 0) { pvWarmup--; pvMin = ac; pvMax = ac; return false; }
  pvBuf[pvIdx % PV_HISTORY] = ac; pvIdx++;
  float mn = 1e9f, mx = -1e9f;
  int used = min(pvIdx, PV_HISTORY);
  for (int i = 0; i < used; i++) { if (pvBuf[i] < mn) mn = pvBuf[i]; if (pvBuf[i] > mx) mx = pvBuf[i]; }
  pvMin = mn; pvMax = mx;
  float amp = pvMax - pvMin; if (amp < 200.0f) return false;
  pvThresh = pvMin + amp * 0.60f;
  bool beat = false;
  if (ac > pvThresh && pvWasBelow && millis() > pvRefractEnd) {
    beat = true; pvRefractEnd = millis() + 350; pvWasBelow = false;
  }
  if (ac < pvMin + amp * 0.35f) pvWasBelow = true;
  return beat;
}

void resetPeakValley() {
  pvIdx = 0; pvDC = 0; pvMin = 1e9f; pvMax = -1e9f;
  pvThresh = 0; pvWasBelow = true; pvRefractEnd = 0; pvWarmup = 30;
  for (int i = 0; i < PV_HISTORY; i++) pvBuf[i] = 0;
}

// =====================================================================
// SPO2
// =====================================================================
#define SPO2_N 100
long irBuf[SPO2_N], redBuf[SPO2_N];
int spo2Idx = 0, spo2SampleCount = 0;
float spo2Prev = 0;
unsigned long lastSpo2Ms = 0;
#define SPO2_INTERVAL 1500UL

void pushSpo2Sample(long ir, long red) {
  irBuf[spo2Idx] = ir; redBuf[spo2Idx] = red;
  if (++spo2Idx >= SPO2_N) spo2Idx = 0;
  if (spo2SampleCount < SPO2_N) spo2SampleCount++;
}

void calcSpO2() {
  if (spo2SampleCount < 50) return;
  if (motionSmooth > MOTION_THRESH_SPO2) return;
  int n = min(spo2SampleCount, SPO2_N);
  double dcIR = 0, dcRed = 0;
  for (int i = 0; i < n; i++) { dcIR += irBuf[i]; dcRed += redBuf[i]; }
  dcIR /= n; dcRed /= n;
  if (dcIR < 20000 || dcRed < 5000) return;
  double rmsIR = 0, rmsRed = 0;
  for (int i = 0; i < n; i++) {
    double dIR = irBuf[i] - dcIR, dRed = redBuf[i] - dcRed;
    rmsIR += dIR * dIR; rmsRed += dRed * dRed;
  }
  double acIR = sqrtf(rmsIR / n), acRed = sqrtf(rmsRed / n);
  if (acIR < 100 || acRed < 50) return;
  double piIR = acIR / dcIR; if (piIR < 0.001 || piIR > 0.15) return;
  double R = (acRed / dcRed) / (acIR / dcIR); if (R < 0.40 || R > 1.50) return;
  double raw = 110.0 - 14.0 * R + SPO2_FINGER_OFFSET;
  raw = constrain(raw, 85.0, 100.0);
  float sn = (float)raw;
  if (spo2Prev > 0 && fabsf(sn - spo2Prev) > 5.0f) { spo2Prev = sn; return; }
  spo2Prev = sn;
  spo2Display = (spo2Display == 0) ? sn : (spo2Display * 0.65f + sn * 0.35f);
}

// =====================================================================
// CONTACT
// =====================================================================
int  contactScore = 0;
long irDCEst = 0;

bool isContact(long ir, long red) {
  bool raw = (ir > IR_CONTACT_THRESH && red > RED_CONTACT_THRESH);
  if (raw) { if (contactScore < 20) contactScore++; }
  else     { if (contactScore > 0)  contactScore--; }
  return contactScore >= CONTACT_SCORE_LOCK;
}

unsigned long noContactSince = 0, lastContactSampleMs = 0;
int contactSampleCount = 0;
float lastAlertSpo2 = 0, lastAlertBpm = 0;
unsigned long lastAlertCheckSound = 0;

void checkAndAlert(float bpm, float spo2) {
  if (millis() - lastAlertCheckSound < 5000UL) return;
  lastAlertCheckSound = millis();
  if (spo2 > 0 && spo2 < SPO2_LOW_THRESHOLD && fabsf(spo2 - lastAlertSpo2) > 0.5f) {
    lastAlertSpo2 = spo2;
    playClipQueued(CLIP_SPO2_LOW);
  }
  if (bpm > 0 && (bpm < BPM_LOW_THRESHOLD || bpm > BPM_HIGH_THRESHOLD) && fabsf(bpm - lastAlertBpm) > 1.0f) {
    lastAlertBpm = bpm;
    playClipQueued(CLIP_BPM_BAD);
  }
}

void resetHeart() {
  bpmDisplay = 0; bpmBufIdx = 0; bpmBufCount = 0;
  spo2Display = 0; spo2Prev = 0; spo2Idx = 0; spo2SampleCount = 0;
  beatAnim = false; lastBeatMs = 0; irDCEst = 0; lastSpo2Ms = 0;
  agcLocked = false; contactScore = 0; lastAlertSpo2 = 0; lastAlertBpm = 0;
  noContactSince = 0; ledPower = 0x7F;
  for (int i = 0; i < BPM_BUF; i++) bpmRaw[i] = 0;
  resetPeakValley(); sw_init();
  contactSampleCount = 0; lastContactSampleMs = 0;
  heartBig = false; nextHeartBeat = 0; lastBeatTime = 0;
}

void doAGC(long irDC) {
  if (millis() - lastAGC < AGC_INTERVAL) return;
  lastAGC = millis();
  bool changed = false;
  if (irDC < AGC_TARGET_LO && ledPower < 0xFF) { ledPower = min(0xFF, (int)ledPower + 0x08); changed = true; agcLocked = false; }
  else if (irDC > AGC_TARGET_HI && ledPower > 0x10) { ledPower = max(0x10, (int)ledPower - 0x08); changed = true; agcLocked = false; }
  else agcLocked = true;
  if (changed) { particleSensor.setPulseAmplitudeRed(ledPower); particleSensor.setPulseAmplitudeIR(ledPower); }
}

// =====================================================================
// BUTTON SYSTEM
// =====================================================================
struct ButtonState {
  int pin; bool lastState, currentState;
  unsigned long pressedAt, lastReleaseAt;
  bool held, holdFired2s, holdFired3s, holdFired5s;
  int clickCount; unsigned long lastClickAt; bool waitingDoubleClick;
};
ButtonState btn1 = {BTN1_PIN, HIGH, HIGH, 0, 0, false, false, false, false, 0, 0, false};
ButtonState btn2 = {BTN2_PIN, HIGH, HIGH, 0, 0, false, false, false, false, 0, 0, false};
ButtonState btn3 = {BTN3_PIN, HIGH, HIGH, 0, 0, false, false, false, false, 0, 0, false};

#define DOUBLE_CLICK_WINDOW 500UL
#define HOLD_2S 2000UL
#define HOLD_3S 3000UL
#define HOLD_5S 5000UL
#define SCREEN_ALERT  4
#define SCREEN_DUEDATE  5
#define SCREEN_COUNT  6


bool pendingSOS = false;

void onBtn1ShortPress() {
  int next = screenMode + 1;
  if (next >= SCREEN_COUNT) next = 0;
  if (next == SCREEN_ALERT) next++;
  if (next >= SCREEN_COUNT) next = 0;
  screenMode = next;

  if (screenMode == 2) resetHeart();

  if (screenMode == SCREEN_DUEDATE && wifiOK) {
    firebaseFetchPending = true;
    display.clearDisplay();
    showDueDateScreen();
    display.display();
    fetchFirebaseData();
    firebaseFetchPending = false;
  }
}

// void onBtn1Hold3s() { toggleSimulationMode(); }  // Đã chuyển sang BTN3

void onBtn1Hold5s() { pendingSOS = true; }
void onBtn3ShortPress() {
  toggleSimulationMode();
}
// ─── BTN2 REAL ───────────────────────────────────────────────────────
void onBtn2Press_Real() {
  // Đang cảnh báo bất kỳ tầng nào → xác nhận, về NORMAL
  if (alertLevel > ALERT_NORMAL || fallConfirmed) {
    confirmAndReset();
    return;
  }
  // Bình thường → mở màn Alert Status
  screenMode = SCREEN_ALERT;
}

// ─── BTN2 SIM ────────────────────────────────────────────────────────
void onBtn2Press_Sim() {
  simScenario = (simScenario + 1) % 4;
  ttsStop();
  switch (simScenario) {
    case 0:
      alertLevel = ALERT_NORMAL; motorOff();
      alertReason = ""; ttsState = TTS_IDLE;
      playClip(CLIP_NORMAL); break;
    case 1:
      activateAlert(ALERT_WARNING, "[SIM] Nhip tim hoi cao", 108.f, 94.5f, 37.6f); break;
    case 2:
      activateAlert(ALERT_DANGER, "[SIM] SpO2 thap", 125.f, 91.5f, 38.3f); break;
    case 3:
      activateAlert(ALERT_EMERGENCY, "[SIM] KHAN CAP", 148.f, 88.f, 39.5f); break;
  }
}

// ─── BTN2 Hold 3s (mọi mode) ─────────────────────────────────────────
void onBtn2Hold3s_Any() {
  // Reset cooldown để gửi được ngay
  lastTelegramSOS = 0;
  pendingSOS = true;
  ttsStop();
  playClip(CLIP_SOS_MANUAL);
  activateAlert(ALERT_EMERGENCY,
    simulationMode ? "[SIM] User nhan SOS!" : "User nhan SOS khan cap!",
    bpmDisplay, spo2Display, getBodyTempDisplay());
}

// ─── Hàm xác nhận chung ──────────────────────────────────────────────
void confirmAndReset() {
  // Fall confirmed
  if (fallConfirmed) {
    fallConfirmed = false;
    fallCooldownEnd = millis() + FALL_COOLDOWN;
    ttsStop();
    playClip(CLIP_CONFIRM_FALL);
  } else {
    ttsStop();
    playClip(CLIP_CONFIRMED);
  }
  // Reset về NORMAL
  alertLevel    = ALERT_NORMAL;
  alertReason   = "";
  alertConfirmed = true;
  inRecovery    = false;
  motorOff();
  vibeMode     = VIBE_OFF;
  ttsState     = TTS_IDLE;
  breathGuideActive = false;
  screenMode   = 2;   // về màn đo
  Serial.println("[BTN2] Confirmed → NORMAL");
}
void updateButton(ButtonState &btn,
  void (*onShortPress)(), void (*onHold2s)() = nullptr,
  void (*onHold3s)()    = nullptr, void (*onHold5s)() = nullptr,
  void (*onDouble)()    = nullptr)
{
  bool raw = digitalRead(btn.pin);
  unsigned long now = millis();
  if (raw != btn.lastState) btn.lastState = raw;
  btn.currentState = raw;
  bool pressed = (btn.currentState == LOW);

  if (pressed && !btn.held && btn.pressedAt == 0) {
    btn.pressedAt = now; btn.held = false;
    btn.holdFired2s = btn.holdFired3s = btn.holdFired5s = false;
  }
  if (pressed && btn.pressedAt > 0) {
    unsigned long dur = now - btn.pressedAt;
    if (dur >= HOLD_5S && !btn.holdFired5s && onHold5s) { btn.holdFired5s = true; onHold5s(); }
    else if (dur >= HOLD_3S && !btn.holdFired3s && onHold3s) { btn.holdFired3s = true; onHold3s(); }
    else if (dur >= HOLD_2S && !btn.holdFired2s && onHold2s) { btn.holdFired2s = true; onHold2s(); }
    btn.held = (dur >= HOLD_2S);
  }
  if (!pressed && btn.pressedAt > 0) {
    unsigned long dur = now - btn.pressedAt; btn.pressedAt = 0;
    if (!btn.holdFired2s && !btn.holdFired3s && !btn.holdFired5s && dur < HOLD_2S) {
      if (onDouble && now - btn.lastClickAt < DOUBLE_CLICK_WINDOW && btn.clickCount >= 1) {
        btn.clickCount = 0; btn.waitingDoubleClick = false; onDouble();
      } else {
        btn.clickCount++; btn.lastClickAt = now; btn.waitingDoubleClick = true;
      }
    }
    btn.held = false;
  }
  if (btn.waitingDoubleClick && btn.clickCount >= 1 &&
      now - btn.lastClickAt > DOUBLE_CLICK_WINDOW && btn.pressedAt == 0) {
    btn.waitingDoubleClick = false;
    int cnt = btn.clickCount; btn.clickCount = 0;
    if (cnt == 1 && onShortPress) onShortPress();
    else if (cnt >= 2 && onDouble)  onDouble();
  }
}


// ─── handleButtons() mới ─────────────────────────────────────────────
void handleButtons() {
  updateButton(btn1,
    onBtn1ShortPress,   // short = chuyển màn
    nullptr,
    nullptr,            // hold 3s = bỏ (đã sang BTN3)
    onBtn1Hold5s,       // hold 5s = SOS
    nullptr);

  // BTN3: toggle SIM/REAL (nhấn ngắn)
  updateButton(btn3,
    onBtn3ShortPress,   // short = toggle SIM/REAL
    nullptr,
    nullptr,
    nullptr,
    nullptr);

  if (simulationMode) {
    updateButton(btn2,
      onBtn2Press_Sim,
      nullptr,
      onBtn2Hold3s_Any,
      nullptr,
      nullptr);
  } else {
    updateButton(btn2,
      onBtn2Press_Real,
      nullptr,
      onBtn2Hold3s_Any,
      nullptr,
      nullptr);
  }
}
// =====================================================================
// UI HELPERS
// =====================================================================
void drawHeart(int cx, int cy, bool big) {
  if (big) {
    display.fillCircle(cx - 4, cy - 2, 5, SH110X_WHITE);
    display.fillCircle(cx + 4, cy - 2, 5, SH110X_WHITE);
    display.fillTriangle(cx - 9, cy + 1, cx + 9, cy + 1, cx, cy + 9, SH110X_WHITE);
  } else {
    display.fillCircle(cx - 2, cy - 1, 3, SH110X_WHITE);
    display.fillCircle(cx + 2, cy - 1, 3, SH110X_WHITE);
    display.fillTriangle(cx - 5, cy + 1, cx + 5, cy + 1, cx, cy + 5, SH110X_WHITE);
  }
}

void drawModeBadge() {
  display.setTextSize(1);
  if (simulationMode) { display.setCursor(155, 55); display.print("S"); }
  else                { display.setCursor(115, 55); display.print("R"); }
}

void drawTTSBadge() {
  if (!ttsEnabled) return;
  display.setTextSize(1);
  display.setCursor(110, 0);
  if (ttsPlaying)     display.print("*");
  else if (ttsQueued) display.print("q");
}

// =====================================================================
// UI: ALERT ANNOUNCE SCREEN
// =====================================================================
void showAlertAnnounce() {
  unsigned long now = millis();
  unsigned long elapsed = now - alertAnnounceStart;
  if (elapsed > ALERT_ANNOUNCE_MS) { alertAnnounceActive = false; return; }

  display.clearDisplay();
  display.drawRect(0, 0, 128, 64, SH110X_WHITE);
  if (announceLevel == ALERT_EMERGENCY && (now / 150) % 2)
    display.drawRect(2, 2, 124, 60, SH110X_WHITE);

  display.setTextSize(2);
  switch (announceLevel) {
    case ALERT_WARNING:
      display.setCursor(8, 4); display.print("! TANG 1 !");
      break;
    case ALERT_DANGER:
      display.setCursor(4, 4);
      if ((now / 300) % 2) display.print("!! TANG 2 !!");
      else                 display.print("  NGUY HIE ");
      break;
    case ALERT_EMERGENCY:
      display.setCursor(4, 4);
      if ((now / 200) % 2) display.print("!!! SOS !!!");
      else                 display.print("!KHAN CAP! ");
      break;
    default: break;
  }

  display.drawLine(0, 22, 127, 22, SH110X_WHITE);
  display.setTextSize(1);
  String reason = announceReason;
  if (reason.length() > 42) reason = reason.substring(0, 39) + "...";
  if (reason.length() > 21) {
    display.setCursor(2, 24); display.print(reason.substring(0, 21));
    display.setCursor(2, 33); display.print(reason.substring(21, 42));
  } else {
    display.setCursor(2, 28); display.print(reason);
  }

  switch (announceLevel) {
    case ALERT_WARNING:   display.setCursor(2, 44); display.print("* Tho sau 4-7-8"); break;
    case ALERT_DANGER:    display.setCursor(2, 44); display.print("* Nghi ngoi ngay!"); break;
    case ALERT_EMERGENCY: display.setCursor(2, 44); display.print("* Goi 115 / SOS!"); break;
    default: break;
  }

  if (ttsPlaying) { display.setCursor(95, 44); display.print("[WAV]"); }

  unsigned long remaining = ALERT_ANNOUNCE_MS - elapsed;
  int barW = (int)((float)remaining / ALERT_ANNOUNCE_MS * 124.0f);
  display.drawRect(2, 55, 124, 6, SH110X_WHITE);
  display.fillRect(2, 55, barW, 6, SH110X_WHITE);
  display.display();
}

// =====================================================================
// UI: CLOCK
// =====================================================================
void showClockScreen() {
  display.drawRect(0, 0, 128, 64, SH110X_WHITE);
  display.setTextSize(1);
  display.setCursor(28, 2); display.print("PREGCARE v5.4");
  display.drawLine(0, 12, 127, 12, SH110X_WHITE);

  struct tm t;
  if (!getLocalTime(&t, 50)) {
    display.setTextSize(2); display.setCursor(34, 22); display.print("--:--");
    display.setTextSize(1); display.setCursor(8, 46);
    if (!wifiOK) display.print("WiFi:WAIT");
    else display.print("NTP syncing...");
    drawModeBadge(); return;
  }
  display.setTextSize(3); display.setCursor(7, 20);
  if (t.tm_hour < 10) display.print('0');
  display.print(t.tm_hour); display.print(':');
  if (t.tm_min  < 10) display.print('0');
  display.print(t.tm_min);
  display.setTextSize(1); display.setCursor(105, 24); display.print("s");
  display.setCursor(105, 34);
  if (t.tm_sec < 10) display.print('0'); display.print(t.tm_sec);
  display.setCursor(6, 52);
  if (t.tm_mday < 10) display.print('0'); display.print(t.tm_mday); display.print('/');
  if ((t.tm_mon + 1) < 10) display.print('0'); display.print(t.tm_mon + 1); display.print('/');
  display.print(t.tm_year + 1900);
  if (alertLevel > ALERT_NORMAL) {
    display.setCursor(90, 52);
    if (alertLevel == ALERT_WARNING)   display.print("WARN");
    if (alertLevel == ALERT_DANGER)    display.print("DANG");
    if (alertLevel == ALERT_EMERGENCY && (millis() / 400) % 2) display.print("SOS!");
  } else drawModeBadge();
  drawTTSBadge();
}

// =====================================================================
// UI: TEMP
// =====================================================================
void drawThermometer(int x, int y, float tempC) {
  int tw = 6, th = 36, bx = x, by = y + th + 6;
  display.drawRect(bx - tw / 2, y, tw, th, SH110X_WHITE);
  display.fillCircle(bx, by, 6, SH110X_WHITE);
  display.fillCircle(bx, by, 4, SH110X_BLACK);
  float tMin = 35.0f, tMax = 40.5f;
  float fraction = constrain((tempC - tMin) / (tMax - tMin), 0.0f, 1.0f);
  int fillH = (int)(fraction * (th - 2));
  if (fillH > 0) display.fillRect(bx - tw / 2 + 1, y + th - 1 - fillH, tw - 2, fillH, SH110X_WHITE);
  display.fillRect(bx - 1, by - 6, 3, 8, SH110X_WHITE);
}

void showTempScreen() {
  updateTemperatureSmooth();
  float bd = getBodyTempDisplay();
  display.drawRect(0, 0, 128, 64, SH110X_WHITE);
  display.setTextSize(1); display.setCursor(22, 2); display.print("NHIET DO CO THE");
  display.drawLine(0, 12, 127, 12, SH110X_WHITE);
  drawThermometer(10, 13, bd);
  display.setTextSize(3); display.setCursor(36, 14); display.print(bd, 1);
  display.setTextSize(1); display.setCursor(106, 28); display.print("oC");
  display.setCursor(38, 40);
  if (bd >= 39.0f) { if ((millis() / 500) % 2) display.print("!! SOT CAO !!"); }
  else if (bd >= 38.0f) display.print("> SOT NHE <");
  else if (bd >= 37.5f) display.print("Tang nhe");
  else if (bd >= 36.0f) display.print("Binh thuong");
  else                  display.print("Hoi thap");
  display.setCursor(38, 50);
  if (simulationMode) { display.print("SIM "); display.print(simTemp, 1); }
  else { display.print("Phong:"); display.print(roomSmooth, 1); display.print("C"); }
  drawModeBadge(); drawTTSBadge();
}

// =====================================================================
// UI: HEART REAL
// =====================================================================
void showHeartScreenReal() {
  if (!maxOK) {
    display.drawRect(0, 0, 128, 64, SH110X_WHITE); display.setTextSize(1);
    display.setCursor(14, 26); display.print("MAX30102 LOI");
    display.setCursor(6, 38); display.print("Kiem tra ket noi"); return;
  }
  particleSensor.check(); bool anyContact = false;
  while (particleSensor.available()) {
    long irRaw = particleSensor.getFIFOIR(), redRaw = particleSensor.getFIFORed();
    particleSensor.nextSample();
    if (irDCEst == 0) irDCEst = irRaw; else irDCEst = (irDCEst * 31 + irRaw) / 32;
    bool contactNow = isContact(irRaw, redRaw);
    if (!contactNow) { if (noContactSince == 0) noContactSince = millis(); continue; }
    noContactSince = 0; anyContact = true; doAGC(irDCEst);
    if (peakValleyBeat((float)irRaw)) {
      unsigned long n2 = millis(); addBeat(n2);
      beatAnim = true; beatAnimEnd = n2 + 200;
    }
    if (motionSmooth <= MOTION_THRESH_SPO2) pushSpo2Sample(irRaw, redRaw);
    if (millis() - lastSpo2Ms > SPO2_INTERVAL) { calcSpO2(); lastSpo2Ms = millis(); }
    checkAndAlert(bpmDisplay, spo2Display);
  }
  if (!anyContact && noContactSince > 0 && millis() - noContactSince > CONTACT_RESET_MS) resetHeart();
  if (millis() > beatAnimEnd) beatAnim = false;

  long irNow = particleSensor.getIR(), redNow = particleSensor.getRed();
  bool contact = isContact(irNow, redNow);
  unsigned long now = millis();

  if (contact && now - lastContactSampleMs >= 1000UL) {
    lastContactSampleMs = now;
    if (contactSampleCount < SLIDE_MIN_VALID) contactSampleCount++;
  }
  if (contact && now - sw.lastSampleMs >= (1000UL / SLIDE_SAMPLE_HZ)) {
    sw.lastSampleMs = now;
    sw_addSample(bpmDisplay, spo2Display,
      bpmDisplay > 40 && bpmDisplay < 200 && motionLevel <= MOTION_THRESH_HR,
      spo2Display > 85 && spo2Display <= 100 && motionSmooth <= MOTION_THRESH_SPO2);
  }
  if (now - sw.lastUpdateMs >= SLIDE_UPDATE_MS) { sw.lastUpdateMs = now; sw_updateAvg(); }

  float td = mlxOK ? getBodyTempDisplay() : 0;
  updateAlertSystem(bpmDisplay, spo2Display, td, fallConfirmed);

  int uiState = (!contact) ? 0 : (contactSampleCount < SLIDE_MIN_VALID) ? 1 : 2;

  display.drawRect(0, 0, 128, 64, SH110X_WHITE);
  display.drawLine(1, 10, 126, 10, SH110X_WHITE);
  display.setTextSize(1); display.setCursor(10, 2); display.print("NHIP TIM | SpO2");
  drawTTSBadge();

  if (alertLevel > ALERT_NORMAL) {
    if (alertLevel == ALERT_WARNING)   { display.setCursor(110, 2); display.print("W1"); }
    if (alertLevel == ALERT_DANGER)    { display.setCursor(110, 2); display.print("W2"); }
    if (alertLevel == ALERT_EMERGENCY && (now / 300) % 2) { display.setCursor(106, 2); display.print("SOS"); }
  }

  if (uiState == 0) {
    display.drawLine(64, 10, 64, 47, SH110X_WHITE);
    display.setTextSize(1);
    display.setCursor(3, 14); display.print("Dat ngon");
    display.setCursor(3, 24); display.print("tay len");
    display.setCursor(3, 34); display.print("cam bien");
    display.setCursor(67, 14); display.print("IR:"); display.print(irNow);
    display.setCursor(67, 24); display.print("P:0x"); display.print(ledPower, HEX);
    display.drawLine(1, 47, 126, 47, SH110X_WHITE); return;
  }
  if (uiState == 1) {
    display.setTextSize(1);
    display.setCursor(3, 13); display.print("Dang khoi dong...");
    display.setCursor(3, 24); display.print("Mau:"); display.print(contactSampleCount); display.print("/"); display.print(SLIDE_MIN_VALID);
    display.drawRect(3, 32, 122, 7, SH110X_WHITE);
    int fill = contactSampleCount * 120 / SLIDE_MIN_VALID;
    display.fillRect(4, 33, fill, 5, SH110X_WHITE);
    if (bpmDisplay > 0)  { display.setCursor(3, 42);  display.print("BPM:"); display.print((int)round(bpmDisplay)); }
    if (spo2Display > 0) { display.setCursor(67, 42); display.print("O2:");  display.print((int)round(spo2Display)); display.print("%"); }
    display.drawLine(1, 47, 126, 47, SH110X_WHITE);
    display.setCursor(3, 50);
    if (motionSmooth > MOTION_THRESH_SPO2) display.print("! Giu ngon tay yen !");
    else display.print("Giu, khong an manh");
    return;
  }

  display.drawLine(64, 10, 64, 47, SH110X_WHITE);
  int bpmShow = (sw.avgBpm > 0) ? (int)round(sw.avgBpm) : (bpmDisplay > 0 ? (int)round(bpmDisplay) : 0);
  display.setTextSize(2);
  if (bpmShow > 0) { display.setCursor((bpmShow >= 100) ? 2 : 8, 20); display.print(bpmShow); }
  else             { display.setCursor(8, 20); display.print("--"); }
  display.setTextSize(1); display.setCursor(44, 25); display.print("bpm");

  int spo2Show = (sw.avgSpo2 > 0) ? (int)round(sw.avgSpo2) : (spo2Display > 0 ? (int)round(spo2Display) : 0);
  display.setTextSize(2);
  if (spo2Show > 0) { display.setCursor((spo2Show >= 100) ? 66 : 72, 20); display.print(spo2Show); }
  else              { display.setCursor(72, 20); display.print("--"); }
  display.setTextSize(1); display.setCursor(110, 20); display.print("%");
  display.setCursor(100, 28); display.print("SpO2");

  display.drawLine(1, 47, 126, 47, SH110X_WHITE);
  unsigned long tSinceBeat = (lastBeatTime > 0) ? (now - lastBeatTime) : 9999;
  bool showBig = false;
  if (bpmDisplay > 0 && lastBeatTime > 0) {
    float bf = (float)(tSinceBeat % heartBeatInterval) / (float)heartBeatInterval;
    showBig = (bf < 0.30f);
  }
  drawHeart(64, 50, showBig);
  display.setTextSize(1);

  if (motionSmooth > MOTION_THRESH_HR)       { display.setCursor(2, 57); display.print("! DANG DONG !"); }
  else if (alertLevel == ALERT_WARNING)       { display.setCursor(2, 54); display.print("Tho 4-7-8"); }
  else if (alertLevel == ALERT_DANGER)        { if ((now / 400) % 2) { display.setCursor(2, 54); display.print("!! NGHI NGOI !!"); } }
  else if (sw.avgBpm > 0 || sw.avgSpo2 > 0) {
    unsigned long el = now - sw.lastUpdateMs;
    unsigned long rem = (SLIDE_UPDATE_MS > el) ? (SLIDE_UPDATE_MS - el) / 1000 : 0;
    display.setCursor(2, 54); display.print("TB:"); display.print(rem); display.print("s");
    if (spo2Show > 0 && spo2Show < (int)SPO2_LOW_THRESHOLD) {
      display.setCursor(87, 54); if ((now / 500) % 2) display.print("O2LOW!");
    } else { display.setCursor(87, 54); display.print("OK"); }
  } else { display.setCursor(2, 54); display.print("Thu thap..."); }
}

// =====================================================================
// UI: SIM SCREEN
// =====================================================================
void showHeartScreenSim() {
  unsigned long now = millis();
  display.drawRect(0, 0, 128, 64, SH110X_WHITE);
  display.setTextSize(1);
  display.setCursor(2, 2); display.print("SIM");
  display.setCursor(24, 2);
  switch (simScenario) {
    case 0: display.print("S0:Normal");  break;
    case 1: display.print("S1:Warning"); break;
    case 2: display.print("S2:Danger");  break;
    case 3: display.print("S3:Emerg");   break;
  }
  if (alertLevel > ALERT_NORMAL) {
    display.setCursor(96, 2);
    if (alertLevel == ALERT_WARNING)   display.print("[W1]");
    if (alertLevel == ALERT_DANGER)    display.print("[W2]");
    if (alertLevel == ALERT_EMERGENCY) display.print("[W3]");
  }
  drawTTSBadge();
  display.drawLine(0, 11, 127, 11, SH110X_WHITE);
  display.setTextSize(2);
  int bpmShow = (int)round(bpmDisplay);
  display.setCursor((bpmShow >= 100) ? 1 : 7, 14); display.print(bpmShow);
  display.setTextSize(1); display.setCursor(2, 30); display.print("bpm");
  display.drawLine(63, 11, 63, 46, SH110X_WHITE);
  display.setTextSize(2);
  int spo2Show = (int)round(spo2Display);
  display.setCursor((spo2Show >= 100) ? 65 : 71, 14); display.print(spo2Show);
  display.setTextSize(1);
  display.setCursor(109, 14); display.print("%");
  display.setCursor(98, 28); display.print("SpO2");
  display.drawLine(0, 37, 127, 37, SH110X_WHITE);
  display.setTextSize(1);
  float td = getBodyTempDisplay();
  display.setCursor(2, 40); display.print("T:"); display.print(td, 1); display.print("C");
  float bf = (float)(now % heartBeatInterval) / (float)heartBeatInterval;
  drawHeart(96, 42, bf < 0.25f);
  display.drawLine(0, 51, 127, 51, SH110X_WHITE);
  display.setCursor(2, 54);
  display.print("BTN2=KichBan BTN1 3s=REAL");
}

// =====================================================================
// UI: TẦNG 1 — THỞ 4-7-8
// =====================================================================
void showWarningScenario() {
  unsigned long now = millis();
  display.drawRect(0, 0, 128, 64, SH110X_WHITE);
  display.setTextSize(1);
  display.setCursor(26, 2); display.print("CANH BAO - T.1");
  drawTTSBadge();
  display.drawLine(0, 10, 127, 10, SH110X_WHITE);

  String phaseLabel = "";
  unsigned long phaseDuration = 0;
  switch (vibeMode) {
    case VIBE_BREATH_INHALE: phaseLabel = "HIT VAO"; phaseDuration = BREATH_INHALE_MS; break;
    case VIBE_BREATH_PAUSE:  phaseLabel = "GIU LAI"; phaseDuration = BREATH_PAUSE_MS;  break;
    case VIBE_BREATH_EXHALE: phaseLabel = "THO RA "; phaseDuration = BREATH_EXHALE_MS; break;
    default: phaseLabel = "THO SAU"; phaseDuration = 4000; break;
  }
  display.setTextSize(2);
  int px = 128 / 2 - (phaseLabel.length() * 12) / 2;
  display.setCursor(px < 0 ? 0 : px, 13); display.print(phaseLabel);
  display.setTextSize(1);
  unsigned long phaseElapsed = 0;
  if (vibePhaseEnd > now) phaseElapsed = phaseDuration - (vibePhaseEnd - now);
  unsigned long secLeft = (vibePhaseEnd > now) ? (vibePhaseEnd - now) / 1000 : 0;
  display.setCursor(50, 31); display.print(secLeft); display.print("s");
  display.setCursor(90, 31); display.print(breathCycleCount + 1); display.print("/3");
  display.drawRect(4, 38, 120, 6, SH110X_WHITE);
  int barW = 0;
  if (phaseDuration > 0) barW = (int)((float)phaseElapsed / phaseDuration * 118.0f);
  if (barW > 0) display.fillRect(5, 39, barW, 4, SH110X_WHITE);
  display.drawLine(0, 47, 127, 47, SH110X_WHITE);
  display.setCursor(2, 50);
  display.print("HR:");
  if (bpmDisplay > 0) display.print((int)round(bpmDisplay)); else display.print("--");
  display.print(" O2:");
  if (spo2Display > 0) { display.print((int)round(spo2Display)); display.print("%"); } else display.print("--");
  display.setCursor(2, 58); display.print("BTN2=OK");
  unsigned long tSB = (lastBeatTime > 0) ? (now - lastBeatTime) : 9999;
  bool sb = false;
  if (bpmDisplay > 0 && lastBeatTime > 0) {
    float f = (float)(tSB % heartBeatInterval) / (float)heartBeatInterval; sb = (f < 0.3f);
  }
  drawHeart(116, 57, sb);
}

// =====================================================================
// UI: TẦNG 2 — NGHỈ NGƠI
// =====================================================================
void showDangerScenario() {
  unsigned long now = millis();
  display.drawRect(0, 0, 128, 64, SH110X_WHITE);
  if ((now / 400) % 2) display.drawRect(2, 2, 124, 60, SH110X_WHITE);
  display.setTextSize(1);
  display.setCursor(16, 2); display.print("NGUY HIEM - TANG 2");
  drawTTSBadge();
  display.drawLine(0, 10, 127, 10, SH110X_WHITE);
  display.setTextSize(2); display.setCursor(14, 13); display.print("NGHI NGOI");
  display.setTextSize(1);
  unsigned long elapsed = now - danger_restStart;
  if (elapsed < DANGER_REST_MS) {
    unsigned long rem = (DANGER_REST_MS - elapsed) / 1000;
    unsigned long m = rem / 60, s = rem % 60;
    display.setCursor(4, 32); display.print("Con lai: ");
    if (m < 10) display.print('0'); display.print(m); display.print(':');
    if (s < 10) display.print('0'); display.print(s);
  } else {
    display.setCursor(4, 32); display.print("Da nghi du 5 phut");
  }
  display.setCursor(4, 42);
  String r = alertReason; if (r.length() > 21) r = r.substring(0, 18) + "...";
  display.print(r);
  display.drawLine(0, 51, 127, 51, SH110X_WHITE);
  display.setCursor(2, 54);
  if ((now / 500) % 2) display.print("BTN2=HA TANG | Hold=SOS");
  else                 display.print("Goi nguoi than ngay!");
}

// =====================================================================
// UI: TẦNG 3 — SOS KHẨN CẤP
// =====================================================================
void showEmergencyScenario() {
  unsigned long now = millis();
  display.drawRect(0, 0, 128, 64, SH110X_WHITE);
  if ((now / 150) % 2) display.drawRect(2, 2, 124, 60, SH110X_WHITE);
  display.setTextSize(2); display.setCursor(22, 3);
  if ((now / 200) % 2) display.print("!!! SOS !!!");
  else                 display.print("KHAN  CAP ");
  drawTTSBadge();
  display.drawLine(0, 22, 127, 22, SH110X_WHITE);
  display.setTextSize(1);
  display.setCursor(2, 25);
  display.print("HR:"); if (bpmDisplay > 0) display.print((int)round(bpmDisplay)); else display.print("--");
  display.print(" O2:"); if (spo2Display > 0) { display.print((int)round(spo2Display)); display.print("%"); } else display.print("--");
  display.setCursor(2, 34);
  float td = getBodyTempDisplay(); display.print("T:"); display.print(td, 1); display.print("C");
  display.setCursor(2, 43);
  if (!wifiOK) display.print("TG: Khong co WiFi");
  else {
    unsigned long next = lastTelegramSOS + TELEGRAM_SOS_COOLDOWN;
    if (now < next) { display.print("TG: "); display.print((next - now) / 1000); display.print("s"); }
    else            { display.print("TG: San sang - Giu BTN2"); }
  }
  display.drawLine(0, 51, 127, 51, SH110X_WHITE);
  display.setCursor(2, 54);
  if ((now / 400) % 2) display.print("GOI 115 | Giu BTN2=SOS");
  else                 display.print("BTN2=Ha tang | Hold=RS");
}

// =====================================================================
// UI: MOTION / SIM CONTROL
// =====================================================================
void showMotionScreen() {
  if (simulationMode) {
    display.drawRect(0, 0, 128, 64, SH110X_WHITE);
    display.setTextSize(1); display.setCursor(28, 2); display.print("SIM CONTROL");
    drawTTSBadge();
    display.drawLine(0, 11, 127, 11, SH110X_WHITE);
    display.setCursor(2, 14); display.print("Scenario: S"); display.print(simScenario);
    display.setCursor(2, 22);
    switch (simScenario) {
      case 0: display.print("Normal (BPM~75)");   break;
      case 1: display.print("Warning (BPM~108)"); break;
      case 2: display.print("Danger (BPM~125)");  break;
      case 3: display.print("Emerg (BPM~148)");   break;
    }
    display.setCursor(2, 32); display.print("BPM:"); display.print((int)simBPM);
    display.print("  O2:"); display.print((int)simSpO2); display.print("%");
    display.setCursor(2, 41); display.print("Temp:"); display.print(simTemp, 1); display.print("C");
    display.drawLine(0, 50, 127, 50, SH110X_WHITE);
    display.setCursor(2, 54); display.print("BTN2=Doi S | 3s=SOS"); return;
  }
  display.drawRect(0, 0, 128, 64, SH110X_WHITE);
  display.setTextSize(1); display.setCursor(25, 2); display.print("MOTION/FALL");
  drawTTSBadge();
  display.drawLine(0, 12, 127, 12, SH110X_WHITE);
  if (!mpuOK) { display.setCursor(22, 28); display.print("MPU6050 LOI"); return; }
  if (fallConfirmed) {
    display.setTextSize(2); display.setCursor(8, 18); display.print("TE NGA!");
    display.setTextSize(1);
    unsigned long rem = (fallAlertEnd > millis()) ? (fallAlertEnd - millis()) / 1000 : 0;
    display.setCursor(8, 40); display.print("Con: "); display.print(rem); display.print("s");
    display.setCursor(8, 52); display.print("BTN2=OK / Hold=SOS"); return;
  }
  display.setCursor(4, 16);
  if (millis() < fallCooldownEnd) { display.print("Cooldown:"); display.print((fallCooldownEnd - millis()) / 1000); display.print("s"); }
  else display.print("Dang giam sat...");
  display.setCursor(4, 26); display.print("M:"); display.print(motionLevel, 3);
  display.print(motionLevel > MOTION_THRESH_HR ? " DONG" : " YEN");
  int bL = constrain((int)(motionLevel * 200), 0, 60);
  display.drawRect(58, 16, 60, 6, SH110X_WHITE); display.fillRect(58, 16, bL, 6, SH110X_WHITE);
  display.setCursor(4, 36); display.print("Acc:"); display.print(lastMag, 2); display.print("g");
  display.setCursor(4, 46); display.print("State:");
  switch (fallState) {
    case FALL_IDLE:     display.print("IDLE"); break;
    case FALL_FREEFALL: display.print("FREEFALL"); break;
    case FALL_IMPACT:   display.print("IMPACT"); break;
    case FALL_POSTURE:  display.print("POSTURE"); break;
  }
  drawModeBadge();
}

// =====================================================================
// UI: ALERT STATUS
// =====================================================================
void showAlertScreen() {
  display.drawRect(0, 0, 128, 64, SH110X_WHITE);
  unsigned long now = millis();
  display.setTextSize(1); display.setCursor(28, 2);
  switch (alertLevel) {
    case ALERT_NORMAL:    display.print("TRANG THAI OK"); break;
    case ALERT_WARNING:   display.print("CANH BAO T.1"); break;
    case ALERT_DANGER:    display.print("NGUY HIEM T.2"); break;
    case ALERT_EMERGENCY: if ((now / 250) % 2) display.print("!!! KHAN CAP !!!"); break;
  }
  drawTTSBadge();
  display.drawLine(0, 10, 127, 10, SH110X_WHITE);
  display.setCursor(2, 14);
  display.print("BPM:"); if (bpmDisplay > 0) display.print((int)bpmDisplay); else display.print("--");
  display.setCursor(66, 14);
  display.print("O2:"); if (spo2Display > 0) { display.print((int)spo2Display); display.print("%"); } else display.print("--");
  display.setCursor(2, 23);
  display.print("T:"); display.print(getBodyTempDisplay(), 1); display.print("C");
  display.setCursor(66, 23);
  // Hiển thị trạng thái audio thay vì TTS
  display.print("WAV:");
  if (!littleFsOK)      display.print("NO FS");
  else if (ttsPlaying)  display.print("PLAY");
  else if (!ttsEnabled) display.print("OFF");
  else                  display.print("OK");
  display.drawLine(0, 31, 127, 31, SH110X_WHITE);
  display.setCursor(2, 34);
  String r = alertReason;
  if (r.length() > 42) r = r.substring(0, 39) + "...";
  if (r.length() > 21) { display.print(r.substring(0, 21)); display.setCursor(2, 43); display.print(r.substring(21)); }
  else display.print(r.length() > 0 ? r : "Tat ca binh thuong.");
  display.drawLine(0, 52, 127, 52, SH110X_WHITE);
  display.setCursor(2, 55);
  display.print("BTN2=XN | Hold 3s=SOS");
}
// =====================================================================
// FIREBASE — SIGN IN lấy idToken
// =====================================================================
bool firebaseSignIn() {
  if (!wifiOK) return false;

  WiFiClientSecure client;
  client.setInsecure();
  HTTPClient http;

  String url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=";
  url += FB_API_KEY;

  String payload = "{\"email\":\"";
  payload += FB_USER_EMAIL;
  payload += "\",\"password\":\"";
  payload += FB_USER_PASS;
  payload += "\",\"returnSecureToken\":true}";

  http.begin(client, url);
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(payload);

  if (code != 200) {
    Serial.printf("[FB] SignIn FAIL HTTP %d\n", code);
    http.end();
    return false;
  }

  String resp = http.getString();
  http.end();

  // Parse idToken — tìm "idToken":"..."
  int ti = resp.indexOf("\"idToken\"");

  if (ti < 0) {

    Serial.println("[FB] No token");

    Serial.println(resp);

    http.end();

    return false;
  }

  ti = resp.indexOf(":", ti);

  ti = resp.indexOf("\"", ti) + 1;

  int te = resp.indexOf("\"", ti);

  String token = resp.substring(ti, te);
  fbTokenExpiry = millis() + 3500000UL;

  token.toCharArray(fbIdToken, sizeof(fbIdToken));

  Serial.println("[FB] TOKEN OK");
  return true;
}

// =====================================================================
// FIREBASE — FETCH Firestore document
// =====================================================================
void fetchFirebaseData() {
  if (!wifiOK || !timeOK) return;

  if (strlen(fbIdToken) == 0 || millis() > fbTokenExpiry) {
    if (!firebaseSignIn()) return;
  }

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(15);

  String url = "https://firestore.googleapis.com/v1/projects/";
  url += FB_PROJECT_ID;
  url += "/databases/(default)/documents/";
  url += FB_COLLECTION;
  url += "/";
  url += FB_DOC_UID;
  // Chỉ lấy các field cần thiết — giảm response size ~80%
  url += "?mask.fieldPaths=expectedBirthDate&mask.fieldPaths=weight&mask.fieldPaths=heightCm";

  HTTPClient http;
  http.begin(client, url);
  http.addHeader("Authorization", String("Bearer ") + fbIdToken);
  http.setTimeout(12000);

  int code = http.GET();
  Serial.printf("[FB] Fetch HTTP %d\n", code);

  if (code != 200) {
    http.end();
    return;
  }

  // Đọc từng chunk thay vì getString()
  WiFiClient* stream = http.getStreamPtr();
  String resp = "";
  unsigned long t0 = millis();
  while (http.connected() && millis() - t0 < 8000) {
    if (stream->available()) {
      String chunk = stream->readString();
      resp += chunk;
      if (resp.length() > 2000) break; // giới hạn an toàn
    } else {
      delay(10);
    }
  }
  http.end();

  Serial.printf("[FB] resp len=%d\n", resp.length());
  if (resp.length() < 20) return;

  // Parse expectedBirthDate
  int idx = resp.indexOf("expectedBirthDate");
  if (idx >= 0) {
    int tsIdx = resp.indexOf("timestampValue", idx);
    if (tsIdx >= 0) {
      tsIdx += 16; // bỏ qua: timestampValue":"
      // tìm dấu " mở
      tsIdx = resp.indexOf('"', tsIdx);
      if (tsIdx >= 0) {
        tsIdx++; // bỏ dấu "
        int tsEnd = resp.indexOf('"', tsIdx);
        if (tsEnd > tsIdx) {
          String tsStr = resp.substring(tsIdx, tsEnd);
          Serial.println("[FB] TS=" + tsStr);

          int yr = tsStr.substring(0, 4).toInt();
          int mo = tsStr.substring(5, 7).toInt();
          int dy = tsStr.substring(8, 10).toInt();

          if (yr > 2020 && mo >= 1 && mo <= 12 && dy >= 1 && dy <= 31) {
            struct tm eddTm;
            memset(&eddTm, 0, sizeof(eddTm));
            eddTm.tm_year = yr - 1900;
            eddTm.tm_mon  = mo - 1;
            eddTm.tm_mday = dy;
            eddTm.tm_hour = 7; // UTC+7
            pregInfo.eddEpoch = mktime(&eddTm);
            snprintf(pregInfo.eddStr, sizeof(pregInfo.eddStr),
                     "%02d/%02d/%04d", dy, mo, yr);
            Serial.println("[FB] EDD=" + String(pregInfo.eddStr));
          }
        }
      }
    }
  }

  // Parse weight
  idx = resp.indexOf("\"weight\"");
  if (idx >= 0) {
    int vs = resp.indexOf("integerValue", idx);
    int vd = resp.indexOf("doubleValue",  idx);
    int vv = -1;
    if (vs >= 0 && (vd < 0 || vs < vd)) vv = vs + 14;
    else if (vd >= 0) vv = vd + 13;
    if (vv > 0) {
      int q1 = resp.indexOf('"', vv);
      int q2 = resp.indexOf('"', q1 + 1);
      if (q1 >= 0 && q2 > q1)
        pregInfo.weightKg = resp.substring(q1 + 1, q2).toFloat();
    }
  }

  // Parse heightCm
  idx = resp.indexOf("\"heightCm\"");
  if (idx >= 0) {
    int vs = resp.indexOf("integerValue", idx);
    if (vs >= 0) {
      int q1 = resp.indexOf('"', vs + 12);
      int q2 = resp.indexOf('"', q1 + 1);
      if (q1 >= 0 && q2 > q1)
        pregInfo.heightCm = resp.substring(q1 + 1, q2).toInt();
    }
  }

  pregInfo.valid = (pregInfo.eddEpoch > 0 && timeOK);
  if (pregInfo.valid) calcPregnancyWeek();
  Serial.printf("[FB] valid=%d week=%d days=%ld w=%.1f\n",
    pregInfo.valid, pregInfo.pregnancyWeek,
    pregInfo.daysLeft, pregInfo.weightKg);
}
// =====================================================================
// FIREBASE — UPLOAD HEALTH DATA
// =====================================================================
bool validHealthData(float bpm, float spo2, float temp) {

  bool bpmOK =
      (bpm >= 40 && bpm <= 180);

  bool spo2OK =
      (spo2 >= 70 && spo2 <= 100);

  bool tempOK =
      (temp >= 30 && temp <= 45);

  return bpmOK && spo2OK && tempOK;
}
void uploadHealthData() {
  if (!wifiOK) return;

  if (strlen(fbIdToken) == 0 || millis() > fbTokenExpiry) {
    if (!firebaseSignIn()) {
      Serial.println("[FB] Upload skip — no token");
      return;
    }
  }

  struct tm timeInfo;
  if (!getLocalTime(&timeInfo, 500)) {
    Serial.println("[FB] Upload skip — no NTP time");
    return;
  }

  time_t nowEpoch = mktime(&timeInfo);
  uint64_t tsMs   = (uint64_t)nowEpoch * 1000ULL;

  char readingKey[32];
  snprintf(readingKey, sizeof(readingKey),
           "%02d_%02d_%02d_%02d_%04d",
           timeInfo.tm_min, timeInfo.tm_hour,
           timeInfo.tm_mday, timeInfo.tm_mon + 1,
           timeInfo.tm_year + 1900);

  char timeStr[24];
  snprintf(timeStr, sizeof(timeStr),
           "%02d:%02d %02d/%02d/%04d",
           timeInfo.tm_hour, timeInfo.tm_min,
           timeInfo.tm_mday, timeInfo.tm_mon + 1,
           timeInfo.tm_year + 1900);

  const char* alertStr = "normal";
  switch (alertLevel) {
    case ALERT_WARNING:   alertStr = "warning";   break;
    case ALERT_DANGER:    alertStr = "danger";     break;
    case ALERT_EMERGENCY: alertStr = "emergency";  break;
    default: break;
  }

  char payload[320];
  snprintf(payload, sizeof(payload),
    "{\"alertLevel\":\"%s\","
    "\"heartRate\":%d,"
    "\"spo2\":%d,"
    "\"temperature\":%.1f,"
    "\"timestamp\":\"%s\","
    "\"timestampMs\":%llu}",
    alertStr,
    (int)round(bpmDisplay),
    (int)round(spo2Display),
    getBodyTempDisplay(),
    timeStr,
    (unsigned long long)tsMs
  );

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(15);

  // ── URL ĐÚNG: dùng firebasedatabase.app + ?auth= ──
  String baseUrl = "https://YOUR_PROJECT_ID-default-rtdb.asia-southeast1.firebasedatabase.app/devices/";
  baseUrl += String(DEVICE_ID);
  String authParam = String(".json?auth=") + String(fbIdToken);  // ← ?auth= thay vì header

  // ── 1. PUT /latest ──
  {
    String url = baseUrl + "/latest" + authParam;
    HTTPClient http;
    http.begin(client, url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(10000);
    int code = http.PUT(payload);
    Serial.printf("[FB] /latest PUT HTTP %d\n", code);
    if (code != 200) Serial.println("[FB] error: " + http.getString());
    http.end();
  }

  delay(200);

  // ── 2. POST /readings — dùng POST để auto-generate key ──
  {
    String url = baseUrl + "/readings" + authParam;
    HTTPClient http;
    http.begin(client, url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(10000);
    int code = http.POST(payload);  // POST tự tạo key unique
    Serial.printf("[FB] /readings POST HTTP %d\n", code);
    if (code != 200) Serial.println("[FB] error: " + http.getString());
    http.end();
  }

  // ── 3. PUT /alerts nếu đang cảnh báo ──
  if (alertLevel > ALERT_NORMAL) {
    delay(200);
    const char* alertMsg = "Canh bao suc khoe";
    float alertVal = bpmDisplay;
    switch (alertLevel) {
      case ALERT_WARNING:  alertMsg = "Canh bao cap 1"; break;
      case ALERT_DANGER:   alertMsg = "Nguy hiem cap 2"; break;
      case ALERT_EMERGENCY: alertMsg = "Khan cap!"; break;
      default: break;
    }

    char alertPayload[256];
    snprintf(alertPayload, sizeof(alertPayload),
      "{\"type\":\"%s\",\"message\":\"%s\",\"value\":%.1f,"
      "\"resolved\":false,\"timestamp\":\"%s\"}",
      alertStr, alertMsg, alertVal, timeStr
    );

    String url = baseUrl + "/alerts/" + String(readingKey) + authParam;
    HTTPClient http;
    http.begin(client, url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(10000);
    int code = http.PUT(alertPayload);
    Serial.printf("[FB] /alerts PUT HTTP %d\n", code);
    http.end();
  }
}
// =====================================================================
// TÍNH TUẦN THAI & SỐ NGÀY CÒN LẠI
// =====================================================================
void calcPregnancyWeek() {
  struct tm now_tm;
  if (!getLocalTime(&now_tm, 100)) return;
  time_t nowEpoch = mktime(&now_tm);

  long diffSec = (long)(pregInfo.eddEpoch - nowEpoch);
  pregInfo.daysLeft = diffSec / 86400L;

  // Thai kỳ 280 ngày (40 tuần) tính từ LMP
  // Tuần thai = 40 - (daysLeft / 7)
  long daysLeft40 = pregInfo.daysLeft;
  if (daysLeft40 < 0) daysLeft40 = 0;
  pregInfo.pregnancyWeek = 40 - (int)(daysLeft40 / 7);
  if (pregInfo.pregnancyWeek < 1)  pregInfo.pregnancyWeek = 1;
  if (pregInfo.pregnancyWeek > 42) pregInfo.pregnancyWeek = 42;
}

// =====================================================================
// UI: MÀN HÌNH ĐẾM NGƯỢC NGÀY DỰ SINH  (128×64 OLED)
// =====================================================================
// Layout (pixel):
//  Y= 0..10  : Header "DUE DATE" + icon tim
//  Y=11      : gạch ngang
//  Y=12..38  : Số ngày đếm ngược — setTextSize(3), font 7-seg style
//  Y=34..38  : EDD nhỏ "12/01/2027" góc phải
//  Y=39      : gạch ngang
//  Y=40..52  : Tuần thai | Cân nặng
//  Y=53      : gạch ngang
//  Y=54..63  : Thông báo nhỏ / trạng thái fetch
// ─────────────────────────────────────────────────────────────────────
void showDueDateScreen() {
  unsigned long now = millis();
  display.drawRect(0, 0, 128, 64, SH110X_WHITE);

  // ── Header ────────────────────────────────────────────────────────
  display.setTextSize(1);
  // Tim nhỏ bên trái header
  display.fillCircle(6,  4, 2, SH110X_WHITE);
  display.fillCircle(10, 4, 2, SH110X_WHITE);
  display.fillTriangle(4, 5, 12, 5, 8, 9, SH110X_WHITE);

  display.setCursor(28, 3);
  display.print("NGAY DU SINH");

  // Tim nhỏ bên phải header
  display.fillCircle(116, 4, 2, SH110X_WHITE);
  display.fillCircle(120, 4, 2, SH110X_WHITE);
  display.fillTriangle(114, 5, 122, 5, 118, 9, SH110X_WHITE);

  display.drawLine(1, 11, 126, 11, SH110X_WHITE);

  // ── Phần đếm ngược ────────────────────────────────────────────────
  if (!pregInfo.valid) {
    // Chưa có dữ liệu
    display.setTextSize(2);
    display.setCursor(14, 18);
    display.print("---");
    display.setTextSize(1);
    display.setCursor(2, 29);
    if (!wifiOK)         display.print("Can ket noi WiFi");
    else if (firebaseFetchPending) display.print("Dang tai du lieu...");
    else                 display.print("Nhan BTN1 de tai");
  } else {
    // Cập nhật daysLeft theo thời gian thực
    calcPregnancyWeek();

    long dl = pregInfo.daysLeft;

    // Hiển thị số ngày to — TextSize(3) = 18px cao, mỗi ký tự ~18px rộng
    // 3 chữ số = 54px, 4 chữ số = 72px → luôn đủ chỗ
    display.setTextSize(2);
    char daysStr[6];
    if (dl < 0)       snprintf(daysStr, sizeof(daysStr), "000");
    else if (dl < 1000) snprintf(daysStr, sizeof(daysStr), "%03ld", dl);
    else              snprintf(daysStr, sizeof(daysStr), "%4ld", dl);

    // Căn giữa số ngày (bỏ chỗ cho EDD nhỏ bên phải)
    int numW = strlen(daysStr) * 18;  // TextSize(3) → ~18px/char
    int cx = (128 - 40 - numW) / 2;  // 40px dành cho cột EDD bên phải
    if (cx < 2) cx = 2;
    display.setCursor(cx-3, 15);
    display.print(daysStr);

    // Nhãn "DAYS" nhỏ bên dưới số
    display.setTextSize(1);
    display.setCursor(cx+10, 30);
    display.print("NGAY");

    // EDD nhỏ góc phải (căn lề phải từ x=88)
    display.setTextSize(1);
    display.setCursor(63, 28);
    display.print(pregInfo.eddStr);  // "12/01/2027"
  }

  display.drawLine(1, 40, 126, 40, SH110X_WHITE);

  // ── Thông tin thai kỳ (hàng dưới) ────────────────────────────────
  // Chia 2 cột: TUẦN THAI | CÂN NẶNG
  // Dọc ngăn cách ở x=64
  display.drawLine(64, 40, 64, 53, SH110X_WHITE);

  // Cột trái — TUẦN THAI
  display.setTextSize(1);
  display.setCursor(4, 42);
  display.print("WEEK");
  display.setTextSize(2);
  display.setCursor(30, 45);
  if (pregInfo.valid) {
    display.print(pregInfo.pregnancyWeek);
  } else {
    display.print("--");
  }

  // Cột phải — CÂN NẶNG
  display.setTextSize(1);
  display.setCursor(68, 42);
  display.print("WEIGHT");
  display.setTextSize(1);
  display.setCursor(68, 51);
  if (pregInfo.valid && pregInfo.weightKg > 0) {
    display.print((int)pregInfo.weightKg);
    display.setTextSize(1);
    display.print("kg");
  } else {
    display.print("--");
  }

  // display.drawLine(1, 61, 126, 61, SH110X_WHITE);

  // ── Footer: trạng thái ────────────────────────────────────────────
  display.setTextSize(1);
  display.setCursor(2, 62);  // Lưu ý: Y=62 sát viền dưới, font nhỏ 6px OK
  // Không có chỗ hiển thị nhiều ở đây vì đã chiếm hết không gian
  // Dùng khu vực này làm nháy nhẹ để biết đang live
  if ((now / 1000) % 2) {
    display.setCursor(95, 65);
    display.print("*");
  }

  drawModeBadge();
  drawTTSBadge();
}

// =====================================================================
// SERIAL TEST — cập nhật cho v5.4
// =====================================================================
void handleSerialTest() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n'); cmd.trim();

  if      (cmd == "test1")  activateAlert(ALERT_WARNING, "TEST T1:BPM hoi cao", 108.0f, 94.5f, 37.6f);
  else if (cmd == "test2")  activateAlert(ALERT_DANGER, "TEST T2:SpO2 thap", 125.0f, 92.0f, 38.2f);
  else if (cmd == "test3")  activateAlert(ALERT_EMERGENCY, "TEST T3:KHAN CAP!", 145.0f, 89.0f, 39.5f);
  else if (cmd == "reset")  {
    alertLevel = ALERT_NORMAL; motorOff(); alertReason = "";
    ttsState = TTS_IDLE; breathGuideActive = false;
    ttsStop(); playClip(CLIP_NORMAL);
  }
  else if (cmd == "sim")    toggleSimulationMode();
  else if (cmd == "s0")     { simScenario = 0; playClip(CLIP_NORMAL); }
  else if (cmd == "s1")     { simScenario = 1; activateAlert(ALERT_WARNING, "[SIM] S1", 108, 94.5f, 37.6f); }
  else if (cmd == "s2")     { simScenario = 2; activateAlert(ALERT_DANGER, "[SIM] S2", 125, 91.5f, 38.3f); }
  else if (cmd == "s3")     { simScenario = 3; activateAlert(ALERT_EMERGENCY, "[SIM] S3", 148, 88, 39.5f); }
  else if (cmd == "fall")   { startFallAlert(); }
  else if (cmd == "sos")    { pendingSOS = true; }
  else if (cmd == "ttson")  { ttsEnabled = true;  Serial.println("[AUDIO] ON"); }
  else if (cmd == "ttsoff") { ttsEnabled = false; ttsStop(); Serial.println("[AUDIO] OFF"); }
  else if (cmd == "vol+") {
    ttsVolume = min(1.0f, ttsVolume + 0.1f);
    if (i2sOut) i2sOut->SetGain(ttsVolume);
    Serial.printf("[AUDIO] Vol: %.1f\n", ttsVolume);
  }
  else if (cmd == "vol-") {
    ttsVolume = max(0.0f, ttsVolume - 0.1f);
    if (i2sOut) i2sOut->SetGain(ttsVolume);
    Serial.printf("[AUDIO] Vol: %.1f\n", ttsVolume);
  }
  // Test từng clip theo số: clip 1, clip 2, ...
  else if (cmd.startsWith("clip ")) {
    int n = cmd.substring(5).toInt();
    if (n >= 1 && n < (int)CLIP_COUNT) {
      AudioClip c = (AudioClip)n;
      Serial.printf("[AUDIO] Test clip %d: %s\n", n, clipFilename(c));
      playClip(c);
    } else Serial.println("clip 1..22");
  }
  else if (cmd == "breath") {
    startBreathingAssist(); ttsState = TTS_BREATHING;
    playClip(CLIP_BREATH_IN);
  }
  // List files trong LittleFS
  else if (cmd == "lsfs") {
    Serial.println("[FS] LittleFS files:");
    File root = LittleFS.open("/");
    File f = root.openNextFile();
    while (f) {
      Serial.printf("  %s  %u bytes\n", f.name(), f.size());
      f = root.openNextFile();
    }
    size_t used = LittleFS.usedBytes(), total = LittleFS.totalBytes();
    Serial.printf("[FS] Used: %u / %u bytes (%.1f%%)\n", used, total, 100.0f * used / total);
  }
  else if (cmd == "info")
    Serial.printf("[INFO] v5.4 Mode=%s Alert=%d BPM=%.1f SpO2=%.1f Temp=%.1f WAV=%s FS=%s\n",
      simulationMode ? "SIM" : "REAL", (int)alertLevel,
      bpmDisplay, spo2Display, getBodyTempDisplay(),
      ttsPlaying ? "PLAY" : (ttsEnabled ? "READY" : "OFF"),
      littleFsOK ? "OK" : "FAIL");
  else if (cmd == "fb")     { firebaseFetchPending = true; Serial.println("[FB] Fetch queued"); }
  else if (cmd == "fbinfo") {
    Serial.printf("[FB] valid=%d daysLeft=%ld week=%d weight=%.1f height=%d EDD=%s\n",
      pregInfo.valid, pregInfo.daysLeft, pregInfo.pregnancyWeek,
      pregInfo.weightKg, pregInfo.heightCm, pregInfo.eddStr);
  }
  else if (cmd == "help") {
    Serial.println("Commands v5.4:");
    Serial.println("  test1/2/3  sim  s0-s3  fall  sos  reset");
    Serial.println("  breath  clip <1-22>  lsfs");
    Serial.println("  ttson  ttsoff  vol+  vol-  info");
    Serial.println("  fb → Fetch Firebase ngay");
    Serial.println("  fbinfo → In thông tin thai kỳ");
  }
  else if (cmd == "falldemo") {
  demoFallMode = !demoFallMode;
  if (demoFallMode) {
    fallImpactG  = 1.4f; fallTiltDeg = 30.0f; fallStillMs = 1500;
    Serial.println("[FALL] DEMO mode: ngưỡng thấp");
  } else {
    fallImpactG  = 2.5f; fallTiltDeg = 55.0f; fallStillMs = 3000;
    Serial.println("[FALL] REAL mode: ngưỡng thực tế");
  }
}
}

// =====================================================================
// SETUP
// =====================================================================
void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN); Wire.setClock(400000);
  pinMode(BTN1_PIN, INPUT_PULLUP);
  pinMode(BTN2_PIN, INPUT_PULLUP);
  pinMode(BTN3_PIN, INPUT_PULLUP);
  pinMode(MPU_INT_PIN, INPUT_PULLUP);
  pinMode(MOTOR_PIN, OUTPUT); analogWrite(MOTOR_PIN, 0);

  telegramConfigured = (
    String(TELEGRAM_BOT_TOKEN) != "YOUR_BOT_TOKEN_HERE" &&
    String(TELEGRAM_CHAT_ID)   != "YOUR_CHAT_ID_HERE"
  );

  // ── Khởi tạo I2S audio output TRƯỚC khi mount FS ──────────────────
  initAudioOutput();

  // ── Khởi tạo LittleFS ─────────────────────────────────────────────
  littleFsOK = LittleFS.begin(false);  // false = không format nếu fail
  if (!littleFsOK) {
    Serial.println("[FS] LittleFS FAIL — thử format...");
    littleFsOK = LittleFS.begin(true); // true = format nếu cần
    if (littleFsOK) Serial.println("[FS] Formatted OK — cần upload audio!");
    else            Serial.println("[FS] FAIL hoàn toàn!");
  } else {
    Serial.printf("[FS] OK — %u/%u bytes used\n", LittleFS.usedBytes(), LittleFS.totalBytes());
  }

  // ── OLED ──────────────────────────────────────────────────────────
  display.begin(0x3C, true);
  display.setTextColor(SH110X_WHITE);
  display.clearDisplay(); display.setTextSize(1);
  display.setCursor(10, 10); display.println("PREGCARE v5.4");
  display.setCursor(10, 20); display.println("WAV Local Audio");
  display.setCursor(10, 30); display.print("FS: ");
  display.println(littleFsOK ? "OK" : "FAIL");
  display.setCursor(10, 40); display.println("Starting...");
  display.display();

  // ── WiFi (cho NTP + Telegram, không cần cho audio) ────────────────
  connectWiFiBlocking(20000UL);
  if (wifiOK) initNTP();

  // ── Cảm biến ──────────────────────────────────────────────────────
  mlxOK = false;
  for (int i = 0; i < 5; i++) {
    if (mlx.begin()) {
      float obj = mlx.readObjectTempC(), amb = mlx.readAmbientTempC();
      if (obj > 0 && obj < 100 && amb > -20 && amb < 80) {
        bodySmooth = obj; roomSmooth = amb; mlxOK = true; break;
      }
    }
    delay(120);
  }

  maxOK = particleSensor.begin(Wire, I2C_SPEED_FAST);
  if (maxOK) {
    particleSensor.setup(0x7F, 8, 2, 100, 411, 4096);
    particleSensor.setPulseAmplitudeRed(ledPower);
    particleSensor.setPulseAmplitudeIR(ledPower);
    particleSensor.setPulseAmplitudeGreen(0);
  }

  mpuOK = mpu.begin();
  if (mpuOK) {
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_1000_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  }

  resetHeart(); alertLevel = ALERT_NORMAL;

  // Motor rung ngắn báo hiệu khởi động xong
  motorSet(true, MOTOR_LEVEL_MEDIUM); delay(100);
  motorSet(false); delay(100);
  motorSet(true, MOTOR_LEVEL_MEDIUM); delay(100);
  motorSet(false);

  // ── Status screen ─────────────────────────────────────────────────
  display.clearDisplay(); display.setTextSize(1);
  display.setCursor(0, 0);  display.print("WiFi:"); display.println(wifiOK ? "OK" : "WAIT");
  display.setCursor(0, 9);  display.print("Time:"); display.println(timeOK ? "OK" : "WAIT");
  display.setCursor(0, 18); display.print("MLX :"); display.println(mlxOK ? "OK" : "FAIL");
  display.setCursor(0, 27); display.print("MAX :"); display.println(maxOK ? "OK" : "FAIL");
  display.setCursor(0, 36); display.print("MPU :"); display.println(mpuOK ? "OK" : "FAIL");
  display.setCursor(0, 45); display.print("FS  :"); display.println(littleFsOK ? "OK" : "FAIL");
  display.setCursor(0, 54); display.print("WAV :"); display.println(littleFsOK ? "READY" : "NO FILES");
  display.display(); delay(2000);

  // Phát clip khởi động nếu FS OK
  if (littleFsOK) {
    playClip(CLIP_READY);
  }
  // if (wifiOK && timeOK) {
  //     Serial.println("[FB] Initial fetch...");
  //     fetchFirebaseData();
  //     lastFirebaseFetch = millis(); // đặt lại để không fetch lại ngay trong loop
  //   }
}



// =====================================================================
// LOOP
// =====================================================================
void loop() {
  updateTTSAudio();        // pump WAV audio — luôn đầu tiên
  // Sau khi breath_done.wav phát xong
  if (
      waitingBreathDoneRecovery &&
      !ttsPlaying &&
      !ttsQueued
  ) {

      waitingBreathDoneRecovery = false;

      // giả lập hồi phục ổn định
      bpmDisplay  = 82;
      spo2Display = 98;
      bodySmooth  = 36.6f - BODY_TEMP_OFFSET;

      // reset alert
      alertLevel = ALERT_NORMAL;
      alertReason = "";

      // tắt breathing
      breathGuideActive = false;

      // tắt motor
      motorOff();

      // reset state
      vibeMode = VIBE_OFF;
      ttsState = TTS_IDLE;

      // quay về màn hình đo
      screenMode = 2;

      // phát thông báo bình thường
      playClip(CLIP_NORMAL);

      Serial.println("[BREATH] Recovery complete");
  }
  maintainTime();
  handleButtons();
  if (!simulationMode) updateMPU();
  updateMotor();
  updateFallSOSMotor();
  updateTemperatureSmooth();
  updateSimulation();
  updateTTSStateMachine();
  handleSerialTest();
  // ── Fetch Firebase định kỳ hoặc khi pending ─────────────────────
  // if (wifiOK) {
  //   if (firebaseFetchPending ||
  //       (lastFirebaseFetch != 0 && millis() - lastFirebaseFetch > FIREBASE_FETCH_INTERVAL)) {
  //     lastFirebaseFetch = millis();
  //     firebaseFetchPending = false;
  //     fetchFirebaseData();
  //   }
  // }
  // =========================================================
  // Upload health data mỗi 1 phút
  // =========================================================
  if (millis() - lastHealthUpload >= HEALTH_UPLOAD_INTERVAL) {
    lastHealthUpload = millis();
    Serial.printf("[FB] Trigger upload: bpm=%.1f spo2=%.1f wifi=%d token=%s\n",
      bpmDisplay, spo2Display, wifiOK, strlen(fbIdToken) > 0 ? "OK" : "EMPTY");
    if (bpmDisplay > 30 && spo2Display > 70) {
      uploadHealthData();
    } else {
      Serial.println("[FB] Skip — invalid data");
    }
  }
  if (pendingSOS) {
    pendingSOS = false;
    // Không reset lastTelegramSOS ở đây nữa (đã reset trong handler)
    String reason = (alertReason.length() > 0) ? alertReason : "Nguoi dung gui SOS";
    if (simulationMode) reason = "[SIM] " + reason;
    bool sent = sendTelegramSOS(reason);
    // Chỉ phát SOS_FAIL nếu thực sự fail gửi, không phải do cooldown
    if (sent) {
      vibeMode = VIBE_STRONG; vibePhaseEnd = millis() + 1000UL;
      playClip(CLIP_SOS_SENT);
    } else {
      // Kiểm tra: nếu tTelegramSOS vừa set (< 2s) thì đã gửi thành công từ activateAlert
      // → không phát fail
      if (millis() - lastTelegramSOS > 2000UL) {
        playClip(CLIP_SOS_FAIL);
      }
    }
  }

  if (screenMode != 2 && !simulationMode) {
    float td = mlxOK ? getBodyTempDisplay() : 0;
    updateAlertSystem(bpmDisplay, spo2Display, td, fallConfirmed);
  }

  if (alertAnnounceActive) {
    showAlertAnnounce();
    if (millis() - alertAnnounceStart > ALERT_ANNOUNCE_MS) {
      alertAnnounceActive = false;
      switch (alertLevel) {
        case ALERT_WARNING:
        case ALERT_DANGER:    screenMode = 2; break;
        case ALERT_EMERGENCY: screenMode = 4; break;
        default: break;
      }
    }
    return;
  }

  display.clearDisplay();
  switch (screenMode) {
    case 0: showClockScreen(); break;
    case 1: showTempScreen();  break;
    case 2:
      if (simulationMode)                     showHeartScreenSim();
      else if (alertLevel == ALERT_WARNING)   showWarningScenario();
      else if (alertLevel == ALERT_DANGER)    showDangerScenario();
      else if (alertLevel == ALERT_EMERGENCY) showEmergencyScenario();
      else                                    showHeartScreenReal();
      break;
    case 3: showMotionScreen(); break;
    case 4: showAlertScreen();  break;
    case 5: showDueDateScreen(); break;
  }
  display.display();
  delay(20);
}

/*
╔══════════════════════════════════════════════════════════════╗
║  PREGCARE v5.4 — WAV LOCAL (LittleFS)                       ║
╠══════════════════════════════════════════════════════════════╣
║  THAY ĐỔI CHÍNH:                                            ║
║  • Xóa Google TTS realtime hoàn toàn                        ║
║  • AudioGeneratorWAV + AudioFileSourceLittleFS               ║
║  • playClip(AudioClip) thay ttsSpeak(String)                ║
║  • playClipQueued() cho clip không ưu tiên                  ║
║  • LittleFS.begin() trong setup()                           ║
║  • littleFsOK flag — audio tắt im nếu FS fail               ║
║  • WiFi chỉ dùng NTP + Telegram (không cần cho audio)       ║
║                                                              ║
║  PARTITION SCHEME (Arduino IDE):                            ║
║  Tools → Partition Scheme →                                 ║
║  "No OTA (2MB APP/2MB SPIFFS)"                              ║
║                                                              ║
║  UPLOAD AUDIO:                                              ║
║  1. Tạo thư mục data/ trong thư mục sketch                  ║
║  2. Copy 22 file WAV vào data/                              ║
║  3. Tools → ESP32 LittleFS Data Upload                      ║
║                                                              ║
║  SERIAL COMMANDS:                                            ║
║   test1/2/3  sim  s0-s3  fall  sos  reset                   ║
║   breath  clip <1-22>  lsfs  ttson  ttsoff  vol+  vol-      ║
║                                                              ║
║  BTN1: Ngắn=màn / 3s=SIM / 5s=SOS                          ║
║  BTN2 (REAL): 1x=xác nhận / 2x=Alert / 3s=SOS              ║
║  BTN2 (SIM):  1x=đổi Scenario / 3s=SOS                     ║
╚══════════════════════════════════════════════════════════════╝
*/




