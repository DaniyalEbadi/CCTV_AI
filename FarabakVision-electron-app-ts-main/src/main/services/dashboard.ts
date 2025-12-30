/**
 * Mock Dashboard Service
 * Generates realistic mock data for dashboard components
 * This simulates API responses until real backend APIs are implemented
 */

import { platform, release, networkInterfaces } from "os";
import * as fs from "fs";

import type {
  IDashboardData,
  IUserData,
  ICameraStatus,
  ICameraBrand,
  IMotionStats,
  IQuickAction,
  IMotionDataPoint,
} from "../../types/electronAPI";

/**
 * Mock Camera Brands Database
 * Realistic camera brands commonly used in surveillance systems
 */
const MOCK_CAMERA_BRANDS: ICameraBrand[] = [
  { name: "Reolink", value: 5, fill: "#4ECDC4" },
  { name: "Dahua", value: 3, fill: "#FF6B6B" },
  { name: "Uniview", value: 2, fill: "#FFD166" },
];

/**
 * Mock Quick Actions
 * Common actions users can perform from the dashboard
 */
const MOCK_QUICK_ACTIONS: IQuickAction[] = [
  {
    id: "add-new-camera",
    label: "Add new Camera",
    icon: "",
    action: "addNewCamera",
  },
  {
    id: "add-new-user",
    label: "Add new User",
    icon: "",
    action: "addNewUser",
  },
  {
    id: "change-theme",
    label: "Change Theme",
    icon: "",
    action: "changeTheme",
  },
  {
    id: "app-info",
    label: "App Info",
    icon: "",
    action: "appInfo",
  },
];

/**
 * Gets the MAC address of the primary network interface
 * Used to uniquely identify the device
 *
 * @returns MAC address in uppercase, or fallback if none found
 */
function getMacAddress(): string {
  const interfaces = networkInterfaces();

  // Find the first non-internal, IPv4 address with a MAC
  for (const [, addrs] of Object.entries(interfaces)) {
    if (addrs) {
      for (const addr of addrs) {
        if (addr.family === "IPv4" && !addr.internal && addr.mac) {
          return addr.mac.toUpperCase();
        }
      }
    }
  }

  // Fallback if no valid MAC found
  return "00:00:00:00:00:00";
}

/**
 * Checks if the system is currently connected to network
 * Determines connection status based on network interfaces
 *
 * @returns "connected" if network available, "disconnected" otherwise
 */
function getConnectionStatus(): "connected" | "disconnected" {
  const interfaces = networkInterfaces();

  // Check if there are any active network interfaces
  for (const [, addrs] of Object.entries(interfaces)) {
    if (addrs) {
      for (const addr of addrs) {
        if (addr.family === "IPv4" && !addr.internal) {
          return "connected";
        }
      }
    }
  }

  return "disconnected";
}

/**
 * Gets a user-friendly OS name with version details where possible.
 * Handles Windows, macOS, Linux (with distro if available), and falls back for others.
 *
 * @returns {string} Friendly OS name (e.g., "Windows 11", "macOS Ventura (13)", "Ubuntu 22.04 LTS")
 */
