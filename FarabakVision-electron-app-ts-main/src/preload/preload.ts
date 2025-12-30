/**
 * Preload Script
 * Runs in an isolated context with access to Node.js APIs
 * Safely exposes limited IPC functionality to the renderer process
 * Reference: https://www.electronjs.org/docs/latest/tutorial/process-model#preload-scripts
 */

import { contextBridge, ipcRenderer } from "electron";
import { dashboardBridge } from "./bridges/dashboard.bridge";

/**
 * Expose electronAPI to the renderer process
 * This object is available as window.electronAPI in the renderer
 * All methods are sandboxed and only allow specific IPC calls
 */
contextBridge.exposeInMainWorld("electronAPI", {
  /**
   * Language management methods
   * Get and set application language preferences
   */
  getLanguage: () => ipcRenderer.invoke("get-language"),
  setLanguage: (lang: string) => ipcRenderer.send("set-language", lang),

  /**
   * Dashboard data methods
   * Fetch dashboard-related data from main process
   */
  dashboard: dashboardBridge,

  // Window control APIs
  window: {
    minimize: () => ipcRenderer.send("window:minimize"),
    maximize: () => ipcRenderer.send("window:maximize"),
    close: () => ipcRenderer.send("window:close"),
    isMaximized: () => ipcRenderer.invoke("window:is-maximized"),
    onMaximized: (callback: (isMaximized: boolean) => void) => {
      ipcRenderer.on("window:maximized", (_event, isMaximized) =>
        callback(isMaximized)
      );
    },
    removeMaximizedListener: () => {
      ipcRenderer.removeAllListeners("window:maximized");
    },
  },
});
