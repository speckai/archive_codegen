class ScreenRecorder {
  constructor() {
    this.isRecording = false;
    this.isReplaying = false;
    this.recordingStartTime = null;

    this.recordingDuration = null;
    this.initialUrl = null;
    this.currentActionIndex = -1;
    this.lastActionTarget = null;
    this.lastSelectedComponent = null;

    this.events = [];
    this.lastEventTime = null;
    this.lastEventTimeTaken = 0;
    this.hasLoadedModernScreenshot = false;
    this.modernScreenshotScript = null;
    this.firstInputTime = null;
    this.consoleLogs = [];
    this.originalConsole = {
      log: console.log,
      warn: console.warn,
      error: console.error,
      info: console.info,
      debug: console.debug,
    };
    this.originalFetch = window.fetch;

    this.lastScrollEvent = null;
    this.lastScrollDirection = null;
    this.accumulatedScrollDelay = 0;
    this.scrollTimeout = null;
    this.scrollDebounceDelay = 500; // Wait 500ms after last scroll event
    this.scrollStartTime = null;

    // Add a way to track processed events to prevent infinite replay loops
    this.processedEventIndices = new Set();

    this.setupEventListeners();
    this.setupMessageListener();
    this.setupConsoleCapture();

    // Add beforeunload event listener to capture navigation events
    window.addEventListener("beforeunload", this.handleBeforeUnload.bind(this));

    window.parent.postMessage({ type: "request_recording_state" }, "*");

    this.checkForRecordingAfterRefresh();
    this.checkForReplayAfterRefresh();

    this.loadModernScreenshot();
  }

  // Method to handle beforeunload event (page navigation/refresh)
  handleBeforeUnload(event) {
    // Save current recording state to sessionStorage before page unloads
    if (this.isRecording && this.events.length > 0) {
      // Re-set the start recording flag to preserve recording state across navigation
      sessionStorage.setItem("screenRecorderStartRecording", "true");

      console.log(
        "[TIMING DEBUG] Before unload, saving events timing:",
        this.events.map((e) => ({
          type: e.type,
          delay: e.delay,
          timestamp: e.timestamp,
        })),
      );

      const serializedEvents = JSON.stringify(
        this.sanitizeEventsForSerialization(this.events),
      );
      sessionStorage.setItem("screenRecorderEvents", serializedEvents);

      if (this.consoleLogs && this.consoleLogs.length > 0) {
        const serializedLogs = JSON.stringify(this.consoleLogs);
        sessionStorage.setItem("screenRecorderConsoleLogs", serializedLogs);
      }

      sessionStorage.setItem(
        "screenRecorderLastEventTime",
        String(this.lastEventTime || 0),
      );
      sessionStorage.setItem(
        "screenRecorderRecordingStartTime",
        String(this.recordingStartTime),
      );
    }
  }

  checkForReplayAfterRefresh() {
    // Check for the general replay flag
    const shouldReplayAfterRefresh = sessionStorage.getItem(
      "screenRecorderReplayAfterRefresh",
    );

    // Also check for the in-progress replay flag
    const replayInProgress = sessionStorage.getItem(
      "screenRecorderReplayInProgress",
    );

    // Check for processed event indices to prevent looping
    const processedIndices = sessionStorage.getItem(
      "screenRecorderProcessedEventIndices",
    );

    console.log("[REPLAY] checkForReplayAfterRefresh called", {
      shouldReplayAfterRefresh,
      replayInProgress,
      hasProcessedIndices: !!processedIndices,
    });

    // Either flag should trigger replay continuation
    if (shouldReplayAfterRefresh === "true" || replayInProgress === "true") {
      // Remove the first flag but not the in-progress flag yet
      sessionStorage.removeItem("screenRecorderReplayAfterRefresh");

      const waitForPageLoad = () => {
        return new Promise((resolve) => {
          if (document.readyState === "complete") {
            setTimeout(resolve, 500);
          } else {
            window.addEventListener("load", () => {
              setTimeout(resolve, 500);
            });
          }
        });
      };

      waitForPageLoad().then(() => {
        try {
          const serializedEvents = sessionStorage.getItem(
            "screenRecorderEvents",
          );
          if (serializedEvents) {
            // Debug the events from sessionStorage
            const parsedEvents = JSON.parse(serializedEvents);
            console.log(
              "[REPLAY STORAGE DEBUG] Events from sessionStorage:",
              parsedEvents.map((e) => ({
                type: e.type,
                delay: e.delay,
                timestamp: e.timestamp,
                hasTimestampProperty: e.hasOwnProperty("timestamp"),
                timestampType: typeof e.timestamp,
              })),
            );

            this.events = parsedEvents;
            console.log("[REPLAY] Restored events for replay", {
              count: this.events.length,
            });
            // Don't remove events yet - might need them for further navigation
          }

          const serializedLogs = sessionStorage.getItem(
            "screenRecorderConsoleLogs",
          );
          if (serializedLogs) {
            this.consoleLogs = JSON.parse(serializedLogs);
            // Don't remove logs yet
          }

          // Restore initial URL from the replay-specific storage key
          const replayInitialUrl = sessionStorage.getItem(
            "screenRecorderReplayInitialUrl",
          );
          if (replayInitialUrl) {
            console.log(
              "[REPLAY] Restored original recording's initial URL:",
              replayInitialUrl,
            );
            this.initialUrl = replayInitialUrl;
          }

          // Restore processed event indices
          if (processedIndices) {
            try {
              this.processedEventIndices = new Set(
                JSON.parse(processedIndices),
              );
              console.log("[REPLAY] Restored processed event indices", {
                count: this.processedEventIndices.size,
              });
            } catch (e) {
              console.error(
                "[REPLAY] Error parsing processed event indices:",
                e,
              );
              this.processedEventIndices = new Set();
            }
          } else {
            this.processedEventIndices = new Set();
          }

          setTimeout(() => {
            this.startReplayAfterRefresh();
          }, 1000);
        } catch (error) {
          console.error(
            "[REPLAY] Failed to restore events from sessionStorage:",
            error,
          );
        }
      });
    }
  }

  startReplayAfterRefresh() {
    console.log("[REPLAY] startReplayAfterRefresh called", {
      eventsCount: this.events.length,
    });

    if (this.events.length === 0) {
      console.log("[REPLAY] No events to replay, aborting");
      return;
    }

    // Check if we were in the middle of replaying and navigated to a new page
    const replayIndex = sessionStorage.getItem("screenRecorderReplayIndex");
    let eventIndex = 0;

    if (replayIndex) {
      eventIndex = parseInt(replayIndex, 10);
      console.log("[REPLAY] Resuming replay from event index:", eventIndex);
      sessionStorage.removeItem("screenRecorderReplayIndex");
    }

    // Skip to the first unprocessed event if we're starting from the beginning
    if (eventIndex === 0 && this.processedEventIndices.size > 0) {
      // Find the highest processed index
      const maxProcessedIndex = Math.max(
        ...Array.from(this.processedEventIndices),
      );
      if (maxProcessedIndex >= 0) {
        eventIndex = maxProcessedIndex + 1;
        console.log(
          "[REPLAY] Skipping to first unprocessed event:",
          eventIndex,
        );
      }
    }

    // Check if we've already processed all events
    if (eventIndex >= this.events.length) {
      console.log("[REPLAY] All events already processed, finishing replay");
      this.finishReplay();
      return;
    }

    this.replayInProgress = true;
    window.parent.postMessage({ type: "start_replay" }, "*");
    this.notifyStateChange();

    this.lastScrollEvent = null;
    this.lastScrollDirection = null;
    this.accumulatedScrollDelay = 0;

    this.currentActionIndex = eventIndex > 0 ? eventIndex - 1 : -1;
    this.notifyStateChange();

    let currentDuration = 0;

    // Log event timings before starting replay
    console.log("[TIMING DEBUG] Events at start of replay:");
    this.events.forEach((event, index) => {
      console.log(
        `  [${index}] ${event.type}: delay=${event.delay}, timestamp=${event.timestamp}`,
      );
    });

    const processNextEvent = () => {
      console.log("[REPLAY] processNextEvent", {
        eventIndex,
        totalEvents: this.events.length,
        replayInProgress: this.replayInProgress,
        processedCount: this.processedEventIndices.size,
      });

      if (!this.replayInProgress || eventIndex >= this.events.length) {
        console.log("[REPLAY] Finished replaying all events or replay stopped");
        this.finishReplay();
        return;
      }

      // Skip already processed events to prevent loops
      if (this.processedEventIndices.has(eventIndex)) {
        console.log("[REPLAY] Skipping already processed event:", eventIndex);
        eventIndex++;
        processNextEvent();
        return;
      }

      const event = this.events[eventIndex];
      const nextEvent = this.events[eventIndex + 1];

      this.currentActionIndex = eventIndex;
      this.notifyStateChange();

      window.parent.postMessage(
        {
          type: "replay_action",
          data: eventIndex,
        },
        "*",
      );

      console.log("[TIMING DEBUG] Processing event in replay:", {
        index: eventIndex,
        type: event.type,
        delay: event.delay,
        timestamp: event.timestamp,
        currentDuration,
      });

      currentDuration += event.delay || 0;
      if (this.recordingDuration > 0) {
        const progress = (currentDuration / this.recordingDuration) * 100;
        window.parent.postMessage(
          {
            type: "replay_progress",
            data: { progress },
          },
          "*",
        );
      }

      // Mark this event as processed to prevent infinite loops
      this.processedEventIndices.add(eventIndex);
      // Save processed indices to sessionStorage
      try {
        sessionStorage.setItem(
          "screenRecorderProcessedEventIndices",
          JSON.stringify(Array.from(this.processedEventIndices)),
        );
      } catch (e) {
        console.error("[REPLAY] Error saving processed event indices:", e);
      }

      eventIndex++;

      // Check if this is a navigation event
      if (event.url && event.url !== window.location.href) {
        // Set all flags needed for proper continuation after navigation
        console.log(
          "[REPLAY] Navigation event detected, saving state for:",
          event.url,
        );

        // Save the current replay position and state
        sessionStorage.setItem(
          "screenRecorderReplayIndex",
          eventIndex.toString(),
        );
        sessionStorage.setItem("screenRecorderReplayInProgress", "true");
        sessionStorage.setItem("screenRecorderReplayAfterRefresh", "true");

        // Log current event timings before navigation
        console.log("[TIMING DEBUG] Event timings before navigation:");
        this.events.forEach((e, i) => {
          console.log(
            `  [${i}] ${e.type}: delay=${e.delay}, timestamp=${e.timestamp}`,
          );
        });

        // Navigate to the new URL
        window.location.href = event.url;
        return;
      }

      const handleNextEvent = (success) => {
        console.log("[REPLAY] handleNextEvent called", {
          success,
          nextEventIndex: eventIndex,
          hasNextEvent: !!nextEvent,
        });

        if (nextEvent) {
          let { delay } = nextEvent;
          delay = Math.max(delay, 100);
          console.log("[REPLAY] Scheduling next event", {
            delay,
            nextType: nextEvent.type,
          });
          setTimeout(processNextEvent, delay);
        } else {
          console.log("[REPLAY] No more events to replay, finishing");
          this.finishReplay();
        }
      };

      // Handle the current event
      try {
        const result = this.replayEvent(event);
        if (result instanceof Promise) {
          result.then(handleNextEvent).catch((error) => {
            console.error("[REPLAY] Error in promise from replayEvent:", error);
            handleNextEvent(false);
          });
        } else {
          handleNextEvent(result);
        }
      } catch (error) {
        console.error("[REPLAY] Error in processNextEvent:", error);
        handleNextEvent(false);
      }
    };

    processNextEvent();
  }

  setupConsoleCapture() {
    const extractErrorInfo = (args) => {
      const errorArg = args.find((arg) => arg instanceof Error);
      if (errorArg) {
        const stack = errorArg.stack?.split("\n").map((line) => line.trim());
        return {
          message: errorArg.message || String(errorArg),
          stack: stack || [],
          error: errorArg,
        };
      }
      return null;
    };

    const formatOutput = (args) => {
      return args
        .map((arg) => {
          if (arg instanceof Error) {
            const errorObj = {
              message: arg.message,
              name: arg.name,
              stack: arg.stack,
            };
            if (arg instanceof TypeError) {
              errorObj.type = "TypeError";
            }
            return JSON.stringify(errorObj, null, 2);
          }
          if (typeof arg === "object") {
            try {
              return JSON.stringify(arg, null, 2);
            } catch (e) {
              return String(arg);
            }
          }
          return String(arg);
        })
        .join(" ");
    };

    window.fetch = async (...args) => {
      const startTime = Date.now();
      try {
        const response = await this.originalFetch.apply(window, args);
        if (!response.ok) {
          const timestamp = startTime - this.recordingStartTime;
          const url = typeof args[0] === "string" ? args[0] : args[0].url;
          const error = new Error(`HTTP error! status: ${response.status}`);
          error.status = response.status;
          error.url = url;

          const stack = error.stack
            ?.split("\n")
            .map((line) => line.trim())
            .filter((line) => !line.includes("recorder.js"));

          if (this.isRecording && stack?.length > 0) {
            this.consoleLogs.push({
              timestamp,
              level: "error",
              output: `Fetch error: ${url} returned ${response.status}`,
              traceback: stack,
            });
          }
        }
        return response;
      } catch (error) {
        const timestamp = startTime - this.recordingStartTime;
        const stack = error.stack
          ?.split("\n")
          .map((line) => line.trim())
          .filter((line) => !line.includes("recorder.js"));

        if (this.isRecording && stack?.length > 0) {
          this.consoleLogs.push({
            timestamp,
            level: "error",
            output: `Network error: ${error.message}`,
            traceback: stack,
          });
        }
        throw error;
      }
    };

    const originalMethods = {
      log: window.console.log,
      warn: window.console.warn,
      error: window.console.error,
      info: window.console.info,
      debug: window.console.debug,
    };

    Object.keys(originalMethods).forEach((level) => {
      const originalMethod = originalMethods[level];

      console[level] = new Proxy(originalMethod, {
        apply: (target, thisArg, args) => {
          const result = Reflect.apply(target, thisArg, args);

          if (this.isRecording) {
            const timestamp = Date.now() - this.recordingStartTime;
            const errorInfo = extractErrorInfo(args);

            if (errorInfo) {
              const stack = errorInfo.stack.filter(
                (line) => !line.includes("recorder.js"),
              );
              if (stack.length > 0) {
                this.consoleLogs.push({
                  timestamp,
                  level,
                  output: errorInfo.message,
                  traceback: stack,
                });
              }
            } else {
              const error = new Error();
              const stack = error.stack
                ?.split("\n")
                .slice(2)
                .map((line) => line.trim())
                .filter((line) => !line.includes("recorder.js"));

              if (stack && stack.length > 0) {
                this.consoleLogs.push({
                  timestamp,
                  level,
                  output: formatOutput(args),
                  traceback: stack,
                });
              }
            }
          }

          return result;
        },
      });
    });
  }

  restoreConsole() {
    Object.keys(this.originalConsole).forEach((method) => {
      console[method] = this.originalConsole[method];
    });
    if (window.fetch !== this.originalFetch) {
      window.fetch = this.originalFetch;
    }
  }

  setupMessageListener() {
    window.addEventListener("message", this.handleMessage.bind(this));
  }

  handleMessage(event) {
    const { type, data } = event.data;

    switch (type) {
      case "toggle_recording":
        this.toggleRecording();
        break;
      case "request_replay":
        this.replay();
        break;
      case "request_recording_data":
        if (this.events.length === 0) {
          return;
        }
        const recordingData = {
          events: this.sanitizeEventsForSerialization(this.events),
          initialUrl: this.initialUrl,
          duration: this.recordingDuration,
          viewportSize: {
            width: window.innerWidth,
            height: window.innerHeight,
          },
          consoleLogs: this.consoleLogs,
        };
        window.parent.postMessage(
          {
            type: "recording_data",
            data: recordingData,
          },
          "*",
        );
        break;
      case "save_recording":
        this.saveRecordingWithAnnotation(data.annotation);
        break;
      case "discard_recording":
        this.discardRecording();
        break;
      case "set_recording_data":
        console.log("[DEBUG] Setting recording data from parent", {
          hasEvents: !!data?.events,
          eventsCount: data?.events?.length || 0,
          hasLogs: !!data?.consoleLogs,
          initialUrl: data?.initialUrl,
        });
        if (data?.events) {
          this.events = data.events;
        }
        if (data?.consoleLogs) {
          this.consoleLogs = data.consoleLogs;
        }
        if (data?.initialUrl) {
          this.initialUrl = data.initialUrl;
          // Save the initial URL in a more permanent location for replay use
          sessionStorage.setItem(
            "screenRecorderOriginalInitialUrl",
            data.initialUrl,
          );
        }
        if (data?.duration) {
          this.recordingDuration = data.duration;
        }
        this.notifyStateChange();
        break;
      case "take_screenshot":
        this.takeScreenshot();
        break;
      case "take_forced_screenshot":
        this.takeForcedScreenshot();
        break;
      case "take_component_screenshot":
        this.takeComponentScreenshot();
        break;
      case "save_screenshot":
        this.saveScreenshot(data);
        break;
      case "save_component_selection":
        this.saveComponentSelection(data);
        break;
      case "cancel_forced_screenshot":
        this.restoreConsole();
        this.discardRecording();
        break;
      case "save_forced_screenshot":
        this.saveForcedScreenshot(data);
        break;
    }
  }

  setupEventListeners() {
    document.addEventListener("click", (e) => this.recordEvent("click", e));
    document.addEventListener(
      "input",
      (e) => this.recordEvent("input", e),
      true,
    );
    document.addEventListener(
      "scroll",
      (e) => {
        if (this.isRecording && !this.isReplaying) {
          if (!this.scrollStartTime) {
            this.scrollStartTime = Date.now();
          }
          if (this.scrollTimeout) {
            clearTimeout(this.scrollTimeout);
          }
          this.scrollTimeout = setTimeout(() => {
            this.recordEvent("scroll", e);
            this.scrollStartTime = null;
          }, this.scrollDebounceDelay);
        }
      },
      true,
    );

    document.addEventListener(
      "change",
      (e) => this.recordEvent("change", e),
      true,
    );
    document.addEventListener(
      "submit",
      (e) => this.recordEvent("submit", e),
      true,
    );
  }

  recordEvent(type, event) {
    if (!this.isRecording || this.isReplaying) {
      return;
    }

    // Double-check to make sure we're not in replay mode
    const replayInProgress = sessionStorage.getItem(
      "screenRecorderReplayInProgress",
    );
    if (replayInProgress === "true") {
      console.log("[DEBUG] Ignoring event during replay:", type);
      return;
    }

    console.log("[DEBUG] Recording event:", type, {
      url: window.location.href,
      target: event.target.tagName,
      eventsCount: this.events.length,
    });

    const currentTime = Date.now();
    const delay = this.lastEventTime
      ? currentTime - this.lastEventTime - this.lastEventTimeTaken
      : 0;

    console.log("[TIMING DEBUG] Recording event timing:", {
      type,
      currentTime,
      lastEventTime: this.lastEventTime,
      lastEventTimeTaken: this.lastEventTimeTaken,
      calculatedDelay: delay,
      recordingStartTime: this.recordingStartTime,
    });

    this.lastEventTimeTaken = 0;

    const eventData = {
      type,
      delay: delay,
      timestamp: currentTime - this.recordingStartTime,
      target: {
        tagName: event.target.tagName,
      },
      url: window.location.href,
    };

    if (type === "click") {
      const rect = event.target.getBoundingClientRect();
      window.parent.postMessage(
        {
          type: "click_animation",
          data: {
            rect: {
              top: rect.top,
              left: rect.left,
              width: rect.width,
              height: rect.height,
            },
          },
        },
        "*",
      );
    }

    if (type === "input") {
      const lastEvent = this.events[this.events.length - 1];
      if (
        lastEvent &&
        lastEvent.type === "input" &&
        lastEvent.target.xpath === this.getXPath(event.target) &&
        event.target.value.startsWith(lastEvent.value)
      ) {
        lastEvent.value = event.target.value;
        lastEvent.target.value = event.target.value;
        lastEvent.timeTaken = currentTime - this.firstInputTime;
        this.lastEventTime = currentTime;
        this.notifyStateChange();
        return;
      } else {
        this.firstInputTime = currentTime;
      }
    }

    if (type === "scroll") {
      const currentScrollY = window.scrollY;
      const currentScrollX = window.scrollX;
      const scrollDuration = this.scrollStartTime
        ? currentTime - this.scrollStartTime
        : 0;

      this.events.push({
        type: "scroll",
        delay: scrollDuration,
        timestamp: currentTime - this.recordingStartTime,
        scrollX: parseInt(currentScrollX),
        scrollY: parseInt(currentScrollY),
        url: window.location.href,
        target: {
          tagName: "DOCUMENT",
        },
      });
      this.currentActionIndex = this.events.length - 1;
      this.lastEventTime = currentTime;
      this.notifyStateChange();
      return;
    } else if (this.lastScrollEvent !== null) {
      this.events.push(this.lastScrollEvent);
      this.lastScrollEvent = null;
      this.lastScrollDirection = null;
      this.accumulatedScrollDelay = 0;
    }

    let targetElement = event.target;

    if (type === "click" && !this.isClickable(targetElement)) {
      const clickableParent = this.findClosestClickableParent(targetElement);
      if (clickableParent) {
        targetElement = clickableParent;
      }
    }

    this.lastEventTime = currentTime;

    const targetForRecording = type === "click" ? targetElement : event.target;
    this.lastActionTarget = targetForRecording;

    const isElementAction = type !== "scroll";

    if (isElementAction) {
      let boundingBox = null;
      try {
        const rect = targetForRecording.getBoundingClientRect();
        boundingBox = {
          minX: rect.left + window.scrollX,
          minY: rect.top + window.scrollY,
          maxX: rect.right + window.scrollX,
          maxY: rect.bottom + window.scrollY,
          width: rect.width,
          height: rect.height,
          centerX: rect.left + window.scrollX + rect.width / 2,
          centerY: rect.top + window.scrollY + rect.height / 2,
        };
      } catch (error) {
        console.warn("Could not get bounding box for element:", error);
      }

      eventData.target = {
        ...eventData.target,
        id: targetForRecording.id,
        className: targetForRecording.className,
        name: targetForRecording.name,
        value: targetForRecording.value,
        checked: targetForRecording.checked,
        href: targetForRecording.href,
        xpath: this.getXPath(targetForRecording),
        cssSelector: this.getCssSelector(targetForRecording),
        html: targetForRecording.outerHTML,
        boundingBox: boundingBox,
        innerText:
          targetForRecording.innerText || targetForRecording.textContent || "",
      };
    }

    switch (type) {
      case "click":
      case "dblclick":
        eventData.button = event.button;
        break;

      case "input":
      case "change":
        eventData.value = event.target.value;
        eventData.checked = event.target.checked;
        eventData.timeTaken = 0;
        break;

      case "scroll":
        eventData.scrollX = window.scrollX;
        eventData.scrollY = window.scrollY;
        break;

      case "submit":
        event.preventDefault();
        break;
    }

    this.events.push(eventData);
    this.currentActionIndex = this.events.length - 1;
    this.notifyStateChange();

    console.log("[DEBUG] Event added, new count:", this.events.length, {
      type,
      url: window.location.href,
      timestamp: eventData.timestamp,
    });
  }

  notifyStateChange() {
    window.parent.postMessage(
      {
        type: "recording_state",
        data: {
          isRecording: this.isRecording,
          events: this.events,
          consoleLogs: this.consoleLogs,
          currentActionIndex: this.currentActionIndex,
          duration: this.recordingDuration,
        },
      },
      "*",
    );
  }

  getXPath(element) {
    if (!element) {
      return "";
    }
    if (element.id) {
      return `//*[@id="${element.id}"]`;
    }

    const paths = [];
    for (
      ;
      element && element.nodeType === Node.ELEMENT_NODE;
      element = element.parentNode
    ) {
      let index = 0;
      let hasFollowingSiblings = false;
      for (
        let sibling = element.previousSibling;
        sibling;
        sibling = sibling.previousSibling
      ) {
        if (sibling.nodeType === Node.DOCUMENT_TYPE_NODE) {
          continue;
        }
        if (sibling.nodeName === element.nodeName) {
          index++;
        }
      }
      for (
        let sibling = element.nextSibling;
        sibling && !hasFollowingSiblings;
        sibling = sibling.nextSibling
      ) {
        if (sibling.nodeName === element.nodeName) {
          hasFollowingSiblings = true;
        }
      }

      const tagName = element.nodeName.toLowerCase();
      const pathIndex = index || hasFollowingSiblings ? `[${index + 1}]` : "";
      paths.unshift(tagName + pathIndex);
    }

    return "/" + paths.join("/") || null;
  }

  getCssSelector(element) {
    if (!element) {
      return "";
    }

    const buildPath = (el) => {
      if (!el || el === document.documentElement) {
        return [];
      }

      let selector = el.tagName.toLowerCase();

      if (el.id) {
        return [`#${this.escapeCssSelector(el.id)}`];
      }

      if (
        el.className &&
        typeof el.className === "string" &&
        el.className.trim()
      ) {
        const classes = el.className.trim().split(/\s+/);
        if (classes.length > 0) {
          selector += "." + classes.join(".");
        }
      }

      if (el.name) {
        selector += `[name="${el.name}"]`;
      }

      if (el.href) {
        try {
          const url = new URL(el.href);
          selector += `[href*="${url.pathname}"]`;
        } catch (e) {
          selector += `[href="${el.href}"]`;
        }
      }

      if (el.type) {
        selector += `[type="${el.type}"]`;
      }

      const parent = el.parentElement;
      if (!parent || parent === document.documentElement) {
        return [selector];
      }

      const siblings = Array.from(parent.children);
      if (siblings.length > 1) {
        const index = siblings.indexOf(el) + 1;
        if (index > 0) {
          selector += `:nth-child(${index})`;
        }
      }

      return [...buildPath(parent), selector];
    };

    const path = buildPath(element);
    if (path.length === 0) {
      return element.tagName.toLowerCase();
    }

    if (path[0].startsWith("#")) {
      return path[0];
    }

    return path.join(" > ");
  }

  escapeCssSelector(str) {
    if (typeof str !== "string") {
      return "";
    }

    return str.replace(/([!"#$%&'()*+,./:;<=>?@[\\\]^`{|}~])/g, "\\$1");
  }

  findTargetElement(targetInfo) {
    if (!targetInfo) {
      return null;
    }

    // Handle case where tagName might be UNKNOWN but we have other selectors
    if (
      targetInfo.tagName === "UNKNOWN" &&
      !targetInfo.id &&
      !targetInfo.cssSelector &&
      targetInfo.className
    ) {
      try {
        const classNames = targetInfo.className.split(" ").filter((c) => c);
        if (classNames.length > 0) {
          const selector =
            "." + classNames.map((c) => this.escapeCssSelector(c)).join(".");
          const elements = document.querySelectorAll(selector);
          if (elements.length > 0) {
            return elements[0];
          }
        }
      } catch (e) {
        console.error("Error finding element by className:", e);
      }
    }

    if (
      !targetInfo.tagName &&
      !targetInfo.id &&
      !targetInfo.cssSelector &&
      !targetInfo.className
    ) {
      return null;
    }

    let foundElement = null;

    if (!foundElement && targetInfo.id) {
      try {
        const escapedId = this.escapeCssSelector(targetInfo.id);
        const element = document.querySelector(`#${escapedId}`);
        if (element) {
          foundElement = element;
        }
      } catch (e) {
        console.error("Error finding element by ID:", e);
        const element = document.getElementById(targetInfo.id);
        if (element) {
          foundElement = element;
        }
      }
    }

    if (!foundElement && targetInfo.cssSelector) {
      try {
        let safeSelector = targetInfo.cssSelector;
        if (safeSelector.includes("#")) {
          safeSelector = safeSelector.replace(
            /(#[^:\s\[\]]+)(:[\w-]+):/g,
            function (match, id, colon) {
              return `${id}\\${colon}\\:`;
            },
          );
        }

        const elements = document.querySelectorAll(safeSelector);
        if (elements.length > 0) {
          foundElement = elements[0];
        }
      } catch (e) {
        console.error("Invalid CSS selector:", targetInfo.cssSelector, e);
      }
    }

    if (!foundElement && targetInfo.xpath) {
      try {
        const isTextNode = targetInfo.tagName === "TEXT";
        const xpath = isTextNode
          ? targetInfo.xpath.replace(/\/text$/, "")
          : targetInfo.xpath;

        const result = document.evaluate(
          xpath,
          document,
          null,
          XPathResult.FIRST_ORDERED_NODE_TYPE,
          null,
        );

        if (result.singleNodeValue) {
          if (isTextNode) {
            foundElement = result.singleNodeValue;
          } else {
            foundElement = result.singleNodeValue;
          }
        }
      } catch (e) {
        console.error("Invalid XPath:", targetInfo.xpath, e);
      }
    }

    if (
      !foundElement &&
      targetInfo.tagName &&
      (targetInfo.innerText || targetInfo.textContent)
    ) {
      const textToMatch = (
        targetInfo.innerText || targetInfo.textContent
      ).trim();

      if (targetInfo.tagName === "TEXT") {
        const allElements = document.querySelectorAll("*");
        for (let i = 0; i < allElements.length; i++) {
          if ((allElements[i].textContent || "").trim() === textToMatch) {
            foundElement = allElements[i];
            break;
          }
        }
      } else {
        const elements = document.getElementsByTagName(targetInfo.tagName);
        for (let i = 0; i < elements.length; i++) {
          const elementText = (elements[i].textContent || "").trim();
          if (elementText === textToMatch) {
            foundElement = elements[i];
            break;
          }
        }
      }
    }

    if (!foundElement && targetInfo.boundingBox) {
      const { centerX, centerY } = targetInfo.boundingBox;

      try {
        const elementAtPoint = document.elementFromPoint(centerX, centerY);
        if (elementAtPoint) {
          foundElement = elementAtPoint;
        }
      } catch (e) {
        console.error("Error finding element at point:", e);
      }
    }

    if (foundElement && !this.isClickable(foundElement)) {
      const clickableParent = this.findClosestClickableParent(foundElement);
      if (clickableParent) {
        foundElement = clickableParent;
      }
    }

    return foundElement;
  }

  isClickable(element) {
    if (!element) {
      return false;
    }

    const clickableTags = [
      "A",
      "BUTTON",
      "INPUT",
      "SELECT",
      "TEXTAREA",
      "LABEL",
      "SUMMARY",
    ];

    if (clickableTags.includes(element.tagName)) {
      return true;
    }

    const clickableRoles = [
      "button",
      "link",
      "checkbox",
      "radio",
      "menuitem",
      "tab",
      "switch",
    ];
    if (
      element.getAttribute("role") &&
      clickableRoles.includes(element.getAttribute("role"))
    ) {
      return true;
    }

    if (
      element.onclick ||
      element.getAttribute("onclick") ||
      element.onmousedown ||
      element.getAttribute("onmousedown")
    ) {
      return true;
    }

    return false;
  }

  findClosestClickableParent(element) {
    let currentElement = element;

    while (currentElement && !this.isClickable(currentElement)) {
      currentElement = currentElement.parentElement;
    }

    return currentElement;
  }

  toggleRecording() {
    if (this.isRecording) {
      this.stopRecording();
    } else {
      this.startRecording();
    }
  }

  startRecording() {
    console.log("[DEBUG] Starting recording");
    this.isRecording = true;
    this.events = [];
    this.consoleLogs = [];
    this.recordingStartTime = Date.now();
    this.lastEventTime = null;
    this.initialUrl = window.location.href;

    console.log("[DEBUG] Setting initial URL for recording:", this.initialUrl);

    // Store the initial URL in a more persistent location
    sessionStorage.setItem("screenRecorderOriginalInitialUrl", this.initialUrl);

    this.setupConsoleCapture();

    console.log(
      "[DEBUG] Saving recording state to sessionStorage before reload",
      {
        initialUrl: this.initialUrl,
        recordingStartTime: this.recordingStartTime,
      },
    );

    sessionStorage.setItem("screenRecorderStartRecording", "true");
    sessionStorage.setItem("screenRecorderInitialUrl", this.initialUrl);
    sessionStorage.setItem(
      "screenRecorderRecordingStartTime",
      String(this.recordingStartTime),
    );

    // Clear any existing events when starting a new recording
    sessionStorage.removeItem("screenRecorderEvents");
    sessionStorage.removeItem("screenRecorderConsoleLogs");

    // Refresh the page
    console.log("[DEBUG] Reloading page to start fresh recording");
    window.location.reload();
  }

  stopRecording() {
    console.log("[DEBUG] Stopping recording", {
      eventsCount: this.events.length,
    });

    if (this.lastScrollEvent !== null) {
      this.events.push(this.lastScrollEvent);
      this.lastScrollEvent = null;
      this.lastScrollDirection = null;
      this.accumulatedScrollDelay = 0;
    }

    const hasMeaningfulEvents = this.events.length > 0;

    let timeFromLastAction = 0;
    if (hasMeaningfulEvents && this.lastEventTime) {
      timeFromLastAction = Date.now() - this.lastEventTime;
    }

    this.events.push({
      type: "terminate",
      delay: timeFromLastAction,
      url: window.location.href,
    });

    this.lastEventTime = null;

    if (!hasMeaningfulEvents) {
      this.events = [];
      this.consoleLogs = [];
      this.recordingDuration = null;
      this.isRecording = false;

      // Clean up all sessionStorage flags
      sessionStorage.removeItem("screenRecorderStartRecording");
      sessionStorage.removeItem("screenRecorderEvents");
      sessionStorage.removeItem("screenRecorderConsoleLogs");
      sessionStorage.removeItem("screenRecorderLastEventTime");
      sessionStorage.removeItem("screenRecorderRecordingStartTime");

      window.parent.postMessage({ type: "recording_stopped" }, "*");
      this.notifyStateChange();
      return;
    }

    // Check if the last meaningful event was a screenshot or component selection
    if (!this.lastEventWasScreenshotOrComponent()) {
      // If not, we need to take a forced screenshot before stopping the recording
      window.parent.postMessage({ type: "require_screenshot" }, "*");
      // Don't set isRecording to false yet, as we still need to handle the screenshot
    } else {
      // If the last event was already a screenshot or component selection, finish normally
      this.isRecording = false;
      const recordingEndTime = Date.now();
      this.recordingDuration = recordingEndTime - this.recordingStartTime;
      this.restoreConsole();

      // Clean up all sessionStorage flags
      sessionStorage.removeItem("screenRecorderStartRecording");
      sessionStorage.removeItem("screenRecorderEvents");
      sessionStorage.removeItem("screenRecorderConsoleLogs");
      sessionStorage.removeItem("screenRecorderLastEventTime");
      sessionStorage.removeItem("screenRecorderRecordingStartTime");

      window.parent.postMessage({ type: "recording_stopped" }, "*");
      this.notifyStateChange();
    }
  }

  lastEventWasScreenshotOrComponent() {
    // Check if there are any events
    if (this.events.length === 0) {
      return false;
    }

    // Look for the last non-terminate event
    for (let i = this.events.length - 1; i >= 0; i--) {
      const event = this.events[i];
      if (event.type !== "terminate") {
        return (
          event.type === "screenshot" || event.type === "component_selection"
        );
      }
    }

    return false;
  }

  takeForcedScreenshot() {
    // This is similar to takeScreenshot but with a different result type
    try {
      if (!window.modernScreenshot) {
        console.error(
          "window.modernScreenshot is not defined even after loading",
        );
        return;
      }

      try {
        window.modernScreenshot
          .domToWebp(document.documentElement, {
            width: window.innerWidth,
            height: window.innerHeight,
            features: {
              restoreScrollPosition: true,
            },
          })
          .then((dataUrl) => {
            const scrollPosition = {
              x: parseInt(window.scrollX),
              y: parseInt(window.scrollY),
            };

            window.parent.postMessage(
              {
                type: "forced_screenshot_result",
                data: dataUrl,
                scrollPosition,
              },
              "*",
            );
          });
      } catch (error) {
        console.error("Error taking forced screenshot:", error);
      }
    } catch (outerError) {
      console.error("Outer error in takeForcedScreenshot:", outerError);
    }
  }

  saveForcedScreenshot(data) {
    // Save the screenshot
    const now = Date.now();
    const delay = this.lastEventTime
      ? now - this.lastEventTime - this.lastEventTimeTaken
      : 0;

    this.events.push({
      type: "screenshot",
      delay,
      timestamp: now - this.recordingStartTime,
      url: window.location.href,
      annotation: data.annotation,
      imageData: data.imageData,
      scrollPosition: {
        x: parseInt(window.scrollX),
        y: parseInt(window.scrollY),
      },
      viewportSize: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
    });

    // Now complete the recording process
    this.isRecording = false;
    this.recordingDuration = now - this.recordingStartTime;
    this.restoreConsole();

    // Send the recording data for annotation
    const recordingData = {
      events: this.sanitizeEventsForSerialization(this.events),
      initialUrl: this.initialUrl,
      duration: this.recordingDuration,
      viewportSize: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
      consoleLogs: this.consoleLogs,
    };

    window.parent.postMessage(
      {
        type: "recording_data_with_screenshot",
        data: recordingData,
        annotation: data.annotation,
      },
      "*",
    );

    this.notifyStateChange();
  }

  saveRecordingWithAnnotation(annotation) {
    if (this.events.length === 0) {
      console.warn("No events to save");
      return;
    }

    const data = {
      events: this.sanitizeEventsForSerialization(this.events),
      initialUrl: this.initialUrl,
      duration: this.recordingDuration,
      viewportSize: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
      consoleLogs: this.consoleLogs,
      annotation: annotation,
      systemInfo: {
        operatingSystem: navigator.userAgentData.platform,
        userAgent: navigator.userAgent,
      },
    };

    window.parent.postMessage(
      {
        type: "save_recording",
        data,
      },
      "*",
    );

    this.events = [];
    this.consoleLogs = [];
    this.currentActionIndex = -1;
    this.recordingDuration = null;
    this.notifyStateChange();
  }

  discardRecording() {
    this.events = [];
    this.consoleLogs = [];
    this.currentActionIndex = -1;
    this.isRecording = false;
    this.recordingDuration = null;

    window.parent.postMessage({ type: "recording_discarded" }, "*");
    this.notifyStateChange();
  }

  sanitizeEventsForSerialization(events) {
    const sanitizedEvents = events.map((event) => {
      const cleanEvent = {
        type: event.type,
        delay: event.delay || 0,
        timestamp: event.timestamp, // Make sure to preserve timestamp
        url: event.url,
        target: event.target,
      };

      if (!event.target) {
        event.target = {
          tagName: "UNKNOWN",
        };
      }

      if (event.type === "terminate") {
        return cleanEvent;
      }

      const targetProps = {
        tagName: event.target.tagName,
      };

      const optionalTargetProps = [
        "id",
        "className",
        "name",
        "value",
        "checked",
        "href",
        "xpath",
        "cssSelector",
        "boundingBox",
        "innerText",
      ];

      optionalTargetProps.forEach((prop) => {
        if (event.target[prop] !== undefined) {
          if (prop === "className" && typeof event.target[prop] !== "string") {
            targetProps[prop] = event.target[prop]?.baseVal || "";
          } else {
            targetProps[prop] = event.target[prop];
          }
        }
      });

      cleanEvent.target = targetProps;

      const optionalEventProperties = [
        "button",
        "key",
        "code",
        "shiftKey",
        "ctrlKey",
        "altKey",
        "metaKey",
        "timeTaken",
        "value",
        "checked",
        "scrollX",
        "scrollY",
        "annotation",
        "viewportSize",
        "scrollPosition",
        "component",
        // Ensure timestamp is properly included
        "timestamp",
      ];

      optionalEventProperties.forEach((property) => {
        if (event[property] !== undefined) {
          cleanEvent[property] = event[property];
        }
      });
      return cleanEvent;
    });

    return sanitizedEvents;
  }

  replay() {
    if (this.isReplaying) {
      if (window.currentReplayCleanup) {
        window.currentReplayCleanup();
        window.currentReplayCleanup = null;
      }
      this.replayInProgress = false;
      this.isReplaying = false;
      this.notifyStateChange();
      return;
    }

    if (this.events.length === 0) {
      return;
    }

    if (this.isRecording) {
      this.isRecording = false;
    }

    // Ensure we have the correct initial URL before starting the replay
    // Check if we have the original URL from when recording started
    const originalInitialUrl = sessionStorage.getItem(
      "screenRecorderOriginalInitialUrl",
    );
    if (originalInitialUrl) {
      this.initialUrl = originalInitialUrl;
    } else if (!this.initialUrl) {
      // If no initialUrl is set, use the first event URL or current URL as fallback
      this.initialUrl =
        (this.events[0] && this.events[0].url) || window.location.href;
    }

    this.isReplaying = true;
    this.replayInProgress = true;
    window.parent.postMessage({ type: "start_replay" }, "*");
    this.notifyStateChange();

    this.lastScrollEvent = null;
    this.lastScrollDirection = null;
    this.accumulatedScrollDelay = 0;

    let totalDuration = 0;
    this.events.forEach((event, index) => {
      totalDuration += event.delay || 0;
    });

    const skipIndices = new Set();
    for (let i = 0; i < this.events.length - 2; i++) {
      if (
        i + 2 < this.events.length &&
        this.events[i].type === "mousedown" &&
        this.events[i + 1].type === "mouseup" &&
        this.events[i + 2].type === "click"
      ) {
        skipIndices.add(i);
        skipIndices.add(i + 1);
      }
    }

    const displayIndices = [];
    this.events.forEach((event, index) => {
      if (!skipIndices.has(index)) {
        displayIndices.push(index);
      }
    });

    this.currentActionIndex = -1;
    this.notifyStateChange();

    sessionStorage.setItem("screenRecorderReplayAfterRefresh", "true");
    sessionStorage.setItem("screenRecorderReplayInProgress", "true");

    sessionStorage.setItem("screenRecorderReplayInitialUrl", this.initialUrl);

    sessionStorage.removeItem("screenRecorderStartRecording");

    try {
      const preSanitizedEvents = JSON.parse(JSON.stringify(this.events));

      const sanitizedEvents = this.sanitizeEventsForSerialization(this.events);

      // Compare events before and after sanitization
      console.log(
        "[COMPARE DEBUG] Events comparison before/after sanitization:",
      );
      for (
        let i = 0;
        i < Math.min(preSanitizedEvents.length, sanitizedEvents.length);
        i++
      ) {
        console.log(`  Event ${i} (${preSanitizedEvents[i].type}):`);
        console.log(
          `    - Before: delay=${preSanitizedEvents[i].delay}, timestamp=${preSanitizedEvents[i].timestamp}`,
        );
        console.log(
          `    - After:  delay=${sanitizedEvents[i].delay}, timestamp=${sanitizedEvents[i].timestamp}`,
        );

        if (preSanitizedEvents[i].timestamp !== sanitizedEvents[i].timestamp) {
          console.log(`    *** TIMESTAMP CHANGED OR LOST! ***`);
        }
      }

      console.log("[TIMING DEBUG] Sanitized events for replay:");
      sanitizedEvents.forEach((event, index) => {
        console.log(
          `  [${index}] ${event.type}: delay=${event.delay}, timestamp=${event.timestamp}, hasTimestamp=${event.hasOwnProperty("timestamp")}`,
        );
      });

      // Examine the JSON stringification process
      const serializedEventsStr = JSON.stringify(sanitizedEvents);
      const parsedBackEvents = JSON.parse(serializedEventsStr);

      console.log("[STRINGIFY DEBUG] Events after JSON stringify and parse:");
      parsedBackEvents.forEach((event, index) => {
        console.log(
          `  [${index}] ${event.type}: delay=${event.delay}, timestamp=${event.timestamp}, hasTimestamp=${event.hasOwnProperty("timestamp")}`,
        );
      });

      // Now check if the issue is in storing to sessionStorage
      sessionStorage.setItem("screenRecorderEvents", serializedEventsStr);
      const retrievedEvents = JSON.parse(
        sessionStorage.getItem("screenRecorderEvents"),
      );

      console.log("[STORAGE DEBUG] Events after sessionStorage save/retrieve:");
      retrievedEvents.forEach((event, index) => {
        console.log(
          `  [${index}] ${event.type}: delay=${event.delay}, timestamp=${event.timestamp}, hasTimestamp=${event.hasOwnProperty("timestamp")}`,
        );
      });

      if (this.consoleLogs && this.consoleLogs.length > 0) {
        const serializedLogs = JSON.stringify(this.consoleLogs);
        sessionStorage.setItem("screenRecorderConsoleLogs", serializedLogs);
      }
    } catch (error) {
      console.error(
        "[REPLAY] Failed to store events in sessionStorage:",
        error,
      );
    }

    // Check if we're already on the correct URL to avoid unnecessary navigation
    if (window.location.href !== this.initialUrl) {
      // Use the original recording's initial URL for navigation, not the current URL
      console.log(
        "[REPLAY] Navigating to original recording's initial URL:",
        this.initialUrl,
      );
      window.location.href = this.initialUrl;
      // Don't reload if we're already navigating to a new URL
    } else {
      console.log(
        "[REPLAY] Already on the correct URL, starting replay immediately",
      );
      // If we're already on the right page, we need to simulate a reload to start the replay
      this.startReplayAfterRefresh();
    }
  }

  replayEvent(event) {
    console.log("[REPLAY] Replaying event", { type: event.type });
    try {
      switch (event.type) {
        case "click":
        case "dblclick": {
          const element = this.findTargetElement(event.target);
          if (element) {
            const rect = element.getBoundingClientRect();
            window.parent.postMessage(
              {
                type: "click_animation",
                data: {
                  rect: {
                    top: rect.top,
                    left: rect.left,
                    width: rect.width,
                    height: rect.height,
                  },
                },
              },
              "*",
            );

            const mouseEvent = new MouseEvent(event.type, {
              bubbles: true,
              cancelable: true,
              view: window,
              button: event.button,
              buttons: event.button === 0 ? 1 : event.button === 1 ? 4 : 2,
            });
            element.dispatchEvent(mouseEvent);
            return true;
          } else {
            console.warn(
              `[REPLAY] Could not find target element for ${event.type} event:`,
              event.target,
            );
            return false;
          }
        }

        case "input": {
          const element = this.findTargetElement(event.target);
          if (!element) {
            console.warn(
              `[REPLAY] Could not find target element for input event:`,
              event.target,
            );
            return false;
          }

          if (element.type === "checkbox" || element.type === "radio") {
            element.checked = event.target.checked;
            element.dispatchEvent(new Event("input", { bubbles: true }));
            return true;
          }

          const targetValue = event.value || "";
          const timeTaken = event.timeTaken || 1000; // Default to 1 second

          return new Promise((resolve) => {
            element.focus();
            element.dispatchEvent(new Event("focus", { bubbles: true }));

            const descriptor = Object.getOwnPropertyDescriptor(
              HTMLInputElement.prototype,
              "value",
            );
            const originalSetter = descriptor ? descriptor.set : null;

            if (originalSetter) {
              originalSetter.call(element, "");
            } else {
              element.value = "";
            }
            element.dispatchEvent(new Event("input", { bubbles: true }));

            let currentIndex = 0;
            const charCount = targetValue.length;
            const delayPerChar = Math.max(
              20,
              Math.floor(timeTaken / charCount),
            );

            const typeNextChar = () => {
              if (currentIndex >= charCount) {
                try {
                  if (element._valueTracker) {
                    element._valueTracker.setValue("");
                  }
                } catch (e) {}

                setTimeout(() => {
                  element.blur();
                  element.dispatchEvent(new Event("blur", { bubbles: true }));
                  resolve(true);
                }, 100);

                return;
              }

              const currentChar = targetValue[currentIndex];
              const currentText = targetValue.slice(0, currentIndex + 1);

              if (originalSetter) {
                originalSetter.call(element, currentText);
              } else {
                element.value = currentText;
              }

              element.dispatchEvent(new Event("input", { bubbles: true }));

              const keyCode = currentChar.charCodeAt(0);

              try {
                element.dispatchEvent(
                  new KeyboardEvent("keydown", {
                    key: currentChar,
                    code: `Key${currentChar.toUpperCase()}`,
                    keyCode,
                    which: keyCode,
                    bubbles: true,
                    cancelable: true,
                  }),
                );

                element.dispatchEvent(
                  new KeyboardEvent("keypress", {
                    key: currentChar,
                    code: `Key${currentChar.toUpperCase()}`,
                    keyCode,
                    which: keyCode,
                    bubbles: true,
                    cancelable: true,
                  }),
                );

                element.dispatchEvent(
                  new KeyboardEvent("keyup", {
                    key: currentChar,
                    code: `Key${currentChar.toUpperCase()}`,
                    keyCode,
                    which: keyCode,
                    bubbles: true,
                    cancelable: true,
                  }),
                );
              } catch (e) {
                console.error("[REPLAY] Error dispatching keyboard events:", e);
              }

              currentIndex++;
              setTimeout(typeNextChar, delayPerChar);
            };

            console.log("[REPLAY] Starting input typing", {
              targetValue,
              timeTaken,
            });
            setTimeout(typeNextChar, 100);
          });
        }

        case "change": {
          const element = this.findTargetElement(event.target);
          if (!element) {
            console.warn(
              `[REPLAY] Could not find target element for change event:`,
              event.target,
            );
            return false;
          }

          if (element.type === "checkbox" || element.type === "radio") {
            element.checked = event.target.checked;
            element.dispatchEvent(new Event("change", { bubbles: true }));
            return true;
          }

          const targetValue = event.value || "";

          const descriptor = Object.getOwnPropertyDescriptor(
            HTMLInputElement.prototype,
            "value",
          );
          const originalSetter = descriptor ? descriptor.set : null;

          if (originalSetter) {
            originalSetter.call(element, targetValue);
          } else {
            element.value = targetValue;
          }

          try {
            if (element._valueTracker) {
              element._valueTracker.setValue("");
            }
          } catch (e) {}

          element.dispatchEvent(new Event("change", { bubbles: true }));
          return true;
        }

        case "scroll": {
          const duration = event.delay;
          console.log("[REPLAY] Scrolling", {
            scrollX: event.scrollX,
            scrollY: event.scrollY,
            duration,
          });
          this.smoothScrollTo(
            parseInt(event.scrollX),
            parseInt(event.scrollY),
            duration,
          );
          return true;
        }

        case "screenshot": {
          console.log("[REPLAY] Handling screenshot event");
          const screenshotMessage = document.createElement("div");
          screenshotMessage.className = "replay-screenshot-annotation";
          screenshotMessage.style.position = "fixed";
          screenshotMessage.style.top = "50%";
          screenshotMessage.style.left = "50%";
          screenshotMessage.style.transform = "translate(-50%, -50%)";
          screenshotMessage.style.backgroundColor = "rgba(0, 0, 0, 0.75)";
          screenshotMessage.style.color = "white";
          screenshotMessage.style.padding = "12px 16px";
          screenshotMessage.style.borderRadius = "12px";
          screenshotMessage.style.zIndex = "9999";
          screenshotMessage.style.maxWidth = "300px";
          screenshotMessage.style.textAlign = "left";
          screenshotMessage.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.15)";
          screenshotMessage.style.transition = "opacity 0.3s ease-out";
          screenshotMessage.style.fontFamily =
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif";
          screenshotMessage.style.fontSize = "14px";
          screenshotMessage.style.lineHeight = "1.4";
          screenshotMessage.style.border =
            "1px dashed rgba(255, 255, 255, 0.2)";
          screenshotMessage.style.backdropFilter = "blur(4px)";

          const annotation = event.annotation || "";
          const truncatedAnnotation =
            annotation.length > 20
              ? annotation.substring(0, 20) + "..."
              : annotation;

          screenshotMessage.innerHTML = `
            <div style="font-weight: 600; margin-bottom: 4px;">Screenshot Taken</div>
            <div style="display: flex; align-items: center;">
              <div style="margin-right: 8px; font-size: 16px;">
                <svg aria-hidden="true" focusable="false" width="16" height="16" style="vertical-align: -0.125em;" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
                  <path fill="currentColor" d="M149.1 64.8L138.7 96H64C28.7 96 0 124.7 0 160V416c0 35.3 28.7 64 64 64H448c35.3 0 64-28.7 64-64V160c0-35.3-28.7-64-64-64H373.3L362.9 64.8C356.4 45.2 338.1 32 317.4 32H194.6c-20.7 0-39 13.2-45.5 32.8zM256 384c-53 0-96-43-96-96s43-96 96-96s96 43 96 96s-43 96-96 96z"></path>
                </svg>
              </div>
              <div style="font-size: 13px; opacity: 0.9;">${truncatedAnnotation}</div>
            </div>
          `;

          document.body.appendChild(screenshotMessage);

          const flashElement = document.createElement("div");
          flashElement.style.position = "fixed";
          flashElement.style.top = "0";
          flashElement.style.left = "0";
          flashElement.style.width = "100%";
          flashElement.style.height = "100%";
          flashElement.style.backgroundColor = "white";
          flashElement.style.opacity = "0.2";
          flashElement.style.zIndex = "9998";
          flashElement.style.pointerEvents = "none";
          flashElement.style.transition = "opacity 0.2s ease-out";
          document.body.appendChild(flashElement);

          const cleanupFunctions = [];

          cleanupFunctions.push(() => {
            if (document.body.contains(flashElement)) {
              document.body.removeChild(flashElement);
            }
          });

          cleanupFunctions.push(() => {
            if (document.body.contains(screenshotMessage)) {
              document.body.removeChild(screenshotMessage);
            }
          });

          window.currentReplayCleanup = () => {
            cleanupFunctions.forEach((cleanup) => cleanup());
          };

          setTimeout(() => {
            flashElement.style.opacity = "0";
            setTimeout(() => {
              cleanupFunctions[0]();
            }, 300);
          }, 50);

          const duration = Math.max(event.delay || 2000, 2000);
          console.log("[REPLAY] Screenshot event will finish in", { duration });
          setTimeout(() => {
            screenshotMessage.style.opacity = "0";
            setTimeout(() => {
              cleanupFunctions[1]();
              window.currentReplayCleanup = null;
              console.log("[REPLAY] Screenshot event completed");
            }, 300);
          }, duration - 300);

          return Promise.resolve(true);
        }

        case "component_selection": {
          console.log("[REPLAY] Handling component_selection event");
          const componentElement = document.createElement("div");
          componentElement.className = "replay-component-annotation";
          componentElement.style.position = "absolute";
          componentElement.style.backgroundColor = "rgba(0, 0, 0, 0.85)";
          componentElement.style.color = "white";
          componentElement.style.padding = "6px 10px";
          componentElement.style.borderRadius = "4px";
          componentElement.style.zIndex = "10000";
          componentElement.style.maxWidth = "calc(100% - 16px)";
          componentElement.style.textAlign = "left";
          componentElement.style.boxShadow = "0 2px 8px rgba(0, 0, 0, 0.2)";
          componentElement.style.transition = "opacity 0.3s ease-out";
          componentElement.style.fontFamily =
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif";
          componentElement.style.backdropFilter = "blur(4px)";
          componentElement.style.border = "1px solid rgba(255, 255, 255, 0.1)";
          componentElement.style.fontSize = "11px";
          componentElement.style.lineHeight = "1.3";
          componentElement.style.whiteSpace = "normal";
          componentElement.style.wordBreak = "break-word";
          componentElement.style.pointerEvents = "none";

          let componentName = "";
          if (event.component && event.component.componentName) {
            componentName = event.component.componentName;
          }

          componentElement.innerHTML = `
            ${componentName ? `<div style="font-weight: 600; font-size: 12px; margin-bottom: 2px;">${componentName}</div>` : ""}
            <div style="font-size: 11px; opacity: 0.9;">${event.annotation || "Component selected"}</div>
          `;

          document.body.appendChild(componentElement);

          let highlightElement = null;
          let targetElement = null;

          const cleanupFunctions = [];

          cleanupFunctions.push(() => {
            if (document.body.contains(componentElement)) {
              document.body.removeChild(componentElement);
            }
          });

          if (event.target) {
            targetElement = this.findTargetElement(event.target);
          }

          if (
            !targetElement &&
            event.component &&
            event.component.htmlClassName
          ) {
            const selector = `.${event.component.htmlClassName.replace(/ /g, ".")}`;
            targetElement = document.querySelector(selector);
          }

          if (targetElement) {
            highlightElement = document.createElement("div");
            highlightElement.className = "replay-component-highlight";
            highlightElement.style.position = "absolute";
            highlightElement.style.transition = "all 0.3s ease-out";

            const updateHighlightPosition = () => {
              const rect = targetElement.getBoundingClientRect();
              highlightElement.style.top = `${rect.top + window.scrollY}px`;
              highlightElement.style.left = `${rect.left + window.scrollX}px`;
              highlightElement.style.width = `${rect.width}px`;
              highlightElement.style.height = `${rect.height}px`;

              componentElement.style.top = `${rect.top + window.scrollY + 2}px`;
              componentElement.style.left = `${rect.left + window.scrollX + 2}px`;
              componentElement.style.transform = "none";
            };

            updateHighlightPosition();
            highlightElement.style.border = "2px dashed #0066ff";
            highlightElement.style.boxSizing = "border-box";
            highlightElement.style.pointerEvents = "none";
            highlightElement.style.zIndex = "9998";
            highlightElement.style.backgroundColor = "rgba(0, 102, 255, 0.05)";
            highlightElement.style.boxShadow =
              "0 0 0 2px rgba(0, 102, 255, 0.2)";
            highlightElement.style.borderRadius = "2px";

            document.body.appendChild(highlightElement);

            window.addEventListener("scroll", updateHighlightPosition);
            window.addEventListener("resize", updateHighlightPosition);

            cleanupFunctions.push(() => {
              if (document.body.contains(highlightElement)) {
                document.body.removeChild(highlightElement);
              }
              window.removeEventListener("scroll", updateHighlightPosition);
              window.removeEventListener("resize", updateHighlightPosition);
            });
          }

          window.currentReplayCleanup = () => {
            cleanupFunctions.forEach((cleanup) => cleanup());
          };

          const duration = Math.max(event.delay || 2000, 2000);
          console.log("[REPLAY] Component selection will finish in", {
            duration,
          });
          setTimeout(() => {
            componentElement.style.opacity = "0";
            if (highlightElement) {
              highlightElement.style.opacity = "0";
            }
            setTimeout(() => {
              cleanupFunctions.forEach((cleanup) => cleanup());
              window.currentReplayCleanup = null;
              console.log("[REPLAY] Component selection event completed");
            }, 300);
          }, duration - 300);

          return Promise.resolve(true);
        }

        case "terminate": {
          console.log("[REPLAY] Handling terminate event - should end replay");
          // The terminate event is the last one, so we can immediately signal we're done
          setTimeout(() => {
            console.log("[REPLAY] Terminate event completed, ending replay");
            if (this.replayInProgress) {
              this.finishReplay();
            }
          }, 500);
          return true;
        }
      }
    } catch (error) {
      console.error("[REPLAY] Error replaying event:", error);
      return false;
    }
  }

  finishReplay() {
    console.log("[REPLAY] finishReplay called", {
      replayInProgress: this.replayInProgress,
      isReplaying: this.isReplaying,
    });

    // Log detailed event timings after replay is complete
    console.log("[TIMING DEBUG] Detailed event timings at end of replay:");
    this.events.forEach((event, index) => {
      console.log(
        `  [${index}] ${event.type}: delay=${event.delay}, timestamp=${event.timestamp}, hasTimestamp=${event.hasOwnProperty("timestamp")}, timestampType=${typeof event.timestamp}`,
      );
    });

    if (window.currentReplayCleanup) {
      console.log("[REPLAY] Executing cleanup function");
      window.currentReplayCleanup();
      window.currentReplayCleanup = null;
    }

    // Make sure we reset all replay state
    this.replayInProgress = false;
    this.isReplaying = false;
    this.currentActionIndex = -1;
    this.processedEventIndices.clear();

    // Notify parent window that replay is finished
    console.log("[REPLAY] Sending replay_finished message to parent");
    window.parent.postMessage({ type: "replay_finished" }, "*");
    this.notifyStateChange();

    // Clean up ALL sessionStorage
    sessionStorage.removeItem("screenRecorderReplayAfterRefresh");
    sessionStorage.removeItem("screenRecorderReplayIndex");
    sessionStorage.removeItem("screenRecorderReplayInProgress");
    sessionStorage.removeItem("screenRecorderReplayInitialUrl");
    // Do NOT remove screenRecorderOriginalInitialUrl as it should persist between replays
    sessionStorage.removeItem("screenRecorderEvents");
    sessionStorage.removeItem("screenRecorderConsoleLogs");
    sessionStorage.removeItem("screenRecorderProcessedEventIndices");

    console.log("[REPLAY] Replay finished completely");
  }

  smoothScrollTo(x, y, duration) {
    const startX = window.scrollX || window.pageXOffset;
    const startY = window.scrollY || window.pageYOffset;
    const distanceX = x - startX;
    const distanceY = y - startY;

    if (distanceX === 0 && distanceY === 0) {
      return;
    }

    if (duration < 50) {
      window.scrollTo(x, y);
      return;
    }

    const startTime = performance.now();

    const easeInOutCubic = (t) => {
      return t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1;
    };

    const scroll = () => {
      const currentTime = performance.now();
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeProgress = easeInOutCubic(progress);

      window.scrollTo(
        startX + distanceX * easeProgress,
        startY + distanceY * easeProgress,
      );

      if (progress < 1) {
        requestAnimationFrame(scroll);
      }
    };

    requestAnimationFrame(scroll);
  }

  async loadModernScreenshot() {
    if (this.hasLoadedModernScreenshot) {
      return true;
    }

    return new Promise((resolve) => {
      const script = document.createElement("script");
      script.src = "https://unpkg.com/modern-screenshot@4.6.0/dist/index.js";
      document.getElementsByTagName("head")[0].appendChild(script);

      script.onload = () => {
        this.hasLoadedModernScreenshot = true;
        this.modernScreenshotScript = script;

        if (
          typeof window.modernScreenshot === "undefined" &&
          typeof modernScreenshot !== "undefined"
        ) {
          window.modernScreenshot = modernScreenshot;
        }
        resolve(true);
      };

      script.onerror = (error) => {
        console.error("Failed to load modern-screenshot:", error);
        resolve(false);
      };
    });
  }

  async takeScreenshot() {
    try {
      if (!window.modernScreenshot) {
        console.error(
          "window.modernScreenshot is not defined even after loading",
        );
        return;
      }

      try {
        const dataUrl = await window.modernScreenshot.domToWebp(
          document.documentElement,
          {
            width: window.innerWidth,
            height: window.innerHeight,
            features: {
              restoreScrollPosition: true,
            },
          },
        );
        const scrollPosition = {
          x: parseInt(window.scrollX),
          y: parseInt(window.scrollY),
        };

        window.parent.postMessage(
          {
            type: "screenshot_result",
            data: dataUrl,
            scrollPosition,
          },
          "*",
        );
      } catch (error) {
        console.error("Error taking screenshot:", error);
      }
    } catch (outerError) {
      console.error("Outer error in takeScreenshot:", outerError);
    }
  }

  async takeComponentScreenshot() {
    try {
      const selectedElement = document.querySelector(
        ".speck-selected-component",
      );
      if (!selectedElement) {
        console.error("No component selected");
        return;
      }

      if (!window.modernScreenshot) {
        console.error(
          "window.modernScreenshot is not defined even after loading",
        );
        return;
      }
      try {
        const dataUrl =
          await window.modernScreenshot.domToWebp(selectedElement);

        this.lastSelectedComponent = {
          element: selectedElement,
          target: {
            xpath: this.getXPath(selectedElement),
            cssSelector: this.getCssSelector(selectedElement),
            tagName: selectedElement.tagName,
            className: selectedElement.className,
            id: selectedElement.id,
          },
        };

        window.parent.postMessage(
          {
            type: "component_screenshot_result",
            data: dataUrl,
            target: this.lastSelectedComponent.target,
          },
          "*",
        );

        this.createComponentFlashEffect(selectedElement);
        selectedElement.classList.remove("speck-selected-component");
      } catch (error) {
        console.error("Error taking component screenshot:", error);
      }
    } catch (outerError) {
      console.error("Outer error in takeComponentScreenshot:", outerError);
    }
  }

  createComponentFlashEffect(element) {
    try {
      const rect = element.getBoundingClientRect();
      const flashElement = document.createElement("div");
      flashElement.style.position = "absolute";
      flashElement.style.top = rect.top + "px";
      flashElement.style.left = rect.left + "px";
      flashElement.style.width = rect.width + "px";
      flashElement.style.height = rect.height + "px";
      flashElement.style.backgroundColor = "white";
      flashElement.style.opacity = "0.3";
      flashElement.style.zIndex = "9999";
      flashElement.style.pointerEvents = "none";
      flashElement.style.transition = "opacity 0.3s ease-out";
      document.body.appendChild(flashElement);

      setTimeout(() => {
        flashElement.style.opacity = "0";
        setTimeout(() => {
          document.body.removeChild(flashElement);
        }, 300);
      }, 50);
    } catch (error) {
      console.error("Error creating component flash effect:", error);
    }
  }

  saveScreenshot(data) {
    if (!this.isRecording) {
      return;
    }

    const now = Date.now();
    const delay = this.lastEventTime
      ? now - this.lastEventTime - this.lastEventTimeTaken
      : 0;
    this.lastEventTime = now;
    this.lastEventTimeTaken = 0;

    this.events.push({
      type: "screenshot",
      delay,
      timestamp: now - this.recordingStartTime,
      url: window.location.href,
      annotation: data.annotation,
      imageData: data.imageData,
      scrollPosition: {
        x: parseInt(window.scrollX),
        y: parseInt(window.scrollY),
      },
      viewportSize: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
    });

    this.notifyStateChange();
  }

  saveComponentSelection(data) {
    if (!this.isRecording) {
      return;
    }

    const now = Date.now();
    const delay = this.lastEventTime
      ? now - this.lastEventTime - this.lastEventTimeTaken
      : 0;
    this.lastEventTime = now;
    this.lastEventTimeTaken = 0;

    const target = this.lastSelectedComponent?.target || { tagName: "UNKNOWN" };

    this.events.push({
      type: "component_selection",
      delay,
      timestamp: now - this.recordingStartTime,
      url: window.location.href,
      component: data.component,
      annotation: data.annotation,
      imageData: data.imageData,
      target: target,
    });

    this.lastSelectedComponent = null;

    this.notifyStateChange();
  }

  // Add a method to check if we should start recording after refresh
  checkForRecordingAfterRefresh() {
    const shouldStartRecording = sessionStorage.getItem(
      "screenRecorderStartRecording",
    );

    // First check if we're in replay mode - replay takes priority over recording
    const replayInProgress = sessionStorage.getItem(
      "screenRecorderReplayInProgress",
    );

    console.log("[DEBUG] checkForRecordingAfterRefresh", {
      shouldStartRecording,
      replayInProgress,
    });

    // Skip recording if we're in replay mode
    if (replayInProgress === "true") {
      console.log(
        "[DEBUG] Skipping recording restoration because replay is in progress",
      );
      return;
    }

    if (shouldStartRecording === "true") {
      // Check for saved events from previous navigation
      const serializedEvents = sessionStorage.getItem("screenRecorderEvents");
      if (serializedEvents) {
        console.log("[DEBUG] Found saved events in sessionStorage");
        try {
          const parsedEvents = JSON.parse(serializedEvents);
          console.log(
            "[TIMING DEBUG] Restored events timing from sessionStorage:",
            parsedEvents.map((e) => ({
              type: e.type,
              delay: e.delay,
              timestamp: e.timestamp,
            })),
          );

          this.events = parsedEvents;
          console.log("[DEBUG] Restored events count:", this.events.length);
          // Don't remove events from sessionStorage yet, in case of another navigation
        } catch (error) {
          console.error("[DEBUG] Error parsing saved events:", error);
          this.events = [];
        }
      } else {
        console.log("[DEBUG] No saved events found in sessionStorage");
      }

      // Check for saved console logs
      const serializedLogs = sessionStorage.getItem(
        "screenRecorderConsoleLogs",
      );
      if (serializedLogs) {
        try {
          this.consoleLogs = JSON.parse(serializedLogs);
          console.log(
            "[DEBUG] Restored console logs count:",
            this.consoleLogs.length,
          );
        } catch (error) {
          console.error("[DEBUG] Error parsing saved console logs:", error);
          this.consoleLogs = [];
        }
      }

      // Restore recording state
      this.isRecording = true;

      // Get saved recording start time or use current time
      const savedStartTime = sessionStorage.getItem(
        "screenRecorderRecordingStartTime",
      );
      this.recordingStartTime = savedStartTime
        ? parseInt(savedStartTime)
        : Date.now();

      console.log("[TIMING DEBUG] Restored recording start time:", {
        savedStartTime,
        parsedStartTime: this.recordingStartTime,
        currentTime: Date.now(),
        timeDiff: Date.now() - this.recordingStartTime,
      });

      // Get saved last event time if available
      const savedLastEventTime = sessionStorage.getItem(
        "screenRecorderLastEventTime",
      );
      this.lastEventTime = savedLastEventTime
        ? parseInt(savedLastEventTime)
        : null;

      console.log("[TIMING DEBUG] Restored last event time:", {
        savedLastEventTime,
        parsedLastEventTime: this.lastEventTime,
      });

      // Get the initial URL from storage - prioritize the original URL
      const originalUrl = sessionStorage.getItem(
        "screenRecorderOriginalInitialUrl",
      );
      const tempUrl = sessionStorage.getItem("screenRecorderInitialUrl");

      this.initialUrl = originalUrl || tempUrl || window.location.href;
      console.log("[DEBUG] Restored initial URL:", this.initialUrl);

      // Clear temporary URL, but keep the original URL
      sessionStorage.removeItem("screenRecorderInitialUrl");
      // We don't remove events and logs as we might need them for further navigation

      this.setupConsoleCapture();

      const initialScrollX = window.scrollX;
      const initialScrollY = window.scrollY;

      if (initialScrollX > 0 || initialScrollY > 0) {
        console.log("[DEBUG] Adding initial scroll event");
        this.events.push({
          type: "scroll",
          delay: 0,
          scrollX: initialScrollX,
          scrollY: initialScrollY,
          url: window.location.href,
        });
      }

      this.notifyStateChange();
      console.log("[DEBUG] Recording state restored after refresh", {
        eventsCount: this.events.length,
        isRecording: this.isRecording,
      });
    }
  }
}

let recorder = null;

function initScreenRecorder() {
  if (typeof window !== "undefined" && !recorder) {
    recorder = new ScreenRecorder();
    window.screenRecorder = recorder;
  }
  return recorder;
}

initScreenRecorder();
