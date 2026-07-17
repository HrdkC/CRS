(function () {
    "use strict";

    var VERSION = "11.5";
    var THEME_KEY = "crs-theme";
    var SYSTEM_QUERY = "(prefers-color-scheme: dark)";
    var VALID_THEMES = ["system", "light", "dark"];
    var root = document.documentElement;
    var mediaQuery = window.matchMedia ? window.matchMedia(SYSTEM_QUERY) : null;
    var lastSignature = "";
    var pollTimer = null;

    function safeTheme(value) {
        return VALID_THEMES.indexOf(value) === -1 ? "system" : value;
    }

    function storageGet() {
        try {
            return safeTheme(localStorage.getItem(THEME_KEY) || "system");
        } catch (error) {
            return "system";
        }
    }

    function storageSet(value) {
        try {
            localStorage.setItem(THEME_KEY, value);
        } catch (error) {
            // The selected theme still applies to the current page.
        }
    }

    function systemTheme() {
        return mediaQuery && mediaQuery.matches ? "dark" : "light";
    }

    function resolvedTheme(choice) {
        var safeChoice = safeTheme(choice);
        if (safeChoice === "dark") return "dark";
        if (safeChoice === "light") return "light";
        return systemTheme();
    }

    function ensureMeta(name, id) {
        var selector = id ? "#" + id : 'meta[name="' + name + '"]';
        var meta = document.querySelector(selector);
        if (!meta) {
            meta = document.createElement("meta");
            if (id) meta.id = id;
            meta.name = name;
            document.head.appendChild(meta);
        }
        return meta;
    }

    function dispatchThemeEvent(detail) {
        var event;
        try {
            event = new CustomEvent("crs:themechange", { detail: detail });
        } catch (error) {
            event = document.createEvent("CustomEvent");
            event.initCustomEvent("crs:themechange", false, false, detail);
        }
        document.dispatchEvent(event);
    }

    function apply(choice, persist, force) {
        var safeChoice = safeTheme(choice);
        var system = systemTheme();
        var resolved = resolvedTheme(safeChoice);
        var signature = safeChoice + "|" + system + "|" + resolved;

        if (persist !== false) storageSet(safeChoice);

        root.setAttribute("data-crs-theme", safeChoice);
        root.setAttribute("data-crs-system-theme", system);
        root.setAttribute("data-crs-resolved-theme", resolved);
        root.style.colorScheme = resolved;

        var colorSchemeMeta = ensureMeta("color-scheme", "crs-color-scheme-meta");
        colorSchemeMeta.setAttribute("content", "light dark");

        var themeColorMeta = ensureMeta("theme-color", "crs-theme-color-meta");
        themeColorMeta.setAttribute("content", resolved === "dark" ? "#081327" : "#f8fafc");

        if (force || signature !== lastSignature) {
            lastSignature = signature;
            dispatchThemeEvent({
                choice: safeChoice,
                system: system,
                resolved: resolved,
                version: VERSION
            });
        }

        return {
            choice: safeChoice,
            system: system,
            resolved: resolved
        };
    }

    function sync(force) {
        return apply(storageGet(), false, force === true);
    }

    function bindSystemWatchers() {
        var update = function () {
            var choice = safeTheme(root.getAttribute("data-crs-theme") || storageGet());
            apply(choice, false, false);
        };

        if (mediaQuery) {
            if (mediaQuery.addEventListener) {
                mediaQuery.addEventListener("change", update);
            } else if (mediaQuery.addListener) {
                mediaQuery.addListener(update);
            }
        }

        window.addEventListener("focus", update);
        window.addEventListener("pageshow", update);
        document.addEventListener("visibilitychange", function () {
            if (!document.hidden) update();
        });
        window.addEventListener("storage", function (event) {
            if (!event || event.key === THEME_KEY || event.key === null) sync(true);
        });

        // Some Windows/browser combinations do not emit the media-query change
        // event reliably while the browser is in the background. A lightweight
        // poll keeps System mode synchronized when the window becomes active.
        pollTimer = window.setInterval(update, 1500);
    }

    if (window.CRSThemeRuntime && window.CRSThemeRuntime.version) {
        window.CRSThemeRuntime.sync(true);
        return;
    }

    window.CRSThemeRuntime = {
        version: VERSION,
        key: THEME_KEY,
        mediaQuery: mediaQuery,
        safeTheme: safeTheme,
        getChoice: storageGet,
        systemTheme: systemTheme,
        resolvedTheme: resolvedTheme,
        apply: apply,
        sync: sync,
        stopPolling: function () {
            if (pollTimer) {
                window.clearInterval(pollTimer);
                pollTimer = null;
            }
        }
    };

    apply(storageGet(), false, true);
    bindSystemWatchers();
})();
