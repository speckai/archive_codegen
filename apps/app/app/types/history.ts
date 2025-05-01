interface HistoryItemType {
  title: string;
  unix_time: number;
  is_verified: boolean;
  commit_id: string;
  description: string;
}

export type { HistoryItemType };
