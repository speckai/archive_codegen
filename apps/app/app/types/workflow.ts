import { Plan } from "./modifications";

export enum WorkflowState {
  IDLE = 0,
  CHAT_SENT = 1,
  CHAT_RECEIVED = 2,
  ASKING_QUESTION = 3,
  CREATING_NEW_PROMPT = 4,
  SEARCHING_CODE = 5,
  WRITING_PLAN = 6,
  IMPLEMENTING_PLAN = 7,
  VALIDATING_CHANGES = 8,
  FIXING_RUNTIME = 9,
  DONE = 10,
}

export interface Workflow {
  // Initial messages
  workflowState: WorkflowState;

  // Planner
  plan?: Plan;
}
