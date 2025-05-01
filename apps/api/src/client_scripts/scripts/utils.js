class RedirectHandler {
  constructor() {
    this.baseUrl = null;
  }

  setupMessageListener() {
    console.log("Setting up message listener");
    window.addEventListener("message", this.handleSetBaseUrl.bind(this));
    window.parent.postMessage({ type: "redirecter_ready" }, "*");
  }

  handleSetBaseUrl(event) {
    console.log("Handling set base URL");
    console.log(event);
    const { type, data } = event.data;
    if (type === "set_base_url") {
      const { baseUrl } = data;
      console.log("Setting base URL to", baseUrl);
      this.baseUrl = baseUrl;
      this.setupRedirectInterception();
    }
  }

  setupRedirectInterception() {
    console.log("Setting up redirect interception");
    if (!this.baseUrl) return;

    // Intercept link clicks
    document.addEventListener("click", this.handleLinkClick.bind(this), true);

    // Intercept form submissions
    document.addEventListener("submit", this.handleFormSubmit.bind(this), true);

    // Override window.open
    this.overrideWindowOpen();

    // Override location changes
    this.overrideLocationChanges();
  }

  handleLinkClick(event) {
    const link = event.target.closest("a");
    if (!link || !link.href) return;

    if (this.isLocalhostUrl(link.href)) {
      event.preventDefault();
      const newUrl = this.replaceLocalhostWithBaseUrl(link.href);
      window.location.href = newUrl;
    }
  }

  handleFormSubmit(event) {
    const form = event.target;
    if (!form.action) return;

    if (this.isLocalhostUrl(form.action)) {
      event.preventDefault();
      const newAction = this.replaceLocalhostWithBaseUrl(form.action);
      form.action = newAction;
      form.submit();
    }
  }

  overrideWindowOpen() {
    const originalWindowOpen = window.open;
    const self = this;

    window.open = function (url, ...args) {
      if (url && self.isLocalhostUrl(url)) {
        url = self.replaceLocalhostWithBaseUrl(url);
      }
      return originalWindowOpen.call(this, url, ...args);
    };
  }

  overrideLocationChanges() {
    const self = this;

    // Override window.location methods
    const originalAssign = window.location.assign;
    window.location.assign = function (url) {
      if (self.isLocalhostUrl(url)) {
        return originalAssign.call(this, self.replaceLocalhostWithBaseUrl(url));
      }
      return originalAssign.call(this, url);
    };

    const originalReplace = window.location.replace;
    window.location.replace = function (url) {
      if (self.isLocalhostUrl(url)) {
        return originalReplace.call(
          this,
          self.replaceLocalhostWithBaseUrl(url),
        );
      }
      return originalReplace.call(this, url);
    };

    // Use a proxy to intercept direct assignments to location.href
    const originalDescriptor = Object.getOwnPropertyDescriptor(
      window.Location.prototype,
      "href",
    );
    Object.defineProperty(window.location, "href", {
      set(url) {
        if (self.isLocalhostUrl(url)) {
          originalDescriptor.set.call(
            this,
            self.replaceLocalhostWithBaseUrl(url),
          );
        } else {
          originalDescriptor.set.call(this, url);
        }
      },
      get() {
        return originalDescriptor.get.call(this);
      },
    });
  }

  isLocalhostUrl(url) {
    try {
      const urlObj = new URL(url);
      return (
        urlObj.hostname === "localhost" ||
        urlObj.hostname.match(/^localhost:\d+$/)
      );
    } catch (e) {
      return false;
    }
  }

  replaceLocalhostWithBaseUrl(url) {
    try {
      const originalUrl = new URL(url);
      const baseUrl = new URL(this.baseUrl);

      // Keep the path, search params, and hash from the original URL
      return `${baseUrl.origin}${originalUrl.pathname}${originalUrl.search}${originalUrl.hash}`;
    } catch (e) {
      return url;
    }
  }
}

function initRedirectHandler() {
  const redirectHandler = new RedirectHandler();
  redirectHandler.setupMessageListener();
}

initRedirectHandler();
