export enum LogType {
  ERROR = "error",
  INFO = "info",
  USER = "user",
}

export type ConsoleOutput = {
  line: string;
  logType: LogType;
};

export type TerminalCommandResult = {
  output: string;
  errors: string;
  statusCode: number;
};
