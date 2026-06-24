/* =====================================================
   Apollo CRS - Professional UI Runtime
   Version: Priority 11.5 Stabilized
   ===================================================== */
(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {
        CRS.flash.init();
        CRS.confirm.init();
        CRS.dropdown.init();
        CRS.cards.init();
        CRS.loginAlerts.init();
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
                const attemptedAt = alert.attempted_at || "";

                const item = document.createElement("div");
                item.className = "login-attempt-alert";
                item.setAttribute("role", "alert");
                item.setAttribute("data-login-alert-id", alert.id);
                item.innerHTML =
                    '<div class="login-attempt-alert-icon">⚠</div>' +
                    '<div class="login-attempt-alert-body">' +
                        '<strong>Another workstation tried to login with your username</strong>' +
                        '<div>Attempted from <b>' + workstation + '</b> / IP <b>' + clientIp + '</b> at ' + attemptedAt + '.</div>' +
                        '<div class="login-attempt-alert-meta">Your active CRS session remains protected. Finish your work and logout when ready.</div>' +
                    '</div>' +
                    '<form method="POST" action="/login-attempt-alerts/' + alert.id + '/ack" class="login-attempt-alert-form">' +
                        '<button type="submit" class="btn btn-secondary btn-sm">Acknowledge</button>' +
                    '</form>';

                stack.prepend(item);
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

            ["click", "keydown", "mousemove", "scroll", "touchstart"].forEach(function (eventName) {
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
            overlay.innerHTML = '<div class="operation-lock-card"><div class="operation-lock-title">' + (message || "Loading...") + '</div></div>';
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
