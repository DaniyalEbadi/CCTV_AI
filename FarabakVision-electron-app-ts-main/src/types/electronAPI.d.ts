/**
 * Dashboard Types and Interfaces
 * Defines the structure of all data used across dashboard cards
 * This ensures type safety throughout the dashboard components
 */

/**
 * User data structure for UserCard component
 * Contains information about the current user and system status
 */
export interface IUserData {
  /** Username or display name */
  username: string;
  /** System OS name (Windows, macOS, Linux) */
  osName: string;
  /** Device MAC address */
  macAddress: string;
  /** Connection status to the system (online/offline) */
  connectionStatus: "connected" | "disconnected";
  /** System uptime formatted as a readable string */
  connectedSince?: string;
}

/**
 * Camera status representation
 * Used in CameraCountCard to show different status categories
 */
export interface ICameraStatus {
  name: string;
  amount: number;
  color: string;
}

/**
 * Camera brand information
 * Used in CameraBrandsCard to display brand distribution
 */
export interface ICameraBrand {
  /** Brand name (e.g., "Hikvision", "Dahua") */
  name: string;
  /** Number of cameras of this brand */
  value: number;
  /** Brand color */
  fill: string;
}

/**
 * Motion statistics data point
 * Represents motion detection metrics at a specific time
 */
export interface IMotionDataPoint {
  /** Time identifier or timestamp */
  time: string;
  /** Count of motion events at this time */
  count: number;
}

/**
 * Complete motion statistics for MotionStatsCard
 * Contains time-series data for motion detection
 */
export interface IMotionStats {
  /** Array of motion data points over time */
  dataPoints: IMotionDataPoint[];
  /** Total motion events recorded in the period */
  totalEvents: number;
  /** Peak motion events count */
  peakCount: number;
}

/**
 * Quick action item for QuickActionsCard
 * Represents a single action button/tile
 */
export interface IQuickAction {
  /** Unique action identifier */
  id: string;
  /** Action label/title */
  label: string;
  /** Icon name or identifier for the action */
  icon: string;
  /** Action handler function name */
  action: string;
  /** Optional custom styling class */
  className?: string;
}

/**
 * Complete dashboard data structure
 * Aggregates all data needed for the dashboard
 */
export interface IDashboardData {
  /** User information and system status */
  user: IUserData;
  /** Camera connection statistics */
  cameraStatus: ICameraStatus[];
  /** Camera brand distribution */
  cameraBrands: ICameraBrand[];
  /** Motion detection statistics */
  motionStats: IMotionStats;
  /** Quick action items */
  quickActions: IQuickAction[];
}

/**
 * IElectronAPI Interface
 * Defines all available Electron IPC methods exposed to the renderer
 * This ensures type safety when using window.electronAPI
 */
export interface IElectronAPI {
  /**
   * Language management methods
   */
  getLanguage: () => Promise<string>;
  setLanguage: (lang: string) => void;
  dashboard: {
    /** Fetch complete dashboard data */
    getDashboardData: () => Promise<IDashboardData>;
    /** Fetch user and system information */
    getUserData: () => Promise<IUserData>;
    /** Fetch camera connection status */
    getCameraStatus: () => Promise<ICameraStatus[]>;
    /** Fetch motion detection statistics */
    getMotionStats: () => Promise<IMotionStats>;
  };
  window: {
    minimize: () => void;
    maximize: () => void;
    close: () => void;
    isMaximized: () => Promise<boolean>;
    onMaximized: (callback: (isMaximized: boolean) => void) => void;
    removeMaximizedListener: () => void;
  };
}

declare global {
  interface Window {
    electronAPI: IElectronAPI;
  }
}
