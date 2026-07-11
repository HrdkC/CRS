/* =====================================================
   Apollo CRS - Professional UI Runtime
   Version: Priority 11.5 Stabilized
   ===================================================== */
(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {
        CRS.preferences.init();
        CRS.security.init();
        CRS.flash.init();
        CRS.confirm.init();
        CRS.dropdown.init();
        CRS.navigation.init();
        CRS.cards.init();
        CRS.tables.init();
        CRS.loginAlerts.init();
        CRS.recipeEditLock.init();
        CRS.session.init();
    });

    const CRS = window.CRS = window.CRS || {};

    CRS.util = {
        qs(selector, root) {
            return (root || document).querySelector(selector);
        },
        qsa(selector, root) {
            return Array.prototype.slice.call((root || document).querySelectorAll(selector));
        },
        isJsonResponse(response) {
            const type = response.headers.get("content-type") || "";
            return type.indexOf("application/json") !== -1;
        },
        formatSeconds(totalSeconds) {
            const safeTotal = Math.max(0, Math.floor(Number(totalSeconds) || 0));
            const minutes = Math.floor(safeTotal / 60);
            const seconds = safeTotal % 60;
            return String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0");
        }
    };

    CRS.preferences = {
        themeKey: "crs-theme",
        fontKey: "crs-font-step",
        themes: ["system", "light", "dark"],
        minFontStep: -4,
        maxFontStep: 4,
        mediaQuery: null,
        fontObserver: null,
        fontExcludeSelector: [
            "script",
            "style",
            "template",
            "noscript",
            "img",
            "svg",
            "path",
            ".site-header",
            ".site-header *",
            ".site-footer",
            ".site-footer *",
            ".crs-accessibility-strip",
            ".crs-accessibility-strip *"
        ].join(","),

        init() {
            this.mediaQuery = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
            this.applyStored();
            this.bindControls();
            this.bindSystemThemeWatcher();
            this.bindFontObserver();
        },

        storageGet(key, fallback) {
            try {
                return localStorage.getItem(key) || fallback;
            } catch (error) {
                return fallback;
            }
        },

        storageSet(key, value) {
            try {
                localStorage.setItem(key, value);
            } catch (error) {
                // Preference still applies for the current page.
            }
        },

        safeTheme(theme) {
            return this.themes.indexOf(theme) === -1 ? "system" : theme;
        },

        safeFontStep(step) {
            const parsed = parseInt(step, 10);
            if (Number.isNaN(parsed)) return 0;
            return Math.max(this.minFontStep, Math.min(this.maxFontStep, parsed));
        },

        resolvedTheme(theme) {
            if (theme === "dark") return "dark";
            if (theme === "light") return "light";
            return this.mediaQuery && this.mediaQuery.matches ? "dark" : "light";
        },

        applyStored() {
            const theme = this.safeTheme(this.storageGet(this.themeKey, "system"));
            const fontStep = this.safeFontStep(this.storageGet(this.fontKey, "0"));
            this.applyTheme(theme, false);
            this.applyFontStep(fontStep, false);
        },

        applyTheme(theme, persist) {
            const safeTheme = this.safeTheme(theme);
            const root = document.documentElement;
            root.setAttribute("data-crs-theme", safeTheme);
            root.setAttribute("data-crs-resolved-theme", this.resolvedTheme(safeTheme));

            if (persist !== false) {
                this.storageSet(this.themeKey, safeTheme);
            }

            CRS.util.qsa("[data-crs-theme-choice]").forEach(function (button) {
                const active = button.getAttribute("data-crs-theme-choice") === safeTheme;
                button.classList.toggle("is-active", active);
                button.setAttribute("aria-pressed", active ? "true" : "false");
            });
        },

        applyFontStep(step, persist) {
            const safeStep = this.safeFontStep(step);
            const adjustPx = safeStep;
            const root = document.documentElement;
            const label = CRS.util.qs("#crs-font-step-label");
            root.setAttribute("data-crs-font-step", String(safeStep));
            this.applyDocumentFontAdjustment(safeStep);

            if (label) {
                label.textContent = adjustPx > 0 ? "+" + adjustPx + "px" : adjustPx + "px";
            }

            if (persist !== false) {
                this.storageSet(this.fontKey, String(safeStep));
            }

            CRS.util.qsa("[data-crs-font-action='decrease']").forEach(function (button) {
                button.disabled = safeStep <= CRS.preferences.minFontStep;
            });
            CRS.util.qsa("[data-crs-font-action='increase']").forEach(function (button) {
                button.disabled = safeStep >= CRS.preferences.maxFontStep;
            });
            CRS.util.qsa("[data-crs-font-action]").forEach(function (button) {
                const action = button.getAttribute("data-crs-font-action");
                const active = action === "reset" && safeStep === 0;
                button.classList.toggle("is-active", active);
                button.setAttribute("aria-pressed", active ? "true" : "false");
            });
        },

        applyDocumentFontAdjustment(step) {
            const safeStep = this.safeFontStep(step);
            const root = document.documentElement;
            root.style.setProperty("--crs-font-adjust", "0px");

            const targets = document.body
                ? [document.body].concat(CRS.util.qsa("*", document.body))
                : [];

            targets.forEach(function (element) {
                CRS.preferences.adjustFontElement(element, safeStep);
            });

            root.style.setProperty("--crs-font-adjust", String(safeStep) + "px");
        },

        adjustFontElement(element, step) {
            if (!element || element.matches(this.fontExcludeSelector)) return;

            if (!element.hasAttribute("data-crs-base-font-size")) {
                const computedSize = parseFloat(window.getComputedStyle(element).fontSize || "0");
                if (!computedSize) return;
                element.setAttribute("data-crs-base-font-size", String(computedSize));
                element.setAttribute(
                    "data-crs-original-inline-font-size",
                    element.style.getPropertyValue("font-size") || ""
                );
                element.setAttribute(
                    "data-crs-original-font-priority",
                    element.style.getPropertyPriority("font-size") || ""
                );
            }

            if (step === 0) {
                const original = element.getAttribute("data-crs-original-inline-font-size") || "";
                const priority = element.getAttribute("data-crs-original-font-priority") || "";
                if (original) {
                    element.style.setProperty("font-size", original, priority);
                } else {
                    element.style.removeProperty("font-size");
                }
                return;
            }

            const baseSize = parseFloat(element.getAttribute("data-crs-base-font-size") || "0");
            if (!baseSize) return;
            element.style.setProperty(
                "font-size",
                Math.max(8, baseSize + step) + "px",
                "important"
            );
        },

        bindFontObserver() {
            if (!document.body || this.fontObserver) return;

            this.fontObserver = new MutationObserver(function () {
                const currentStep = CRS.preferences.safeFontStep(
                    document.documentElement.getAttribute("data-crs-font-step") || "0"
                );
                if (currentStep !== 0) {
                    CRS.preferences.applyDocumentFontAdjustment(currentStep);
                }
            });

            this.fontObserver.observe(document.body, {
                childList: true,
                subtree: true
            });
        },

        bindControls() {
            const toggle = CRS.util.qs("#crs-settings-toggle");
            const panel = CRS.util.qs("#crs-settings-panel");

            document.addEventListener("click", function (event) {
                const themeButton = event.target.closest("[data-crs-theme-choice]");
                const fontButton = event.target.closest("[data-crs-font-action]");

                if (themeButton) {
                    CRS.preferences.applyTheme(themeButton.getAttribute("data-crs-theme-choice"));
                    return;
                }

                if (fontButton) {
                    const action = fontButton.getAttribute("data-crs-font-action");
                    const currentStep = CRS.preferences.safeFontStep(
                        document.documentElement.getAttribute("data-crs-font-step") || "0"
                    );
                    if (action === "increase") CRS.preferences.applyFontStep(currentStep + 1);
                    if (action === "decrease") CRS.preferences.applyFontStep(currentStep - 1);
                    if (action === "reset") CRS.preferences.applyFontStep(0);
                }
            });

            if (!toggle || !panel) return;

            toggle.addEventListener("click", function (event) {
                event.stopPropagation();
                const opening = panel.hidden;
                panel.hidden = !opening;
                toggle.setAttribute("aria-expanded", opening ? "true" : "false");
            });

            panel.addEventListener("click", function (event) {
                const themeButton = event.target.closest("[data-crs-theme-choice]");
                const fontButton = event.target.closest("[data-crs-font-action]");

                if (themeButton) {
                    CRS.preferences.applyTheme(themeButton.getAttribute("data-crs-theme-choice"));
                    return;
                }

                if (fontButton) {
                    const action = fontButton.getAttribute("data-crs-font-action");
                    const currentStep = CRS.preferences.safeFontStep(
                        document.documentElement.getAttribute("data-crs-font-step") || "0"
                    );
                    if (action === "increase") CRS.preferences.applyFontStep(currentStep + 1);
                    if (action === "decrease") CRS.preferences.applyFontStep(currentStep - 1);
                    if (action === "reset") CRS.preferences.applyFontStep(0);
                }
            });

            document.addEventListener("click", function (event) {
                if (panel.hidden || event.target.closest(".crs-display-settings")) return;
                panel.hidden = true;
                toggle.setAttribute("aria-expanded", "false");
            });

            document.addEventListener("keydown", function (event) {
                if (event.key !== "Escape" || panel.hidden) return;
                panel.hidden = true;
                toggle.setAttribute("aria-expanded", "false");
                toggle.focus();
            });
        },

        bindSystemThemeWatcher() {
            if (!this.mediaQuery) return;

            const updateResolvedTheme = function () {
                const theme = CRS.preferences.safeTheme(
                    document.documentElement.getAttribute("data-crs-theme") || "system"
                );
                document.documentElement.setAttribute(
                    "data-crs-resolved-theme",
                    CRS.preferences.resolvedTheme(theme)
                );
            };

            if (this.mediaQuery.addEventListener) {
                this.mediaQuery.addEventListener("change", updateResolvedTheme);
            } else if (this.mediaQuery.addListener) {
                this.mediaQuery.addListener(updateResolvedTheme);
            }
        }
    };

    CRS.security = {
        init() {
            this.patchForms();
            this.patchFetch();
        },

        token() {
            const meta = CRS.util.qs('meta[name="csrf-token"]');
            return meta ? meta.getAttribute("content") || "" : "";
        },

        isUnsafeMethod(method) {
            return ["POST", "PUT", "PATCH", "DELETE"].indexOf(String(method || "GET").toUpperCase()) !== -1;
        },

        isSameOrigin(url) {
            try {
                const parsed = new URL(url, window.location.href);
                return parsed.origin === window.location.origin;
            } catch (error) {
                return false;
            }
        },

        appendFormToken(form) {
            if (!form || !this.isUnsafeMethod(form.getAttribute("method"))) return;
            if (form.querySelector('input[name="_csrf_token"]')) return;

            const token = this.token();
            if (!token) return;

            const hidden = document.createElement("input");
            hidden.type = "hidden";
            hidden.name = "_csrf_token";
            hidden.value = token;
            form.appendChild(hidden);
        },

        patchForms() {
            document.addEventListener("submit", function (event) {
                CRS.security.appendFormToken(event.target);
            }, true);
        },

        patchFetch() {
            if (!window.fetch || window.fetch._crsCsrfPatched) return;

            const originalFetch = window.fetch.bind(window);

            window.fetch = function (input, init) {
                const options = init ? Object.assign({}, init) : {};
                const inputMethod = input && input.method ? input.method : "GET";
                const method = (options.method || inputMethod || "GET").toUpperCase();
                const inputUrl = input && input.url ? input.url : input;

                if (CRS.security.isUnsafeMethod(method) && CRS.security.isSameOrigin(inputUrl)) {
                    const token = CRS.security.token();
                    if (token) {
                        const headers = new Headers(options.headers || (input && input.headers ? input.headers : undefined));
                        headers.set("X-CSRFToken", token);
                        options.headers = headers;
                    }
                }

                return originalFetch(input, options);
            };

            window.fetch._crsCsrfPatched = true;
        }
    };

    CRS.flash = {
        init() {
            CRS.util.qsa(".flash-message").forEach(function (message) {
                const sticky = message.dataset.sticky === "1";
                if (sticky) return;
                setTimeout(function () {
                    message.style.transition = "opacity 0.35s ease, transform 0.35s ease";
                    message.style.opacity = "0";
                    message.style.transform = "translateY(-4px)";
                    setTimeout(function () { message.remove(); }, 380);
                }, 4500);
            });
        }
    };

    CRS.confirm = {
        init() {
            const confirmedForms = new WeakSet();

            CRS.util.qsa("form[data-confirm]").forEach(function (form) {
                form.addEventListener("submit", function (event) {
                    if (confirmedForms.has(form)) return;
                    const message = form.getAttribute("data-confirm");
                    if (message && !window.confirm(message)) {
                        event.preventDefault();
                        return;
                    }
                    confirmedForms.add(form);
                });
            });

            CRS.util.qsa("a[data-confirm], button[data-confirm]").forEach(function (element) {
                const parentForm = element.closest("form[data-confirm]");
                if (parentForm && (element.type || "").toLowerCase() === "submit") return;

                element.addEventListener("click", function (event) {
                    const message = element.getAttribute("data-confirm");
                    if (message && !window.confirm(message)) {
                        event.preventDefault();
                    }
                });
            });
        }
    };

    CRS.dropdown = {
        init() {
            CRS.util.qsa(".dropdown").forEach(function (dropdown) {
                let closeTimer = null;

                dropdown.addEventListener("mouseenter", function () {
                    if (closeTimer) clearTimeout(closeTimer);
                    dropdown.classList.add("dropdown-open");
                });

                dropdown.addEventListener("mouseleave", function () {
                    closeTimer = setTimeout(function () {
                        dropdown.classList.remove("dropdown-open");
                    }, 500);
                });

                const trigger = dropdown.querySelector("a");
                if (trigger) {
                    trigger.addEventListener("click", function (event) {
                        if (trigger.getAttribute("href") === "#") {
                            event.preventDefault();
                            dropdown.classList.toggle("dropdown-open");
                        }
                    });
                }
            });

            document.addEventListener("click", function (event) {
                if (event.target.closest(".dropdown")) return;
                CRS.util.qsa(".dropdown.dropdown-open").forEach(function (dropdown) {
                    dropdown.classList.remove("dropdown-open");
                });
            });
        }
    };

    CRS.navigation = {
        init() {
            CRS.util.qsa(".nav-back-button").forEach(function (button) {
                button.addEventListener("click", function () {
                    const fallback = button.getAttribute("data-back-fallback") || "/";
                    const referrer = document.referrer || "";
                    const sameOrigin = referrer.indexOf(window.location.origin) === 0;

                    if (window.history.length > 1 && sameOrigin) {
                        window.history.back();
                        return;
                    }

                    window.location.href = fallback;
                });
            });

            const header = CRS.util.qs(".site-header");
            const toggle = CRS.util.qs(".mobile-nav-toggle", header);
            const navigation = CRS.util.qs("#primary-navigation", header);
            if (!header || !toggle || !navigation) return;

            function setOpen(open) {
                header.classList.toggle("mobile-navigation-open", open);
                toggle.setAttribute("aria-expanded", open ? "true" : "false");
                toggle.setAttribute(
                    "aria-label",
                    open ? "Close navigation menu" : "Open navigation menu"
                );
            }

            toggle.addEventListener("click", function () {
                setOpen(toggle.getAttribute("aria-expanded") !== "true");
            });

            navigation.addEventListener("click", function (event) {
                const link = event.target.closest("a");
                if (!link || link.getAttribute("href") === "#") return;
                if (window.matchMedia("(max-width: 980px)").matches) setOpen(false);
            });

            document.addEventListener("keydown", function (event) {
                if (event.key === "Escape") setOpen(false);
            });

            window.addEventListener("resize", function () {
                if (!window.matchMedia("(max-width: 980px)").matches) setOpen(false);
            });
        }
    };

    CRS.cards = {
        init() {
            CRS.util.qsa(".dashboard-card").forEach(function (card, index) {
                card.style.opacity = "0";
                card.style.transform = "translateY(10px)";
                setTimeout(function () {
                    card.style.transition = "opacity 0.25s ease, transform 0.25s ease";
                    card.style.opacity = "1";
                    card.style.transform = "translateY(0)";
                }, Math.min(index * 50, 400));
            });
        }
    };

    CRS.tables = {
        init() {
            CRS.util.qsa("table").forEach(function (table) {
                if (table.dataset.clientSortReady === "1" || table.classList.contains("no-client-sort")) return;

                const headerRow = table.tHead ? table.tHead.rows[0] : table.querySelector("tr");
                const body = table.tBodies && table.tBodies.length ? table.tBodies[0] : null;
                if (!headerRow || !body || body.rows.length < 2) return;

                table.dataset.clientSortReady = "1";
                table.classList.add("client-sort-table");

                CRS.util.qsa("th", headerRow).forEach(function (th, columnIndex) {
                    if (th.colSpan && th.colSpan > 1) return;
                    if (th.querySelector("a, button, input, select")) {
                        th.classList.add("client-sort-existing-control");
                        return;
                    }

                    const label = th.textContent.trim();
                    if (!label) return;

                    th.textContent = "";
                    const button = document.createElement("button");
                    const labelSpan = document.createElement("span");
                    const icon = document.createElement("b");
                    button.type = "button";
                    button.className = "client-sort-button";
                    button.title = "Sort by " + label;
                    labelSpan.textContent = label;
                    icon.setAttribute("aria-hidden", "true");
                    icon.textContent = "↕";
                    button.appendChild(labelSpan);
                    button.appendChild(icon);
                    button.addEventListener("click", function () {
                        CRS.tables.sort(table, columnIndex, button);
                    });

                    th.appendChild(button);
                });
            });
        },

        cellText(row, columnIndex) {
            const cell = row.cells[columnIndex];
            if (!cell) return "";
            return (cell.getAttribute("data-sort-value") || cell.textContent || "").trim();
        },

        compareValues(a, b) {
            const numericA = Number(String(a).replace(/,/g, ""));
            const numericB = Number(String(b).replace(/,/g, ""));
            const bothNumeric = a !== "" && b !== "" && !Number.isNaN(numericA) && !Number.isNaN(numericB);

            if (bothNumeric) return numericA - numericB;
            return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
        },

        sort(table, columnIndex, button) {
            const body = table.tBodies[0];
            const currentDirection = button.getAttribute("data-sort-direction") || "none";
            const nextDirection = currentDirection === "asc" ? "desc" : "asc";
            const rows = Array.prototype.slice.call(body.rows);

            rows.sort(function (rowA, rowB) {
                const result = CRS.tables.compareValues(
                    CRS.tables.cellText(rowA, columnIndex),
                    CRS.tables.cellText(rowB, columnIndex)
                );
                return nextDirection === "asc" ? result : -result;
            });

            rows.forEach(function (row) { body.appendChild(row); });

            CRS.util.qsa(".client-sort-button", table).forEach(function (otherButton) {
                otherButton.removeAttribute("data-sort-direction");
                const icon = otherButton.querySelector("b");
                if (icon) icon.textContent = "↕";
            });

            button.setAttribute("data-sort-direction", nextDirection);
            const icon = button.querySelector("b");
            if (icon) icon.textContent = nextDirection === "asc" ? "↑" : "↓";
        }
    };

    CRS.loginAlerts = {
        init() {
            document.addEventListener("submit", async function (event) {
                const form = event.target;
                if (!form || !form.classList || !form.classList.contains("login-attempt-alert-form")) return;

                event.preventDefault();
                await CRS.loginAlerts.acknowledge(form);
            });
        },

        async acknowledge(form) {
            const alertCard = form.closest(".login-attempt-alert");
            const button = form.querySelector("button[type='submit']");
            const originalText = button ? button.textContent : "";

            if (button) {
                button.disabled = true;
                button.textContent = "Acknowledging...";
            }

            try {
                const response = await fetch(form.action, {
                    method: "POST",
                    headers: { "X-Requested-With": "XMLHttpRequest" }
                });

                const payload = await (CRS.util.isJsonResponse(response) ? response.json() : Promise.resolve({}));

                if (response.status === 401 || payload.redirect) {
                    window.location.href = payload.redirect || "/login";
                    return;
                }

                if (!response.ok || !payload.ok) {
                    if (button) {
                        button.disabled = false;
                        button.textContent = originalText || "Acknowledge";
                    }
                    return;
                }

                if (alertCard) {
                    alertCard.style.transition = "opacity 0.18s ease, transform 0.18s ease";
                    alertCard.style.opacity = "0";
                    alertCard.style.transform = "translateY(-5px)";
                    setTimeout(function () { alertCard.remove(); }, 220);
                }
            } catch (error) {
                if (button) {
                    button.disabled = false;
                    button.textContent = originalText || "Acknowledge";
                }
            }
        },

        show(alerts) {
            if (!alerts || !alerts.length) return;

            let stack = CRS.util.qs(".login-attempt-alert-stack");
            if (!stack) {
                stack = document.createElement("div");
                stack.className = "login-attempt-alert-stack";
                const main = CRS.util.qs(".main-container");
                if (main) main.prepend(stack);
                else document.body.appendChild(stack);
            }

            alerts.forEach(function (alert) {
                if (document.querySelector('[data-login-alert-id="' + alert.id + '"]')) return;

                const workstation = alert.attempted_workstation_name || "Unknown workstation";
                const clientIp = alert.attempted_client_ip || "-";
                const attemptedAt = alert.last_attempted_at || alert.attempted_at || "";
                const attemptCount = parseInt(alert.attempt_count || "1", 10);
                const item = document.createElement("div");
                item.className = "login-attempt-alert";
                item.setAttribute("role", "alert");
                item.setAttribute("data-login-alert-id", alert.id);

                const icon = document.createElement("div");
                icon.className = "login-attempt-alert-icon";
                icon.textContent = "!";

                const body = document.createElement("div");
                body.className = "login-attempt-alert-body";
                const title = document.createElement("strong");
                title.textContent = "Another workstation tried to login with your username";
                const detail = document.createElement("div");
                detail.textContent = "Attempted from " + workstation + " / IP " + clientIp + " at " + attemptedAt + ".";
                if (attemptCount > 1) {
                    const attemptBadge = document.createElement("span");
                    attemptBadge.className = "status-badge status-warning";
                    attemptBadge.textContent = attemptCount + " attempts";
                    detail.appendChild(document.createTextNode(" "));
                    detail.appendChild(attemptBadge);
                }
                const meta = document.createElement("div");
                meta.className = "login-attempt-alert-meta";
                meta.textContent = "Your active CRS session remains protected. Finish your work and logout when ready.";
                body.appendChild(title);
                body.appendChild(detail);
                body.appendChild(meta);

                const form = document.createElement("form");
                form.method = "POST";
                form.action = "/login-attempt-alerts/" + encodeURIComponent(String(alert.id)) + "/ack";
                form.className = "login-attempt-alert-form";
                const acknowledge = document.createElement("button");
                acknowledge.type = "submit";
                acknowledge.className = "btn btn-secondary btn-sm";
                acknowledge.textContent = "Acknowledge";
                form.appendChild(acknowledge);

                item.appendChild(icon);
                item.appendChild(body);
                item.appendChild(form);

                stack.prepend(item);
            });
        }
    };


    CRS.recipeEditLock = {
        init() {
            const page = CRS.util.qs(".recipe-edit-lock-page[data-edit-lock-release-url]");
            if (!page) return;

            const releaseUrl = page.getAttribute("data-edit-lock-release-url");
            const lockId = page.getAttribute("data-edit-lock-id") || "";
            let normalSubmitInProgress = false;
            let released = false;

            CRS.util.qsa(".recipe-edit-save-form, .recipe-edit-release-form", page).forEach(function (form) {
                form.addEventListener("submit", function () {
                    normalSubmitInProgress = true;
                });
            });

            function releaseLock(reason) {
                if (released || normalSubmitInProgress || !releaseUrl) return;
                released = true;

                const payload = new FormData();
                payload.append("lock_id", lockId);
                payload.append("reason", reason || "PAGE_UNLOAD");
                payload.append("_csrf_token", CRS.security.token());

                if (navigator.sendBeacon) {
                    try {
                        navigator.sendBeacon(releaseUrl, payload);
                        return;
                    } catch (error) {
                        // Fall through to fetch keepalive.
                    }
                }

                try {
                    fetch(releaseUrl, {
                        method: "POST",
                        body: payload,
                        keepalive: true,
                        headers: { "X-Requested-With": "XMLHttpRequest" }
                    });
                } catch (error) {
                    // Server-side expiry still protects plant operation.
                }
            }

            window.addEventListener("pagehide", function () {
                releaseLock("PAGE_HIDE");
            });

            document.addEventListener("visibilitychange", function () {
                if (document.visibilityState === "hidden") {
                    releaseLock("PAGE_HIDDEN");
                }
            });
        }
    };

    CRS.session = {
        init() {
            const countdown = CRS.util.qs("#session-countdown");
            if (!countdown) return;

            const countdownValue = CRS.util.qs("#session-countdown-value");
            const settingsPreview = CRS.util.qs("#session-settings-countdown");
            let timeoutSeconds = parseInt(countdown.getAttribute("data-timeout-seconds") || "1800", 10);
            let lastActivityEpoch = parseInt(countdown.getAttribute("data-last-activity-epoch") || "0", 10);
            if (!lastActivityEpoch) lastActivityEpoch = Math.floor(Date.now() / 1000);

            let deadlineEpoch = lastActivityEpoch + timeoutSeconds;
            let lastHeartbeatMs = 0;
            let userActivitySinceHeartbeat = false;
            let expireInProgress = false;
            const heartbeatIntervalMs = 15000;

            function render() {
                const remaining = deadlineEpoch - Math.floor(Date.now() / 1000);
                const display = CRS.util.formatSeconds(remaining);

                if (countdownValue) countdownValue.textContent = display;
                if (settingsPreview) settingsPreview.textContent = display;

                countdown.classList.remove("session-countdown-warning", "session-countdown-danger");
                if (remaining <= 60) countdown.classList.add("session-countdown-danger");
                else if (remaining <= 180) countdown.classList.add("session-countdown-warning");

                if (remaining <= 0 && !expireInProgress) {
                    expireInProgress = true;
                    expireFromClientTimer();
                }
            }

            async function heartbeat(forceActivity) {
                const nowMs = Date.now();
                if (!forceActivity && nowMs - lastHeartbeatMs < heartbeatIntervalMs) return;

                lastHeartbeatMs = nowMs;
                const hadUserActivity = Boolean(forceActivity || userActivitySinceHeartbeat);
                userActivitySinceHeartbeat = false;

                try {
                    const response = await fetch("/session-heartbeat", {
                        method: "POST",
                        headers: {
                            "X-Requested-With": "XMLHttpRequest",
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({ user_activity: hadUserActivity })
                    });

                    if (!response.ok) {
                        window.location.href = "/login";
                        return;
                    }

                    const payload = await response.json();
                    if (!payload.ok) {
                        window.location.href = payload.redirect || "/login";
                        return;
                    }

                    timeoutSeconds = parseInt(payload.timeout_seconds || timeoutSeconds, 10);
                    lastActivityEpoch = parseInt(payload.last_activity_epoch || lastActivityEpoch, 10);
                    deadlineEpoch = lastActivityEpoch + timeoutSeconds;
                    countdown.setAttribute("data-timeout-seconds", String(timeoutSeconds));
                    countdown.setAttribute("data-last-activity-epoch", String(lastActivityEpoch));

                    if (payload.login_attempt_alerts) CRS.loginAlerts.show(payload.login_attempt_alerts);
                    render();
                } catch (error) {
                    // Server remains the source of truth on the next successful request.
                }
            }

            async function expireFromClientTimer() {
                if (countdownValue) countdownValue.textContent = "00:00";
                try {
                    await fetch("/session-auto-expire", {
                        method: "POST",
                        headers: { "X-Requested-With": "XMLHttpRequest" }
                    });
                } catch (error) {
                    // Redirect still protects the UI.
                }
                window.location.href = "/login";
            }

            function markActivity() {
                userActivitySinceHeartbeat = true;
            }

            ["click", "keydown", "input", "change", "scroll", "touchstart", "pointerdown"].forEach(function (eventName) {
                document.addEventListener(eventName, markActivity, { passive: true });
            });

            setInterval(function () { heartbeat(false); }, heartbeatIntervalMs);
            setInterval(function () {
                render();
                if (userActivitySinceHeartbeat) heartbeat(true);
            }, 1000);

            heartbeat(false);
            render();
        }
    };

    CRS.loading = {
        show(message) {
            if (CRS.util.qs("#loading-overlay")) return;
            const overlay = document.createElement("div");
            overlay.id = "loading-overlay";
            overlay.className = "operation-lock-overlay";
            overlay.style.display = "grid";
            const card = document.createElement("div");
            card.className = "operation-lock-card";
            const title = document.createElement("div");
            title.className = "operation-lock-title";
            title.textContent = message || "Loading...";
            card.appendChild(title);
            overlay.appendChild(card);
            document.body.appendChild(overlay);
        },
        hide() {
            const overlay = CRS.util.qs("#loading-overlay");
            if (overlay) overlay.remove();
        }
    };

    window.showLoading = CRS.loading.show;
    window.hideLoading = CRS.loading.hide;
})();
