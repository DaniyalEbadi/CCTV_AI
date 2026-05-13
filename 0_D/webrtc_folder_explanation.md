اول یک خط مرزی خیلی مهم

🧠
ICE = شبکه (IP / Port / NAT / Route)
signaling = قابلیت‌ها و قرارداد (SDP)

ICE می‌گه:

«از کجا می‌تونم بیام؟»

signaling می‌گه:

«اگه اومدم، قراره چی رد و بدل کنیم؟»

ICE دقیقاً چیارو چک می‌کنه؟ (یادآوری سریع)

ICE candidate شامل ایناست:

candidate:1 1 UDP 2130706431 192.168.1.10 54032 typ host


یعنی:

IP

Port

Protocol (UDP/TCP)

نوع (host / srflx / relay)

priority

ICE:

این مسیرها رو تست می‌کنه

RTT می‌گیره

بهترین مسیر رو انتخاب می‌کنه

❗ ICE اصلاً کاری به codec، video، audio نداره

حالا signaling دقیقاً چیارو «چک / اعلام» می‌کنه؟

signaling چک نمی‌کنه
❗ اعلام می‌کنه

همه‌چی توی SDP اتفاق می‌افته.

SDP چیه؟

📄 Session Description Protocol

یه متن ساده‌ست ولی خیلی پرجزئیات:

v=0
o=- 46117326 2 IN IP4 127.0.0.1
s=-
t=0 0


SDP یعنی:

«این جلسه قراره این شکلی باشه»

Offer یعنی «من چی بلدم؟» دقیقاً یعنی چی؟

Offer = پیشنهاد قرارداد

مثال واقعی 👇

m=video 9 UDP/TLS/RTP/SAVPF 96 102
a=rtpmap:96 H264/90000
a=rtpmap:102 VP8/90000
a=fmtp:96 profile-level-id=42e01f
a=recvonly


یعنی:

من video دارم

این codecها رو بلدم:

H264

VP8

H264 رو با این profile بلدم

فقط می‌خوام دریافت کنم (recvonly)

📌 اینا «قابلیت» هستن، نه تصمیم نهایی

Offer شامل این اطلاعاته:
🎥 Media

video / audio / data

🎧 Codec

H264

VP8

Opus

PCMU

…

🔁 Direction

sendrecv

sendonly

recvonly

inactive

🧩 Payload Type
96 → H264

⏱️ Timing / clock
90000 Hz

🔐 Security

DTLS fingerprint

SRTP

🧠 Extensions

RTX

FEC

simulcast

bandwidth hints

Answer یعنی چی؟

Answer = قبول + فیلتر

Answer می‌گه:

«این چیزایی که گفتی، ایناشو قبول دارم»

مثال 👇

Offer گفت:

H264, VP8


Answer:

m=video 9 UDP/TLS/RTP/SAVPF 96
a=rtpmap:96 H264/90000


یعنی:
❌ VP8
✅ فقط H264

Answer چه کارهایی می‌کنه؟

codecهایی که بلد نیست حذف می‌کنه

direction رو محدود می‌کنه

extensionهایی که پشتیبانی نمی‌کنه حذف می‌کنه

bitrate و profile رو فیکس می‌کنه

📌 Answer تصمیم نهاییه

یه مثال واقعی مذاکره
Offer:

من:

video

H264 / VP8

sendrecv

Answer:

تو:

video

فقط H264

recvonly

📌 نتیجه:

ویدیو

فقط H264

من می‌فرستم، تو می‌گیری

signaling پس چی «چک» می‌کنه؟

signaling:

SDP رو رد و بدل می‌کنه

consistency رو حفظ می‌کنه

تضمین می‌کنه Offer قبل Answer برسه

ICE candidateها رو تحویل می‌ده

❌ signaling:

NAT رو چک نمی‌کنه

پورت تست نمی‌کنه

packet نمی‌فرسته

یه نمودار ذهنی ساده
SDP (Offer/Answer)
  ↓
قرارداد رسانه‌ای
  ↓
ICE Candidate
  ↓
مسیر شبکه
  ↓
RTP Flow (video/audio)

تفاوت خیلی دقیق در یک جمله

🧠
ICE می‌گه «از کجا وصل شیم»
SDP (signaling) می‌گه «وقتی وصل شدیم، چی رد و بدل کنیم»