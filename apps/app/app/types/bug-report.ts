export interface ConsoleLog {
  artifactId: string;
  contentType: string;
  markdownFormat: string;
  data: {
    id: string;
    recordingId: string;
    title: string;
    description: string;
    timestamp: number;
    log: {
      timestamp: number;
      level: string;
      output: string;
      traceback: string[];
    };
    context: string;
  };
}

export interface TextModels {
  [key: string]: ConsoleLog;
}

export interface AssetUrls {
  [key: string]: string;
}

export interface BugReport {
  report: string;
  assetUrls: AssetUrls;
  textModels: TextModels;
}

// Function to convert snake_case to camelCase
export function snakeToCamel(str: string): string {
  if (str.startsWith("console_")) {
    return str;
  }
  return str.replace(/_([a-z])/g, (match, letter) => letter.toUpperCase());
}

// Function to convert an object's keys from snake_case to camelCase recursively
export function convertToCamelCase<T>(obj: any): T {
  if (Array.isArray(obj)) {
    return obj.map((item) => convertToCamelCase(item)) as unknown as T;
  }

  if (obj !== null && typeof obj === "object") {
    const newObj: any = {};

    Object.keys(obj).forEach((key) => {
      const camelKey = snakeToCamel(key);
      newObj[camelKey] = convertToCamelCase(obj[key]);
    });

    return newObj as T;
  }

  return obj as T;
}

// Function to convert camelCase to snake_case
export function camelToSnake(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

// Function to convert an object's keys from camelCase to snake_case recursively
export function convertToSnakeCase<T>(obj: any): T {
  if (Array.isArray(obj)) {
    return obj.map((item) => convertToSnakeCase(item)) as unknown as T;
  }

  if (obj !== null && typeof obj === "object") {
    const newObj: any = {};

    Object.keys(obj).forEach((key) => {
      const snakeKey = camelToSnake(key);
      newObj[snakeKey] = convertToSnakeCase(obj[key]);
    });

    return newObj as T;
  }

  return obj as T;
}
