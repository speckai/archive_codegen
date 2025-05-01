import { create } from "zustand";

export type UserSettings = {};

export interface UserSettingsStore extends UserSettings {
  setUserSettings: (settings: Partial<UserSettings>) => void;
}

export const useUserSettingsStore = create<UserSettingsStore>()((set, get) => ({
  setUserSettings: (newSettings) => {
    set((state) => ({
      ...state,
      ...newSettings,
    }));
  },
}));
