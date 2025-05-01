function log(message) {
  // console.log("speck_script.js:", message);
}

function executeSpeckConnector() {
  let currentBoundingBox = null;
  let selectionModeEnabled = false;
  let endpoint = null;
  let taskId = null;
  let token = null;

  let storageState = {
    cookies: {},
    localStorage: {},
    sessionStorage: {},
  };

  const parseCookies = () => {
    return document.cookie.split(";").reduce((acc, cookie) => {
      const [key, value] = cookie.trim().split("=");
      if (key) {
        acc[key] = value;
      }
      return acc;
    }, {});
  };

  const getCurrentState = () => {
    const filterBannedKeys = (obj) => {
      const filteredObj = { ...obj };
      const bannedKeys = ["screenRecorderState", "screenReplayData"];

      bannedKeys.forEach((key) => {
        delete filteredObj[key];
      });

      return filteredObj;
    };

    return {
      cookies: parseCookies(),
      localStorage: filterBannedKeys({ ...localStorage }),
      sessionStorage: filterBannedKeys({ ...sessionStorage }),
    };
  };

  const checkStorageChanges = async () => {
    const currentState = getCurrentState();

    ["cookies", "localStorage", "sessionStorage"].forEach((type) => {
      const oldKeys = Object.keys(storageState[type]);
      const newKeys = Object.keys(currentState[type]);

      if (
        oldKeys.length !== newKeys.length ||
        oldKeys.some(
          (key) => storageState[type][key] !== currentState[type][key],
        )
      ) {
        // console.log(`${type} updated:`, currentState[type]);
      }
    });

    storageState = currentState;

    if (endpoint && token && taskId) {
      try {
        const response = await fetch(endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ task_id: taskId, state: storageState }),
        });
        if (!response.ok) {
          console.error("Failed to send storage state to endpoint");
        }
      } catch (error) {
        console.error("Error sending storage state:", error);
      }
    }
  };

  storageState = getCurrentState();

  window.addEventListener("storage", checkStorageChanges);
  setInterval(checkStorageChanges, 60000); // Check every minute (60000ms)

  /**
   * Send a URL message to the parent window.
   * @param {string} url
   */
  const sendUrlToParent = (url) => {
    const parsedUrl = new URL(url);
    const pathParts = parsedUrl.pathname.split("/").filter(Boolean);
    const previewIndex = pathParts.indexOf("preview");

    let normalizedPath = "/";
    if (previewIndex !== -1 && pathParts.length > previewIndex + 2) {
      const remainingParts = pathParts.slice(previewIndex + 3);
      if (remainingParts.length > 0) {
        normalizedPath = "/" + remainingParts.join("/");
      }
    }

    const normalizedUrl = new URL(url);
    normalizedUrl.pathname = normalizedPath;

    window.parent.postMessage(
      { type: "url", url: normalizedUrl.toString() },
      "*",
    );
  };

  const removeBoundingBox = () => {
    if (currentBoundingBox) {
      currentBoundingBox.style.opacity = "0";
    }
  };

  /**
   * Handler for incoming messages from the parent window.
   * @param {MessageEvent} event
   */
  const handleMessage = (event) => {
    const { type } = event.data;

    if (type === "components_selected") {
      const { data } = event.data;
      updateComponentOutlines(data);
    }

    if (type === "endpoint") {
      endpoint = event.data.data.endpoint;
      token = event.data.data.token;
      taskId = event.data.data.taskId;
      checkStorageChanges();
    }

    if (type === "select_component") {
      const { enabled } = event.data;
      selectionModeEnabled = enabled;
      if (!enabled) {
        removeBoundingBox();
        const selectedComponent = document.querySelector(
          ".speck-selected-component",
        );
        if (selectedComponent) {
          selectedComponent.classList.remove("speck-selected-component");
          selectedComponent.removeAttribute("data-component-name");
          selectedComponent.removeAttribute("data-file-path");
        }
      }
    }
  };

  /**
   * Retrieve React fiber info for an element and build its component hierarchy.
   * @param {HTMLElement} element
   * @returns {Promise<Object[] | null>}
   */
  const getComponentInfo = async (element) => {
    const reactFiberKey = Object.keys(element).find((key) =>
      key.startsWith("__reactFiber$"),
    );
    if (!reactFiberKey) {
      return null;
    }

    const fiberNode = element[reactFiberKey];

    if (fiberNode) {
      const componentHierarchy = [];
      let currentFiber = fiberNode;

      while (currentFiber) {
        if (currentFiber._debugSource) {
          let { fileName, lineNumber } = currentFiber._debugSource;

          // If the fileName has repo-####, remove the repo-### by finding the first / and removing up until that
          if (fileName.includes("repo-")) {
            const index = fileName.indexOf("repo-");
            const slashIndex = fileName.indexOf("/", index);
            fileName = fileName.substring(slashIndex + 1);
          }

          componentHierarchy.push({
            filePath: fileName,
            lineNumber: lineNumber,
            componentName: currentFiber.elementType?.name || null,
          });
        }
        currentFiber = currentFiber.return;
      }

      if (componentHierarchy.length === 0) {
        currentFiber = fiberNode;
        while (currentFiber) {
          const props =
            currentFiber.memoizedProps || currentFiber.pendingProps || {};
          const htmlTag =
            typeof currentFiber.type === "string" ? currentFiber.type : null;
          const htmlClassName = props.className;
          const htmlChildren =
            typeof props.children === "string" ? props.children : null;

          if (htmlTag) {
            componentHierarchy.push({
              noComponentInfo: true,
              filePath: "",
              lineNumber: -1,
              componentName: "",
              htmlClassName: htmlClassName,
              htmlTag: htmlTag,
              htmlChildren: htmlChildren,
            });
          }
          currentFiber = currentFiber.return;
        }
      }

      return componentHierarchy;
    }

    return null;
  };

  /**
   * Initialize all browser-level code for bounding boxes and component selection.
   */
  const initBrowserCode = () => {
    currentBoundingBox = null;

    /**
     * Create the bounding box that shows on hover.
     * @returns {HTMLDivElement}
     */
    const createHoverBoundingBox = () => {
      const box = document.createElement("div");
      box.style.cssText = `
        position: fixed;
        border: 1px dashed rgba(50, 120, 255, 0.8);
        border-radius: 2px;
        background-color: rgba(50, 100, 255, 0.1);
        pointer-events: none;
        z-index: 2147483647;
        transition: 
          top 0.15s cubic-bezier(0.4, 0, 0.2, 1),
          left 0.15s cubic-bezier(0.4, 0, 0.2, 1),
          width 0.15s cubic-bezier(0.4, 0, 0.2, 1) 0.04s,
          height 0.15s cubic-bezier(0.4, 0, 0.2, 1) 0.04s,
          opacity 0.15s cubic-bezier(0.4, 0, 0.2, 1);
        opacity: 0;
      `;
      document.body.appendChild(box);
      return box;
    };

    /**
     * Put the hover bounding box around a given element.
     * @param {HTMLElement} element
     */
    const updateBoundingBox = (element) => {
      if (!currentBoundingBox) {
        currentBoundingBox = createHoverBoundingBox();
      }
      const rect = element.getBoundingClientRect();
      currentBoundingBox.style.top = `${rect.top}px`;
      currentBoundingBox.style.left = `${rect.left}px`;
      currentBoundingBox.style.width = `${rect.width}px`;
      currentBoundingBox.style.height = `${rect.height}px`;
      currentBoundingBox.style.opacity = "1";
    };

    document.addEventListener("mouseover", async (event) => {
      if (!selectionModeEnabled) {
        return;
      }
      const element = event.target;
      try {
        updateBoundingBox(element);
      } catch (error) {
        console.error("Error updating bounding box:", error);
        removeBoundingBox();
      }
    });

    document.addEventListener("mouseout", () => {
      if (selectionModeEnabled) {
        return;
      }
      removeBoundingBox();
    });

    window.addEventListener("scroll", () => {
      const hoveredElement = document.querySelector(":hover");
      if (hoveredElement && selectionModeEnabled) {
        updateBoundingBox(hoveredElement);
      }
    });

    window.addEventListener("resize", () => {
      const hoveredElement = document.querySelector(":hover");
      if (hoveredElement && selectionModeEnabled) {
        updateBoundingBox(hoveredElement);
      }
    });

    document.addEventListener(
      "click",
      async (event) => {
        if (!selectionModeEnabled) {
          return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        const element = event.target;
        const prevSelectedComponent = document.querySelector(
          ".speck-selected-component",
        );
        if (prevSelectedComponent) {
          prevSelectedComponent.classList.remove("speck-selected-component");
        }

        const componentHierarchy = await getComponentInfo(element);

        if (componentHierarchy && componentHierarchy.length > 0) {
          element.setAttribute(
            "data-component-name",
            componentHierarchy[0].componentName || "",
          );
          element.setAttribute(
            "data-file-path",
            componentHierarchy[0].filePath || "",
          );

          element.classList.add("speck-selected-component");
          selectionModeEnabled = false;

          removeBoundingBox();

          window.parent.postMessage(
            {
              type: "component_selected",
              data: componentHierarchy[0],
            },
            "*",
          );
        } else {
          log("Component Info not found for the selected element.");
        }
      },
      true,
    );

    const handleLinkClicks = () => {
      document.addEventListener(
        "click",
        (event) => {
          const link = event.target.closest("a");
          if (link && link.target === "_blank") {
            event.preventDefault();
            link.target = "_self";
            link.click();
          }
        },
        true,
      );
    };

    const init = () => {
      if (document.readyState === "complete") {
        handleLinkClicks();
      } else {
        window.addEventListener("load", handleLinkClicks);
      }

      const observer = new MutationObserver(() => {
        handleLinkClicks();
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true,
      });

      handleLinkClicks();
    };

    init();
  };

  window.addEventListener("message", handleMessage);
  sendUrlToParent(window.location.href);

  if (typeof window !== "undefined") {
    initBrowserCode();
  }
}

