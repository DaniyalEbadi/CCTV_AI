# راهنمای کامل برای فرانت‌اند دولوپر (Frontend Developer)

## 📌 **چیکار کنم؟ قدم به قدم**

### **قدم ۱: اول OpenAPI رو بفهم (مثل نقشه ساختمون)**

**OpenAPI.yaml اینا رو بهت می‌ده:**

```
📋 لیست تمام کارهایی که می‌تونی با سرور انجام بدی:
├── 📹 مدیریت دوربین‌ها
│   ├── GET /api/streams          ← ببین چه دوربین‌هایی داریم
│   ├── PUT /api/streams          ← دوربین جدید اضافه کن
│   └── DELETE /api/streams       ← دوربین رو پاک کن
├── 🎬 پخش ویدیو
│   ├── POST /api/webrtc         ← ویدیوی زنده (WebRTC)
│   ├── GET /api/stream.mp4      ← دانلود ویدیو
│   └── GET /api/stream.m3u8     ← پخش برای موبایل
├── 📸 عکس
│   ├── GET /api/frame.jpeg      ← عکس بگیر
│   └── GET /api/frame.mp4       ← کلیپ کوتاه
├── 🔍 پیدا کردن دوربین
│   ├── GET /api/onvif           ← دوربین‌های شبکه
│   └── GET /api/homekit         ← دوربین‌های اپل
├── 🎮 کنترل دوربین (PTZ)
│   └── POST /onvif/             ← حرکت دوربین (چپ/راست/زوم)
└── ⚙️ تنظیمات
    ├── GET /api                 ← اطلاعات برنامه
    └── GET/POST /api/config     ← تنظیمات رو بخون/بنویس
```

**مثلاً:**
```javascript
// می‌خوای لیست دوربین‌ها رو بگیری:
// از OpenAPI می‌فهمی: GET /api/streams

// می‌خوای عکس بگیر:
// از OpenAPI می‌فهمی: GET /api/frame.jpeg?src=camera1

// می‌خوای دوربین رو حرکت بدی:
// از OpenAPI می‌فهمی: POST /onvif/ (با XML خاص)
```

### **قدم ۲: برای استفاده راحت، Client بساز**

**از OpenAPI یه کتابخونه JS درست کن:**
```bash
# توی ترمینال بزن:
npx @openapitools/openapi-generator-cli generate \
  -i openapi.yaml \
  -g typescript-axios \
  -o ./src/api

# یا با Swagger:
npm install swagger-client
```

**حالا راحت می‌تونی اینطوری کد بزنی:**
```typescript
import { DefaultApi } from './src/api';

const api = new DefaultApi();

// همه چیز auto-complete داره!
const streams = await api.getStreams();
const snapshot = await api.getFrameJpeg('camera1');
const info = await api.getApi();
```

### **قدم ۳: video-rtc.js رو فقط برای پخش ویدیو استفاده کن**

**video-rtc.js فقط یه کار بلده: ویدیوی زنده نشون بده**

```html
<!-- اول فایل رو اضافه کن -->
<script src="video-rtc.js"></script>

<!-- توی HTML -->
<video id="camera1" autoplay muted controls></video>

<!-- توی JavaScript -->
<script>
// این خیلی ساده‌ست:
const videoElement = document.getElementById('camera1');
const player = new VideoRTC({
  video: videoElement,  // کدوم video تگ
  url: 'http://localhost:1984/api/webrtc?src=camera1'  // آدرس دوربین
});

// تموم! ویدیو شروع می‌شه
// خودش همه کارا رو می‌کنه: وصل شدن، ری‌کانکت، خطاها
</script>
```

### **قدم ۴: یه برنامه کامل Electron بساز**

