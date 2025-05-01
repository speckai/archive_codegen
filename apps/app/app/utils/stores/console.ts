import { ConsoleOutput } from "@ctypes/terminal";
import { create } from "zustand";

interface ConsoleState {
  outputs: ConsoleOutput[];
  addOutput: (output: ConsoleOutput) => void;
  clearOutputs: () => void;
}
export const useConsoleStore = create<ConsoleState>((set) => ({
  outputs: [],
  addOutput: (output) =>
    set((state) => ({ outputs: [...state.outputs, output] })),
  clearOutputs: () => set({ outputs: [] }),
}));
