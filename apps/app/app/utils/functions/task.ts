"use client";

import { resetTask, useTaskStore } from "@/app/utils/stores/task";
import { disconnectSocket } from "@utils/socket";
import { useRecorderStore } from "@utils/stores/recorder";
import { resetWebview } from "@utils/stores/website-preview";

export async function openTask() {
  const { task } = useTaskStore.getState();

  if (!task.currentWorkspace) {
    console.error("No current workspace found");
    return;
  }
}

export async function requestNewTask(
  gitRepoId: number,
  workspaceName: string,
  issueNumber: number | undefined,
  token: string,
): Promise<{
  success: boolean;
  message?: string;
  taskId?: string;
}> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/repos/entries/workspace/create_task`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        git_repo_id: gitRepoId,
        workspace_name: workspaceName,
        issue_number: issueNumber,
      }),
    },
  );

  if (response.ok) {
    const result = await response.json();
    if (result.success) {
      return { success: true, taskId: result.task_id };
    } else {
      return { success: false, message: result.message };
    }
  }

  return {
    success: false,
    message: `Failed to get added repo. Server responded with: ${response.status}`,
  };
}

export async function deleteTask(
  gitRepoId: number,
  taskId: string,
  token: string,
): Promise<{
  success: boolean;
}> {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/repos/entries/tasks/remove/${gitRepoId}/${taskId}`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return { success: data.success };
  } catch (error) {
    console.error("Error deleting task:", error);
    return { success: false };
  }
}

export async function closeTask() {
  const { setCurrentWorkspace } = useTaskStore.getState();
  const { resetRecorder } = useRecorderStore.getState();

  disconnectSocket();
  setCurrentWorkspace(null);
  resetWebview();

  resetRecorder();

  resetTask();
}