**ساختار پوشه‌ها:**
```
پروژه-من/
├── 📦 package.json
├── 🏗️ main.js                    # قسمت اصلی Electron
├── 🌉 preload.js                 # پل امن بین Electron و صفحه
├── 📁 src/
│   ├── 🎬 VideoPlayer.js         # از video-rtc.js استفاده می‌کنه
│   ├── 📋 CameraList.js          # لیست دوربین‌ها (با OpenAPI)
│   ├── 🎮 PTZControls.js         # کنترل‌های حرکت دوربین
│   └── ⚙️ Settings.js            # تنظیمات
├── 📁 public/
│   ├── 🏠 index.html             # صفحه اصلی
│   └── 📹 video-rtc.js          # فایل پخش ویدیو
└── 📄 openapi.yaml               # نقشه API
```

### **قدم ۵: برای Electron، Main و Renderer رو جدا کن**

**۱. main.js (قسمت اصلی Electron - مثل Backend):**
```javascript
const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const axios = require('axios');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'), // مهم!
      nodeIntegration: false, // امنیت
      contextIsolation: true  // امنیت
    }
  });
  
  mainWindow.loadFile('public/index.html');
}

// اینجا با go2rtc صحبت می‌کنیم
ipcMain.handle('get-cameras', async () => {
  const response = await axios.get('http://localhost:1984/api/streams');
  return response.data;
});

ipcMain.handle('take-snapshot', async (event, cameraName) => {
  const response = await axios.get(
    `http://localhost:1984/api/frame.jpeg?src=${cameraName}`,
    { responseType: 'arraybuffer' }
  );
  return Buffer.from(response.data); // عکس رو برمی‌گردونیم
});

app.whenReady().then(createWindow);
```

**۲. preload.js (پل امن):**
```javascript
const { contextBridge, ipcRenderer } = require('electron');

// این توابع رو به صفحه می‌دیم
contextBridge.exposeInMainWorld('electronAPI', {
  // دوربین‌ها رو بگیر
  getCameras: () => ipcRenderer.invoke('get-cameras'),
  
  // عکس بگیر
  takeSnapshot: (cameraName) => ipcRenderer.invoke('take-snapshot', cameraName),
  
  // دوربین رو حرکت بده
  moveCamera: (cameraName, pan, tilt) => 
    ipcRenderer.invoke('move-camera', cameraName, pan, tilt),
  
  // ضبط کن
  startRecording: (cameraName, seconds) => 
    ipcRenderer.invoke('start-recording', cameraName, seconds)
});
```

**۳. صفحه HTML/JS (رندرر - مثل Frontend معمولی):**
```html
<!DOCTYPE html>
<html>
<head>
  <script src="video-rtc.js"></script>
</head>
<body>
  <div class="sidebar">
    <h3>📹 دوربین‌ها</h3>
    <div id="camera-list"></div>
    <button onclick="addCamera()">+ اضافه کردن دوربین</button>
  </div>
  
  <div class="main">
    <!-- پخش ویدیو -->
    <video id="live-view" autoplay muted></video>
    
    <!-- کنترل‌ها -->
    <div class="controls">
      <button onclick="takePhoto()">📸 عکس</button>
      <button onclick="startRecording()">⏺ ضبط ۳۰ ثانیه</button>
      
      <!-- حرکت دوربین -->
      <div class="ptz">
        <button onclick="moveUp()">⬆</button><br>
        <button onclick="moveLeft()">⬅</button>
        <button onclick="stopMove()">⏹</button>
        <button onclick="moveRight()">➡</button><br>
        <button onclick="moveDown()">⬇</button>
      </div>
    </div>
  </div>
  
  <script>
    // ---------- قسمت ۱: پخش ویدیو ----------
    // فقط از video-rtc.js استفاده کن
    const videoElement = document.getElementById('live-view');
    let player;
    
    function playCamera(cameraName) {
      if (player) player.destroy();
      
      player = new VideoRTC({
        video: videoElement,
        url: `http://localhost:1984/api/webrtc?src=${cameraName}`
      });
    }
    
    // ---------- قسمت ۲: بقیه کارا ----------
    // از electronAPI استفاده کن
    async function loadCameras() {
      const cameras = await window.electronAPI.getCameras();
      displayCameraList(cameras);
    }
    
    async function takePhoto() {
      const currentCamera = getSelectedCamera();
      const imageData = await window.electronAPI.takeSnapshot(currentCamera);
      
      // عکس رو ذخیره کن
      const blob = new Blob([imageData], { type: 'image/jpeg' });
      const url = URL.createObjectURL(blob);
      
      // دانلود کن
      const a = document.createElement('a');
      a.href = url;
      a.download = `snapshot-${Date.now()}.jpg`;
      a.click();
    }
    
    async function moveUp() {
      await window.electronAPI.moveCamera('camera1', 0, 0.5); // بالا
    }
    
    async function startRecording() {
      const currentCamera = getSelectedCamera();
      const videoData = await window.electronAPI.startRecording(currentCamera, 30);
      
      // ویدیو رو ذخیره کن
      const blob = new Blob([videoData], { type: 'video/mp4' });
      const url = URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.href = url;
      a.download = `recording-${Date.now()}.mp4`;
      a.click();
    }
    
    // بارگذاری اولیه
    loadCameras();
  </script>
