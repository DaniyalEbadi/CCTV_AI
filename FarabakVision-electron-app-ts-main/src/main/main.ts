import { app, BrowserWindow, ipcMain, Menu } from "electron";
import path from "node:path";
import started from "electron-squirrel-startup";

import Store from "electron-store";
import {
  getDashboardData,
  getUserData,
  getCameraStatus,
  getMotionStats,
} from "@main/services/dashboard";

// Declare Vite injected variables
declare const MAIN_WINDOW_VITE_DEV_SERVER_URL: string;
declare const MAIN_WINDOW_VITE_NAME: string;

const store = new Store(); // For persistence

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (started) {
  app.quit();
}

/**
 * Dashboard IPC Handlers
 * These handlers provide mock dashboard data to the renderer process
 * Registered early so they're available when window loads
 */

/**
 * Handle dashboard data request
 * Returns complete dashboard data including user info, camera status, and motion stats
 * Usage: await window.electronAPI.dashboard.getDashboardData()
 */
ipcMain.handle("dashboard:get-data", () => {
  return getDashboardData();
});

/**
 * Handle user data request
 * Returns current user and system information
 * Usage: await window.electronAPI.dashboard.getUserData()
 */
ipcMain.handle("dashboard:get-user", () => {
  return getUserData();
});

/**
 * Handle camera status request
 * Returns camera connection and activity status
 * Usage: await window.electronAPI.dashboard.getCameraStatus()
 */
ipcMain.handle("dashboard:get-camera-status", () => {
  return getCameraStatus();
});

/**
 * Handle motion statistics request
 * Returns motion detection data and statistics
 * Usage: await window.electronAPI.dashboard.getMotionStats()
 */
ipcMain.handle("dashboard:get-motion-stats", () => {
  return getMotionStats();
});

/**
 * Window Control IPC Handlers
 * These handlers allow the renderer to control the window
 */
ipcMain.on("window:minimize", (event) => {
  const window = BrowserWindow.fromWebContents(event.sender);
  window?.minimize();
});

ipcMain.on("window:maximize", (event) => {
  const window = BrowserWindow.fromWebContents(event.sender);
  if (window?.isMaximized()) {
    window.unmaximize();
  } else {
    window?.maximize();
  }
});

ipcMain.on("window:close", (event) => {
  const window = BrowserWindow.fromWebContents(event.sender);
  window?.close();
});

ipcMain.handle("window:is-maximized", (event) => {
  const window = BrowserWindow.fromWebContents(event.sender);
  return window?.isMaximized() ?? false;
});

const createWindow = () => {
  // Create the browser window.
  const mainWindow = new BrowserWindow({
    width: 810,
    height: 610,
    minWidth: 810,
    minHeight: 610,
    show: false,
    center: true,
    backgroundColor: "#101517",
    frame: false, // Remove default title bar
    titleBarStyle: "hidden", // For macOS
    icon: path.join(__dirname, "src/assets/icons/icon.png"), // Explicit PNG for Linux
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
    },
  });

  // Send maximize/unmaximize events to renderer
  mainWindow.on("maximize", () => {
    mainWindow.webContents.send("window:maximized", true);
  });

  mainWindow.on("unmaximize", () => {
    mainWindow.webContents.send("window:maximized", false);
  });

  // and load the index.html of the app.
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(
      path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`)
    );
  }

  // Show when ready
  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
  });

  // Open the DevTools.
  mainWindow.webContents.openDevTools();
};

// Set the application menu
Menu.setApplicationMenu(null);

// On app ready, detect and send initial language
const preferredLangs = app.getPreferredSystemLanguages(); // e.g., ['fa-IR', 'en-US']
let initialLang = "en"; // Default
if (preferredLangs.length > 0) {
  const topLang = preferredLangs[0].split("-")[0]; // e.g., 'fa'
  if (["en", "fa", "ar"].includes(topLang)) {
    initialLang = topLang;
  }
}

// If no stored lang (first start), set it
if (!store.get("language")) {
  store.set("language", initialLang);
}

// IPC to get/set language from renderer
ipcMain.handle("get-language", () => store.get("language"));
ipcMain.on("set-language", (event, lang) => {
  if (["en", "fa", "ar"].includes(lang)) {
    store.set("language", lang);
    // Optionally reload window or notify renderer to update
  }
});

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.on("ready", createWindow);

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  // On OS X it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