/**
 * Draw outlines on elements that match the given selectedComponents data.
 * @param {Array} selectedComponents
 */
function updateComponentOutlines(selectedComponents) {
  const removedOutlines = document.querySelectorAll(".speck-component-outline");
  removedOutlines.forEach((el) => {
    if (el.resizeObserver) {
      el.resizeObserver.disconnect();
    }
    if (el.mutationObserver) {
      el.mutationObserver.disconnect();
    }
    window.removeEventListener("scroll", el.updatePosition);
    window.removeEventListener("resize", el.updatePosition);
    el.remove();
  });

  document.querySelectorAll("*").forEach((element) => {
    const reactFiberKey = Object.keys(element).find((key) =>
      key.startsWith("__reactFiber$"),
    );
    if (!reactFiberKey) {
      return;
    }

    const fiberNode = element[reactFiberKey];
    if (fiberNode) {
      let currentFiber = fiberNode;
      while (currentFiber) {
        if (currentFiber._debugSource) {
          const { fileName, lineNumber } = currentFiber._debugSource;
          const isSelected = selectedComponents.some(
            (selectedComponent) =>
              selectedComponent.file_path === fileName &&
              selectedComponent.line_number === lineNumber,
          );
          if (isSelected) {
            const box = document.createElement("div");
            box.classList.add("speck-component-outline");

            const updateBoxPosition = () => {
              const rect = element.getBoundingClientRect();
              box.style.cssText = `
                position: fixed;
                top: ${rect.top}px;
                left: ${rect.left}px;
                width: ${rect.width}px;
                height: ${rect.height}px;
                border: 1px dashed rgba(100, 100, 255, 0.5);
                background-color: rgba(100, 100, 255, 0.1);
                pointer-events: none;
                z-index: 2147483647;
              `;
            };

            updateBoxPosition();
            document.body.appendChild(box);

            const resizeObserver = new ResizeObserver(updateBoxPosition);
            resizeObserver.observe(element);

            const mutationObserver = new MutationObserver(updateBoxPosition);
            mutationObserver.observe(document.body, {
              childList: true,
              subtree: true,
            });

            window.addEventListener("scroll", updateBoxPosition);
            window.addEventListener("resize", updateBoxPosition);

            box.updatePosition = updateBoxPosition;
            box.resizeObserver = resizeObserver;
            box.mutationObserver = mutationObserver;
            return;
          }
        }
        currentFiber = currentFiber.return;
      }
    }
  });
}