</body>
</html>
```

### **قدم ۶: کامپوننت‌های اصلی که باید بسازی**

**۱. VideoPlayer.vue/React Component:**
```javascript
// فقط video-rtc.js رو wrap کن
export default {
  props: ['cameraName'],
  template: `
    <div>
      <video ref="videoElement" autoplay muted controls></video>
    </div>
  `,
  mounted() {
    this.player = new VideoRTC({
      video: this.$refs.videoElement,
      url: `http://localhost:1984/api/webrtc?src=${this.cameraName}`
    });
  },
  beforeUnmount() {
    if (this.player) this.player.destroy();
  }
};
```

**۲. CameraManager.vue/React:**
```javascript
// از OpenAPI استفاده می‌کنه
export default {
  data() {
    return { cameras: [] };
  },
  async created() {
    const api = new DefaultApi(); // از OpenAPI ساخته شده
    this.cameras = await api.getStreams();
  },
  methods: {
    async addCamera(url, name) {
      await api.putStreams(url, name);
    }
  }
};
```

### **📌 خلاصه برای تو به عنوان فرانت‌اند:**

**"video-rtc.js" = فقط برای این:**
```javascript
// فقط ویدیوی زنده نشون بده
const player = new VideoRTC({
  video: videoElement,
  url: '/api/webrtc?src=camera1'
});
// کار دیگری ازش نداز!
```

**"openapi.yaml" = برای همه کارهای دیگر:**
- لیست کردن دوربین‌ها
- عکس گرفتن
- ضبط ویدیو
- کنترل حرکت دوربین
- پیدا کردن دوربین جدید
- تنظیمات برنامه

**Electron = واسه این کارا:**
- برنامه دسکتاپ درست کنی
- به فایل‌سیستم دسترسی داشته باشی
- توی سیستم‌تری (کنار ساعت) باشی
- با کلیک راست روی فایل‌ها کار کنی
- نوتیفیکیشن سیستمی بدی

### **🚀 شروع کن اینطوری:**

1. **اول OpenAPI رو باز کن**، ببین چه endpointهایی داریم
2. **یه صفحه ساده HTML بساز** با video-rtc.js
3. **کتابخونه API از OpenAPI درست کن** (با openapi-generator)
4. **کامپوننت VideoPlayer بساز** (دور video-rtc.js)
5. **کامپوننت CameraList بساز** (با کتابخونه API)
6. **کنترل‌ها رو اضافه کن** (عکس، ضبط، PTZ)
7. **برای Electron wrap کن** (main.js, preload.js)

**مهم:** video-rtc.js فقط پخش ویدیو بلده! برای هر کار دیگه، باید از API استفاده کنی که توی openapi.yaml تعریف شده.

نیاز به کمک بیشتری داری؟ بپرس! 🎯
