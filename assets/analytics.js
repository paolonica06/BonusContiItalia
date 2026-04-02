(function () {
  const CONFIG_PATH = "data/site-config.json";
  const DEBUG_QUERY = "analytics_debug";

  const state = {
    initialized: false,
    debug: false,
    queue: [],
  };

  function getPageContext() {
    const body = document.body || document.documentElement;
    return {
      page_type: body.dataset.pageType || "page",
      page_slug: body.dataset.pageSlug || "page",
      offer_slug: body.dataset.offerSlug || "",
    };
  }

  function sanitizeText(value) {
    return (value || "")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, 120);
  }

  function sanitizeParams(params) {
    const cleaned = {};
    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") {
        return;
      }
      cleaned[key] = String(value).slice(0, 100);
    });
    return cleaned;
  }

  function sendEvent(eventName, params) {
    let sent = false;

    if (typeof window.plausible === "function") {
      window.plausible(eventName, { props: params });
      sent = true;
    }

    if (typeof window.gtag === "function") {
      window.gtag("event", eventName, params);
      sent = true;
    }

    if (state.debug || !sent) {
      console.info("[bonuscontiitalia analytics]", eventName, params);
    }
  }

  function flushQueue() {
    while (state.queue.length > 0) {
      const [eventName, params] = state.queue.shift();
      sendEvent(eventName, params);
    }
  }

  function enqueueOrSend(eventName, params) {
    const payload = sanitizeParams({ ...getPageContext(), ...params });

    if (!state.initialized) {
      state.queue.push([eventName, payload]);
      return;
    }

    sendEvent(eventName, payload);
  }

  function loadGa4(measurementId) {
    if (!measurementId || typeof window.gtag === "function") {
      return;
    }

    window.dataLayer = window.dataLayer || [];
    window.gtag = function gtag() {
      window.dataLayer.push(arguments);
    };

    window.gtag("js", new Date());
    window.gtag("config", measurementId, {
      send_page_view: true,
      anonymize_ip: true,
    });

    const script = document.createElement("script");
    script.async = true;
    script.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(measurementId);
    document.head.appendChild(script);
  }

  function getPlacement(link) {
    const placements = [
      [".sticky-cta", "sticky_bar"],
      [".hero-actions", "hero"],
      [".comparison-table", "comparison_table"],
      [".contact-panel", "contact_panel"],
      [".social-card", "social_section"],
      [".source-box", "sources"],
      ["footer", "footer"],
      ["nav", "header_nav"],
      [".button-row", "button_row"],
    ];

    for (const [selector, label] of placements) {
      if (link.closest(selector)) {
        return label;
      }
    }

    return "content";
  }

  function getDestinationSlug(url) {
    const fileName = url.pathname.split("/").pop() || "";

    if (fileName === "index.html" || fileName === "") {
      return "home";
    }

    if (fileName === "come-iniziare.html") {
      return "come-iniziare";
    }

    if (fileName.startsWith("bonus-") && fileName.endsWith(".html")) {
      return fileName.replace(".html", "").replace("bonus-", "");
    }

    return "";
  }

  function classifyClick(link) {
    const href = link.getAttribute("href") || "";
    if (!href || href.startsWith("javascript:")) {
      return null;
    }

    const linkText = sanitizeText(link.textContent);
    const placement = getPlacement(link);

    if (href.startsWith("tel:")) {
      return {
        eventName: "contact_click",
        params: {
          contact_type: "phone",
          placement,
          link_text: linkText,
          target_kind: "phone",
        },
      };
    }

    const url = new URL(href, window.location.href);
    const sameOrigin = url.origin === window.location.origin;
    const destinationSlug = getDestinationSlug(url);

    if (url.hostname === "wa.me") {
      return {
        eventName: "contact_click",
        params: {
          contact_type: "whatsapp",
          placement,
          link_text: linkText,
          target_kind: "whatsapp",
        },
      };
    }

    if (url.hostname === "t.me" && url.pathname === "/bonuscontiita") {
      return {
        eventName: "contact_click",
        params: {
          contact_type: "telegram_direct",
          placement,
          link_text: linkText,
          target_kind: "telegram_direct",
        },
      };
    }

    if (url.hostname === "t.me" && url.pathname === "/bonuscontiitalia") {
      return {
        eventName: "channel_click",
        params: {
          channel_name: "telegram",
          placement,
          link_text: linkText,
          target_kind: "telegram_channel",
        },
      };
    }

    if (link.classList.contains("source-link")) {
      return {
        eventName: "source_click",
        params: {
          placement,
          link_text: linkText,
          outbound_host: url.hostname,
          target_kind: "source",
        },
      };
    }

    if (sameOrigin && destinationSlug) {
      return {
        eventName: "guide_click",
        params: {
          placement,
          link_text: linkText,
          destination_slug: destinationSlug,
          target_kind: "guide_page",
        },
      };
    }

    if (href.startsWith("#")) {
      return {
        eventName: "navigation_click",
        params: {
          placement,
          link_text: linkText,
          destination_slug: href.replace("#", ""),
          target_kind: "section_jump",
        },
      };
    }

    if (!sameOrigin && link.matches(".cta, .button-link, .table-link, .sticky-cta a")) {
      return {
        eventName: "offer_click",
        params: {
          placement,
          link_text: linkText,
          outbound_host: url.hostname,
          target_kind: "offer_or_outbound",
        },
      };
    }

    if (sameOrigin) {
      return {
        eventName: "navigation_click",
        params: {
          placement,
          link_text: linkText,
          target_kind: "internal_navigation",
        },
      };
    }

    return {
      eventName: "outbound_click",
      params: {
        placement,
        link_text: linkText,
        outbound_host: url.hostname,
        target_kind: "outbound",
      },
    };
  }

  function bindClickTracking() {
    document.addEventListener("click", function handleClick(event) {
      const link = event.target.closest("a[href]");
      if (!link || link.dataset.analyticsIgnore === "true") {
        return;
      }

      const click = classifyClick(link);
      if (!click) {
        return;
      }

      enqueueOrSend(click.eventName, click.params);
    });
  }

  function loadConfig() {
    return fetch(CONFIG_PATH, { cache: "no-cache" })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Impossibile caricare " + CONFIG_PATH);
        }
        return response.json();
      })
      .catch(function () {
        return {};
      });
  }

  function initializeAnalytics(config) {
    const query = new URLSearchParams(window.location.search);
    state.debug = Boolean(config?.analytics?.debug) || query.get(DEBUG_QUERY) === "1";

    const measurementId = config?.analytics?.ga4_measurement_id || "";
    if (measurementId) {
      loadGa4(measurementId);
    }

    state.initialized = true;
    flushQueue();
  }

  bindClickTracking();

  loadConfig().then(function (config) {
    initializeAnalytics(config);
  });

  window.BonusContiAnalytics = {
    track: enqueueOrSend,
  };
})();
