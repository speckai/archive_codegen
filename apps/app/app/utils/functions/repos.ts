import { Repo, Workspace, WorkspaceSettings } from "@ctypes/repos";

const convertToRepoSettings = (settings: any): WorkspaceSettings | null => {
  if (!settings) {
    return null;
  }
  return {
    branch: settings.branch,
    packageManager: settings.package_manager,
    port: settings.port,
    devCommand: settings.dev_command,
    rootDirectory: settings.root_directory,
    installCommand: settings.install_command,
    tsconfig_path: settings.tsconfig_path,
    availableBranches: settings.available_branches,
  };
};

const convertToRepo = (repo: any): Repo => ({
  gitRepoId: repo.git_repo_id,
  name: repo.name,
  fullName: repo.full_name,
  url: repo.url,
  visibility: repo.visibility,
  owner: {
    id: repo.owner.id,
    name: repo.owner.name,
    url: repo.owner.url,
    avatarUrl: repo.owner.avatar_url,
  },
  lastOpenedUnix: repo.last_opened_unix || repo.updated_at,
  runtimeFiles: repo.runtime_files,
  browserStorage: repo.browser_storage,
  workspaces: repo.workspaces
    ? repo.workspaces.map((workspace: any) => ({
        name: workspace.name,
        settings: convertToRepoSettings(workspace.settings),
        type: workspace.type,
      }))
    : null,
});

export const convertToWorkspace = (space: any): Workspace => ({
  gitRepoId: space.git_repo_id,
  workspaceName: space.workspace_name,
  repoName: space.repo_name,
  repoFullName: space.repo_full_name,
  repoUrl: space.repo_url,
  visibility: space.visibility,
  owner: {
    name: space.owner.name,
    url: space.owner.url,
    avatarUrl: space.owner.avatar_url,
    id: space.owner.id,
  },
  settings: convertToRepoSettings(space.settings),
  runtimeFiles: space.runtime_files || null,
  browserStorage: space.browser_storage || null,
  issueNumber: space.issue_number || null,
});

export async function addInstalledRepos(
  gitRepoIds: number[],
  token: string,
): Promise<{
  success: boolean;
  message?: string;
  addedRepos?: Repo[];
}> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/repos/entries/added/add`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ git_repo_ids: gitRepoIds }),
    },
  );
  if (response.ok) {
    const result = await response.json();
    if (result.success) {
      const addedRepos = result.added_repos.map(convertToRepo);

      return {
        success: true,
        message: result.message,
        addedRepos,
      };
    } else {
      console.error("Failed to add repos:", result.message);
      return { success: false, message: result.message };
    }
  } else {
    console.error(
      "Failed to add repos. Server responded with:",
      response.status,
    );
    return { success: false, message: response.status.toString() };
  }
}

export async function removeAddedRepo(
  gitRepoId: number,
  token: string,
): Promise<{
  success: boolean;
  message: string;
  addedRepos?: Repo[];
}> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/repos/entries/added/remove`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ git_repo_id: gitRepoId }),
    },
  );
  if (response.ok) {
    const result = await response.json();
    if (result.success) {
      const addedRepos = result.added_repos.map(convertToRepo);
      return { success: true, message: result.message, addedRepos };
    } else {
      return { success: false, message: result.message };
    }
  } else {
    console.error(
      `Failed to remove repo. Server responded with: ${response.status}`,
    );
    return {
      success: false,
      message: `Failed to remove repo. Server responded with: ${response.status}`,
    };
  }
}

export async function getAddedRepos(token: string): Promise<{
  success: boolean;
  message?: string;
  addedRepos?: Repo[];
  installed?: boolean;
}> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/repos/entries/added/get`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
  if (response.ok) {
    const result = await response.json();
    if (result.success) {
      const addedRepos = result.added_repos.map(convertToRepo);
      return { success: true, addedRepos: addedRepos };
    } else if (result.status === "NO_REPOS_FOUND") {
      return {
        success: false,
        message: "No added repos found. Click the '+' button to add a repo.",
      };
    } else if (result.status === "NO_INSTALLATION_ID") {
      return {
        success: false,
        message: "Please install the app to add repos.",
      };
    } else {
      return { success: false, message: result.status };
    }
  } else {
    console.error(
      `Failed to get added repos. Server responded with: ${response.status}`,
    );
    return {
      success: false,
      message: `Failed to get added repos. Server responded with: ${response.status}`,
    };
  }
}

export async function getInstalledRepos(token: string): Promise<{
  success: boolean;
  message: string;
  installedRepos?: Repo[];
  failedInstallations?: string[];
  existingRepos?: string[];
}> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/repos/entries/installed/get`,
    {
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    },
  );

  if (!response.ok) {
    return {
      success: false,
      message: `Failed to get installed repos. Server responded with: ${response.status}`,
    };
  }

  const data = await response.json();

  if (!data.success) {
    return {
      success: false,
      message: data.message,
    };
  }

  const installedRepos = data.installed_repos.map(convertToRepo);
  const failedInstallations = data.failed_installations.map(
    (installation: any) => installation.name,
  );
  const existingRepos = data.existing_repos;
  return {
    success: true,
    message: "",
    installedRepos,
    failedInstallations,
    existingRepos,
  };
}

