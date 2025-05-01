export interface RepoOwner {
  id: number;
  name: string;
  url: string;
  avatarUrl: string;
}

export enum WorkspaceType {
  EXISTING = "existing",
  NEW = "new",
}

export interface WorkspaceOption {
  name?: string;
  settings?: WorkspaceSettings;
  type: WorkspaceType;
}

export interface Repo {
  gitRepoId: number;
  name: string;
  fullName: string;
  url: string;
  visibility: string;
  owner: RepoOwner;
  lastOpenedUnix: number | null; // Unix timestamp in seconds

  runtimeFiles: { name: string; contents: string }[] | null;
  browserStorage: { [key: string]: string } | null;

  workspaces: WorkspaceOption[];
}

export interface Workspace {
  gitRepoId: number;
  workspaceName: string;
  repoName: string;
  repoFullName: string;
  repoUrl: string;
  visibility: string;
  owner: RepoOwner;
  settings: WorkspaceSettings | null;

  runtimeFiles: { name: string; contents: string }[] | null;
  browserStorage: { [key: string]: string } | null;
  issueNumber: number | null;
}

export interface WorkspaceSettings {
  branch: string | null;
  packageManager: "npm" | "pnpm" | "yarn" | "bun" | null;
  port: number | null;
  devCommand: string | null;
  rootDirectory: string | null;
  installCommand: string | null;
  tsconfig_path: string | null;
  availableBranches?: string[];
  workspaceName?: string;
}
