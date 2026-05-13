حالا که ICE / SDP / signaling رو دقیق فهمیدی، وقتشه client.go رو مهندسی‌وار و دقیق باز کنیم.
اینجا دیگه حرف مبتدی نیست؛ دقیقاً می‌گیم این فایل مغز WebRTC تو go2rtc چطوری کار می‌کنه.

نقش client.go در یک جمله

🧠
client.go = Router + Orchestrator کل WebRTC Clientها

نه خودش WebRTC رو اختراع می‌کنه
نه SDP رو دست‌کاری می‌کنه
نه ICE رو پیاده‌سازی می‌کنه

بلکه:

«ببین URL چیه → بفهم طرف مقابلم کیه → client مناسب رو صدا بزن»

ساختار کلی فایل

فایل ۳ تا لایه‌ی منطقی داره:

1️⃣ streamsHandler  ← تصمیم‌گیر اصلی
2️⃣ Clientها        ← پیاده‌سازی signaling
3️⃣ ابزار مشترک     ← Dial (auth)

1️⃣ streamsHandler (مهم‌ترین قسمت)

این تابع دروازه‌ی ورود همه‌ی WebRTCهاست.

func streamsHandler(rawURL string) (core.Producer, error)

ورودی:
webrtc:...

خروجی:
core.Producer


📌 Producer یعنی:

«یه منبع زنده‌ی media که go2rtc می‌تونه بخونه»

قدم 1: جدا کردن fragment (#)
webrtc:http://ip/path#format=creality#client_id=abc


اینا از URL درمیاد:

format
client_id
ice_servers


📌 fragment فقط برای انتخاب client استفاده می‌شه
نه توی HTTP / WS واقعی

قدم 2: حذف prefix
rawURL = rawURL[7:] // remove webrtc:


📌 webrtc: فقط یه namespace داخلیه

قدم 3: تشخیص scheme
ws / wss
http / https


اینجا یه تصمیم خیلی مهم گرفته می‌شه 👇

اگر scheme = WebSocket
webrtc:ws://...


📌 یعنی:

«signaling زنده داریم»

routing:
switch format {
  case kinesis     → kinesisClient
  case openipc     → openIPCClient
  case switchbot   → switchbotClient
  default          → go2rtcClient
}


🔹 چرا؟

Kinesis / Wyze → signaling اختصاصی

OpenIPC → firmware خاص

default → go2rtc ↔ go2rtc

اگر scheme = HTTP
webrtc:http://...


📌 یعنی:

«signaling درخواست/پاسخ»

routing:
switch format {
  case milestone → milestoneClient
  case wyze      → wyzeClient
  case creality  → crealityClient
  default        → whepClient
}


🔹 پیش‌فرض = WHEP استاندارد

نتیجه‌ی streamsHandler

هر چی باشه، آخرش:

return someClient(...)


📌 streamsHandler:

WebRTC بلد نیست

SDP بلد نیست

ICE بلد نیست

فقط تصمیم می‌گیره کی کار رو انجام بده

2️⃣ go2rtcClient (WebRTC کلاسیک با WS)

این یکی رو دقیق بررسی کنیم چون مرجع بقیه‌ست.

مرحله 1: WebSocket signaling
conn, _, err := Dial(url)


📌 این فقط برای:

Offer

Answer

ICE candidate

❌ ویدیو از این رد نمی‌شه

مرحله 2: PeerConnection
pc, err := PeerConnection(true)


true یعنی:

ما initiator هستیم → Offer می‌فرستیم

مرحله 3: webrtc.Conn wrapper
prod := webrtc.NewConn(pc)


این wrapper:

SDP می‌سازه

candidateها رو هندل می‌کنه

state رو مانیتور می‌کنه

مرحله 4: Listen (قلب ICE)
prod.Listen(func(msg any) { ... })


اینجا دو چیز میاد:

🧊 ICECandidate
webrtc/candidate


→ می‌فرستیمش سمت remote از طریق WebSocket

🔌 PeerConnectionState
Connected / Failed / Closed


→ تعیین موفقیت اتصال

مرحله 5: ساخت Offer
CreateOffer(medias)


medias:

video recvonly
audio recvonly
audio sendonly


📌 این یعنی:

تصویر و صدا می‌گیریم

صدا هم می‌فرستیم (mic)

مرحله 6: Offer → WS
webrtc/offer

مرحله 7: Answer ← WS
webrtc/answer

prod.SetAnswer(answer)


📌 اینجا SDP contract نهایی می‌شه

مرحله 8: ICE از remote
AddCandidate(...)

مرحله 9: wait
connState.Wait()


تا:

Connected

یا Error

3️⃣ whepClient (HTTP استاندارد)

فرقش با go2rtcClient:

مورد	go2rtc	WHEP
signaling	WebSocket	HTTP
ICE	trickle	داخل Offer
round-trip	چندتا	یکی
firewall	سخت‌تر	راحت‌تر

📌 WHEP = ساده ولی کم‌انعطاف

4️⃣ Dial (احراز هویت WS)
ws://user:pass@host


→ تبدیل به:

Authorization: Basic base64(user:pass)


📌 تمیز و استاندارد

جمع‌بندی نهایی (خیلی مهم)

🧠
client.go:

تصمیم می‌گیره با کی حرف بزنیم

انتخاب می‌کنه چطور حرف بزنیم

اجرای واقعی رو می‌سپره به client تخصصی

اگر این فایل نباشه:

❌ هر دستگاه یه entry جدا می‌خواست
❌ chaos مطلق