import { useTaskStore } from "@/app/utils/stores/task";
import { useToast } from "@chakra-ui/react";
import Cookies from "js-cookie";
import { useEffect, useState } from "react";
import io, { Socket } from "socket.io-client";
import { createSocketCallback } from "./socket-callback";

let socket: Socket | null = null;
let isCallbacksSet = false;
let retryCount = 0;
const MAX_RETRIES = 3;

const socketStatusEvent = new EventTarget();

export const connectSocket = (
  token: string,
  taskId: string,
  toast: Function,
  isPreview: boolean = false,
) => {
  if (socket) {
    return;
  }

  const socketUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!socketUrl || typeof socketUrl !== "string") {
    console.error("NEXT_PUBLIC_API_URL is not defined or not a string");
    return;
  }

  const setupSocket = (workerAuth = {}) => {
    try {
      const workerCookie = Cookies.get("speck_worker_id");
      const headers: Record<string, string> = {};
      if (workerCookie) {
        headers["X-Worker-ID"] = workerCookie;
      }

      socket = io(socketUrl, {
        auth: {
          HTTP_AUTHORIZATION: `${token}`,
          is_preview: isPreview,
          ...workerAuth,
        },
        withCredentials: true,
        transports: ["websocket", "polling"],
        extraHeaders: headers,
        reconnection: true,
        reconnectionAttempts: 3,
        timeout: 10000,
      });

      socket.on("connect", () => {
        retryCount = 0;
        socket?.emit("initialize", {
          task_id: taskId,
          is_preview: isPreview,
        });

        socketStatusEvent.dispatchEvent(
          new CustomEvent("socketStatus", { detail: true }),
        );
      });

      socket.on("disconnect", () => {
        const socketCallback = createSocketCallback(toast);

        for (const event of socket?.receiveBuffer || []) {
          socketCallback(socket, {
            message_type: event[1].message_type,
            data: event[1].data,
          });
        }

        socketStatusEvent.dispatchEvent(
          new CustomEvent("socketStatus", { detail: false }),
        );
      });

      socket.on("connect_error", (error) => {
        console.error("Socket connection error:", error);
        toast({
          title: "Connection Error",
          description: "Failed to connect to server",
          status: "error",
        });
      });

      socket.on("worker_redirect", (data: { worker_id: string }) => {
        console.log("Redirecting to worker:", data.worker_id);
        if (retryCount >= MAX_RETRIES) {
          console.error("Max worker redirect retries reached");
          return;
        }
        retryCount++;

        disconnectSocket();
        setupSocket({ worker_id: data.worker_id });
        setupSocketCallbacks(toast);
      });
    } catch (error) {
      console.error("Error setting up socket:", error);
    }

    return socket;
  };

  return setupSocket();
};

export const disconnectSocket = () => {
  if (socket) {
    isCallbacksSet = false;
    socket.disconnect();
    socket = null;
  }
};

export const useSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const { addNewMessage } = useTaskStore();
  const toast = useToast();

  useEffect(() => {
    const handleSocketStatus = (event: Event) => {
      const customEvent = event as CustomEvent;
      setIsConnected(customEvent.detail);
    };

    socketStatusEvent.addEventListener("socketStatus", handleSocketStatus);

    if (socket) {
      setupSocketCallbacks(toast);
    }

    return () => {
      socketStatusEvent.removeEventListener("socketStatus", handleSocketStatus);
    };
  }, [addNewMessage]);

  const emit = (eventName: string, data: any) => {
    if (socket) {
      socket.emit(eventName, data);
    }
  };

  return { isConnected, emit };
};

export const setupSocketCallbacks = (toast: Function) => {
  if (isCallbacksSet || !socket) {
    return;
  }

  const socketCallback = createSocketCallback(toast);

  socket.onAny((eventName, ...args) => {
    if (socket) {
      socketCallback(socket, { eventType: eventName, ...args[0] });
    }
  });

  isCallbacksSet = true;
};
