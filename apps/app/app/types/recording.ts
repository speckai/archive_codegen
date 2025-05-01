export interface BoundingBox {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
  centerX: number;
  centerY: number;
}

export interface Target {
  tagName: string;
  id?: string;
  className?: string;
  name?: string;
  value?: string;
  checked?: boolean;
  xpath?: string;
  cssSelector?: string;
  boundingBox?: BoundingBox;
  innerText?: string;
}

export interface ViewportSize {
  width: number;
  height: number;
}

export interface ConsoleLog {
  timestamp: number; // ms since recording started
  level: "log" | "warn" | "error" | "info" | "debug";
  output: string;
  traceback?: string[];
}

export interface SystemInfo {
  operatingSystem: string;
  userAgent: string;
}

export interface RecordingEvent {
  type: string;
  delay: number;
  url: string;
  target?: Target;
  button?: number;
  scrollX?: number;
  scrollY?: number;
  value?: string;
  checked?: boolean;
  timeTaken?: number;
  [key: string]: any;
}

export interface SnakeCaseBoundingBox {
  min_x: number;
  min_y: number;
  max_x: number;
  max_y: number;
  width: number;
  height: number;
  center_x: number;
  center_y: number;
}

export interface SnakeCaseTarget {
  tag_name: string;
  id?: string;
  class_name?: string;
  name?: string;
  value?: string;
  checked?: boolean;
  xpath?: string;
  css_selector?: string;
  bounding_box?: SnakeCaseBoundingBox;
  inner_text?: string;
}

export interface SnakeCaseViewportSize {
  width: number;
  height: number;
}

export interface SnakeCaseConsoleLog {
  timestamp: number;
  level: "log" | "warn" | "error" | "info" | "debug";
  output: string;
  traceback?: string[];
}

export interface SnakeCaseRecordingEvent {
  type: string;
  delay: number;
  url: string;
  target?: SnakeCaseTarget;
  button?: number;
  scroll_x?: number;
  scroll_y?: number;
  value?: string;
  checked?: boolean;
  time_taken?: number;
  [key: string]: any;
}

export interface SnakeCaseSystemInfo {
  operating_system: string;
  user_agent: string;
}

export interface Recording {
  id: string;
  events: RecordingEvent[];
  baseUrl: string;
  initialUrl: string;
  duration: number;
  viewportSize: ViewportSize;
  name: string;
  annotation?: string;
  consoleLogs: ConsoleLog[];
  systemInfo: SystemInfo;
}

export interface SnakeCaseRecording {
  id: string;
  events: SnakeCaseRecordingEvent[];
  base_url: string;
  initial_url: string;
  duration: number;
  viewport_size: SnakeCaseViewportSize;
  name: string;
  annotation?: string;
  console_logs: SnakeCaseConsoleLog[];
  system_info: SnakeCaseSystemInfo;
}

const camelToSnakeCase = (str: string): string => {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
};

const convertKeysToSnakeCase = (obj: any): any => {
  if (obj === null || typeof obj !== "object") {
    return obj;
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => convertKeysToSnakeCase(item));
  }

  return Object.keys(obj).reduce((acc, key) => {
    const snakeCaseKey = camelToSnakeCase(key);
    acc[snakeCaseKey] = convertKeysToSnakeCase(obj[key]);
    return acc;
  }, {} as any);
};

const toSnakeCaseTarget = (target: Target): SnakeCaseTarget => {
  return convertKeysToSnakeCase(target) as SnakeCaseTarget;
};

const toSnakeCaseEvent = (event: RecordingEvent): SnakeCaseRecordingEvent => {
  const snakeCaseEvent = convertKeysToSnakeCase(
    event,
  ) as SnakeCaseRecordingEvent;

  if (event.target) {
    snakeCaseEvent.target = toSnakeCaseTarget(event.target);
  }

  return snakeCaseEvent;
};
const toSnakeCaseViewportSize = (
  viewportSize: ViewportSize,
): SnakeCaseViewportSize => {
  return convertKeysToSnakeCase(viewportSize) as SnakeCaseViewportSize;
};

export const toSnakeCase = (recording: Recording): SnakeCaseRecording => {
  return {
    id: recording.id,
    events: recording.events.map(toSnakeCaseEvent),
    base_url: recording.baseUrl,
    initial_url: recording.initialUrl,
    duration: recording.duration,
    viewport_size: toSnakeCaseViewportSize(recording.viewportSize),
    name: recording.name,
    annotation: recording.annotation,
    console_logs: recording.consoleLogs,
    system_info: {
      operating_system: recording.systemInfo.operatingSystem,
      user_agent: recording.systemInfo.userAgent,
    },
  };
};
