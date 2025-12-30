/**
 * Dashboard Bridge
 * Exposes dashboard-related IPC calls to the renderer process
 * Provides type-safe access to dashboard data through the electronAPI
 */

import { ipcRenderer } from "electron";
import type {
  IDashboardData,
  IUserData,
  ICameraStatus,
  IMotionStats,
} from "@/types/electronAPI";

/**
 * Dashboard bridge object
 * Contains all methods for fetching dashboard-related data
 * All methods are async and return promises
 */
export const dashboardBridge = {
  /**
   * Fetches complete dashboard data
   * Includes user info, camera status, motion stats, and quick actions
   *
   * @returns Promise resolving to complete dashboard data
   */
  getDashboardData: (): Promise<IDashboardData> =>
    ipcRenderer.invoke("dashboard:get-data"),

  /**
   * Fetches only user data
   * Useful for refreshing user/system information
   *
   * @returns Promise resolving to user data
   */
  getUserData: (): Promise<IUserData> =>
    ipcRenderer.invoke("dashboard:get-user"),

  /**
   * Fetches current camera connection status
   * Shows connected, active, and inactive camera counts
   *
   * @returns Promise resolving to camera status
   */
  getCameraStatus: (): Promise<ICameraStatus> =>
    ipcRenderer.invoke("dashboard:get-camera-status"),

  /**
   * Fetches motion detection statistics
   * Returns time-series motion data and summary metrics
   *
   * @returns Promise resolving to motion statistics
   */
  getMotionStats: (): Promise<IMotionStats> =>
    ipcRenderer.invoke("dashboard:get-motion-stats"),
};
