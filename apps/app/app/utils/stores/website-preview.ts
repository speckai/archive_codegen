import { create } from "zustand";

export type WebviewSettings = {
  iframeLastUpdated: number;
  url: string;
  domain: string;
  isLoading: boolean;
  history: string[];
  historyIndex: number;
  previewWidth: number;
  sandboxBaseUrl: string;
};

interface NavbarStoreProps extends WebviewSettings {
  setWebviewSettings: (settings: Partial<WebviewSettings>) => void;
  setSandboxBaseUrl: (ip: string) => void;
  setIsLoading: (isLoading: boolean) => void;
}

export const useWebviewStore = create<
  NavbarStoreProps & {
    getFullUrl: () => string;
    goBack: () => void;
    goForward: () => void;
    rerenderIframe: () => void;
    resetHistory: () => void;
    setUrl: (url: string) => void;
  }
>()((set, get) => ({
  iframeLastUpdated: 0, // To force rerender
  sandboxBaseUrl: "",
  url: "/",
  domain: "",

  isLoading: true,
  history: [],
  historyIndex: -1,
  previewWidth: 100,

  setWebviewSettings: (newSettings) => {
    set((state) => ({
      ...state,
      ...newSettings,
    }));
  },
  setSandboxBaseUrl: (baseUrl: string) => {
    set((state) => ({
      ...state,
      sandboxBaseUrl: baseUrl,
      iframeLastUpdated: state.iframeLastUpdated + 1, // Increment iframeLastUpdated
    }));
  },
  setIsLoading: (isLoading: boolean) => {
    set((state) => ({
      ...state,
      isLoading,
    }));
  },

  getFullUrl: () => {
    const { url, sandboxBaseUrl } = get();

    if (url.includes("http://") || url.includes("https://")) {
      return url;
    }

    let trimmedBaseUrl = sandboxBaseUrl.endsWith("/")
      ? sandboxBaseUrl.slice(0, -1)
      : sandboxBaseUrl;
    return `${trimmedBaseUrl}${url}`;
  },

  goBack: () => {
    const { url, history, historyIndex } = get();
    let newUrl = url;
    let newIndex = historyIndex;

    if (historyIndex > 0) {
      newUrl = history[historyIndex - 1];
      newIndex = historyIndex - 1;
    } else if (historyIndex === 0) {
      newUrl = "/";
      newIndex = -1;
    }

    set({
      url: newUrl,
      historyIndex: newIndex,
    });
  },

  goForward: () => {
    const { history, historyIndex } = get();
    const newIndex = historyIndex + 1;

    if (newIndex < history.length) {
      set({
        url: history[newIndex],
        historyIndex: newIndex,
      });
    }
  },

  rerenderIframe: () => {
    get().setWebviewSettings({ iframeLastUpdated: Date.now() });
  },

  resetHistory: () => {
    set({
      history: [],
      historyIndex: -1,
    });
  },

  setUrl: (url: string) => {
    set((state) => {
      const lastUrl = state.history[state.history.length - 1];
      if (lastUrl === url) {
        return { ...state, url };
      }

      return {
        ...state,
        url,
        history: [...state.history, url],
        historyIndex: state.historyIndex + 1,
      };
    });
  },
}));

export const resetWebview = () => {
  useWebviewStore.getState().setWebviewSettings({
    iframeLastUpdated: 0,
    sandboxBaseUrl: "",
    url: "/",
    domain: "",

    isLoading: true,
    history: [],
    historyIndex: -1,
    previewWidth: 100,
  });
};