export async function getWorkspaceSettings(
  taskId: string,
  token: string,
): Promise<{
  success: boolean;
  message?: string;
  settings?: WorkspaceSettings;
}> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/repos/settings/get/${taskId}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );

  if (!response.ok) {
    return {
      success: false,
      message: `Failed to get repo settings. Server responded with: ${response.status}`,
    };
  }

  const data = await response.json();

  if (!data.settings) {
    return {
      success: false,
      message: data.message,
    };
  }

  return {
    success: true,
    settings: {
      packageManager: data.settings.package_manager,
      port: data.settings.port,
      devCommand: data.settings.dev_command,
      rootDirectory: data.settings.root_directory,
      installCommand: data.settings.install_command,
      branch: data.settings.branch,
      tsconfig_path: data.settings.tsconfig_path || null,
      availableBranches: data.settings.available_branches,
      workspaceName: data.settings.space_name,
    },
  };
}

export async function saveWorkspaceSettings(
  gitRepoId: number,
  workspaceName: string,
  token: string,
  settings: WorkspaceSettings,
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/repos/settings/save`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        git_repo_id: gitRepoId,
        workspace_name: workspaceName,
        repo_settings: {
          package_manager: settings.packageManager,
          port: settings.port,
          dev_command: settings.devCommand,
          root_directory: settings.rootDirectory,
          install_command: settings.installCommand,
          branch: settings.branch,
          tsconfig_path: settings.tsconfig_path,
        },
        new_workspace_name:
          settings.workspaceName !== workspaceName
            ? settings.workspaceName
            : null,
      }),
    },
  );

  if (!response.ok) {
    return {
      success: false,
      message: `Failed to save repo settings. Server responded with: ${response.status}`,
    };
  }

  const data = await response.json();
  return { success: true, message: data.message };
}

export async function getRuntimeFiles(
  gitRepoId: number,
  token: string,
): Promise<{
  success: boolean;
  message?: string;
  runtimeFiles?: { name: string; contents: string }[];
}> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/repos/settings/runtime_files/get/${gitRepoId}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );

  if (!response.ok) {
    return {
      success: false,
      message: `Failed to get runtime files. Server responded with: ${response.status}`,
    };
  }

  const data = await response.json();
  return { success: true, runtimeFiles: data.runtime_files };
}

export async function saveRuntimeFiles(
  gitRepoId: number,
  token: string,
  runtimeFiles: { name: string; contents: string }[],
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/repos/settings/runtime_files/save`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        git_repo_id: gitRepoId,
        runtime_files: runtimeFiles,
      }),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    return {
      success: false,
      message:
        data.message ||
        `Failed to save runtime files. Server responded with: ${response.status}`,
    };
  }

  return {
    success: data.success,
    message: data.message,
  };
}

export async function getUserCustomRules(
  token: string,
): Promise<{ success: boolean; message?: string; rules?: string }> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/repos/settings/custom_rules/user/get`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );

  if (!response.ok) {
    return {
      success: false,
      message: `Failed to get user custom rules. Server responded with: ${response.status}`,
    };
  }

  const data = await response.json();
  return {
    success: true,
    rules: data.rules,
  };
}

export async function saveUserCustomRules(
  token: string,
  rules: string,
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/repos/settings/custom_rules/user/save`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ rules }),
    },
  );

  if (!response.ok) {
    return {
      success: false,
      message: `Failed to save user custom rules. Server responded with: ${response.status}`,
    };
  }

  const data = await response.json();
  return { success: true, message: data.message };
}

export async function getRepoCustomRules(
  gitRepoId: number,
  token: string,
): Promise<{ success: boolean; message?: string; rules?: string }> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/repos/settings/custom_rules/repo/get/${gitRepoId}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );

  if (!response.ok) {
    return {
      success: false,
      message: `Failed to get repo custom rules. Server responded with: ${response.status}`,
    };
  }

  const data = await response.json();
  return {
    success: true,
    rules: data.rules,
  };
}

export async function saveRepoCustomRules(
  gitRepoId: number,
  token: string,
  rules: string,
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/repos/settings/custom_rules/repo/save`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        git_repo_id: gitRepoId,
        rules,
      }),
    },
  );

  if (!response.ok) {
    return {
      success: false,
      message: `Failed to save repo custom rules. Server responded with: ${response.status}`,
    };
  }

  const data = await response.json();
  return { success: true, message: data.message };
}
