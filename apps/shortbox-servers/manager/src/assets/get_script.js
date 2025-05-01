(function () {
  try {
    // Safely post message to parent without directly accessing its properties
    window.postMessage({ type: "SANDBOX_READY", source: "sandbox" }, "*");

    // Instead of directly accessing parent, use a more secure approach
    if (window.parent !== window) {
      window.parent.postMessage(
        { type: "SANDBOX_READY", source: "sandbox" },
        "*",
      );
    }

    window.addEventListener("message", function (event) {
      // Always verify origin for security before processing messages
      // You can add specific origins to check against if needed
      // if (event.origin !== "allowed-origin") return;

      if (event.data && event.data.type === "INJECT_SCRIPT" && event.data.src) {
        const script = document.createElement("script");
        script.src = event.data.src;
        script.async = true;
        document.body.appendChild(script);
      }
    });
  } catch (e) {
    // Catch any security errors that might occur
    console.log("Sandbox script error:", e.message);
  }
})();