function getFriendlyOSName(): string {
  const plat = platform();
  const rel = release();

  if (plat === "win32") {
    const parts = rel.split(".");
    const major = parts[0];
    const build = parseInt(parts[2], 10) || 0;

    if (major === "10") {
      return build >= 22000 ? "Windows 11" : "Windows 10";
    } else if (major === "6") {
      if (rel.startsWith("6.3")) return "Windows 8.1";
      if (rel.startsWith("6.2")) return "Windows 8";
      if (rel.startsWith("6.1")) return "Windows 7";
      return "Windows (Older Version)";
    } else if (major === "11") {
      return "Windows 11"; // Future-proofing
    }
    return "Windows";
  } else if (plat === "darwin") {
    const major = parseInt(rel.split(".")[0], 10);
    if (major >= 23) return "macOS Sonoma (14)";
    if (major >= 22) return "macOS Ventura (13)";
    if (major >= 21) return "macOS Monterey (12)";
    if (major >= 20) return "macOS Big Sur (11)";
    if (major >= 19) return "macOS Catalina (10.15)";
    if (major >= 18) return "macOS Mojave (10.14)";
    if (major >= 17) return "macOS High Sierra (10.13)";
    if (major >= 16) return "macOS Sierra (10.12)";
    if (major >= 15) return "OS X El Capitan (10.11)";
    if (major >= 14) return "OS X Yosemite (10.10)";
    return "macOS";
  } else if (plat === "linux") {
    try {
      const osRelease = fs.readFileSync("/etc/os-release", "utf8");
      const lines = osRelease.split("\n");
      let prettyName = "";
      for (const line of lines) {
        if (line.startsWith("PRETTY_NAME=")) {
          prettyName = line.split("=")[1].replace(/"/g, "").trim();
          break;
        }
      }
      return prettyName || `Linux (Kernel ${rel})`;
    } catch (e) {
      return `Linux (Kernel ${rel})`;
    }
  } else {
    // Fallback for less common platforms like 'freebsd', 'sunos', etc.
    return `${plat.charAt(0).toUpperCase() + plat.slice(1)} ${rel}`;
  }
}

/**
 * Generates mock user data with real system information
 * Uses actual OS and network data, keeps username as mock
 *
 * @returns User data with real OS name, MAC address, and connection status
 */
/**
 * Generates mock user data with real system information
 * Uses actual OS and network data, keeps username as mock
 *
 * @returns User data with real OS name, MAC address, and connection status
 */
function generateMockUserData(): IUserData {
  // Calculate app start time in milliseconds
  const uptimeMs = process.uptime() * 1000;
  const startTime = new Date(Date.now() - uptimeMs);

  return {
    username: "System Admin",
    osName: getFriendlyOSName(),
    macAddress: getMacAddress(),
    connectionStatus: getConnectionStatus(),
    connectedSince: startTime.toLocaleString(), // Shows local start time (e.g., "12/11/2025, 10:00:00 AM")
  };
}

/**
 * Generates mock cameras status statistics
 *
 * @returns Array of camera statuses
 */
function generateMockCameraStatus(): ICameraStatus[] {
  return [
    { name: "activeCameras", amount: 10, color: "#22C55E" },
    { name: "inactiveCameras", amount: 3, color: "#EF4444" },
  ];
}

/**
 * Generates mock motion statistics with time-series data
 * Creates a realistic motion pattern over time
 *
 * @returns Motion statistics with data points and summary metrics
 */
function generateMockMotionStats(): IMotionStats {
  // Generate mock data points for the last 24 hours in 6-hour intervals
  const dataPoints: IMotionDataPoint[] = [];
  const now = new Date();

  for (let i = 0; i < 4; i++) {
    const time = new Date(now.getTime() - i * 6 * 60 * 60 * 1000);
    dataPoints.unshift({
      time: time.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      // Generate realistic motion counts with some variation
      count: Math.floor(Math.random() * 50) + 20,
    });
  }

  const counts = dataPoints.map((dp) => dp.count);
  const totalEvents = counts.reduce((a, b) => a + b, 0);
  const peakCount = Math.max(...counts);

  return {
    dataPoints,
    totalEvents,
    peakCount,
  };
}

/**
 * Gets complete dashboard data
 * Aggregates all mock data for dashboard initialization
 * This function simulates a complete API response
 *
 * @returns Complete dashboard data with all sections populated
 */
export function getDashboardData(): IDashboardData {
  return {
    user: generateMockUserData(),
    cameraStatus: generateMockCameraStatus(),
    cameraBrands: MOCK_CAMERA_BRANDS,
    motionStats: generateMockMotionStats(),
    quickActions: MOCK_QUICK_ACTIONS,
  };
}

/**
 * Gets only user data
 * Useful when user information needs to be refreshed separately
 *
 * @returns Updated mock user data
 */
export function getUserData(): IUserData {
  return generateMockUserData();
}

/**
 * Gets only camera status
 * Useful for real-time status updates
 *
 * @returns Current camera status
 */
export function getCameraStatus(): ICameraStatus[] {
  return generateMockCameraStatus();
}

/**
 * Gets only motion statistics
 * Can be called more frequently to update motion data
 *
 * @returns Updated motion statistics
 */
export function getMotionStats(): IMotionStats {
  return generateMockMotionStats();
}
