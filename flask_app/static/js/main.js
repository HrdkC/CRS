/* =====================================================
   Apollo CRS - UI JavaScript
   Version 0.1 Beta
   Purpose: Single-source JS aligned to base.html
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

    window.CRS = window.CRS || {};

    /* =====================================================
       01. Utilities
       ===================================================== */
    CRS.util = {
        qs: function (selector, root) {
            return (root || document).querySelector(selector);
        },

        qsa: function (selector, root) {
            return Array.prototype.slice.call((root || document).querySelectorAll(selector));
        },

        toInt: function (value, fallback) {
            const parsed = parseInt(value, 10);
            return Number.isFinite(parsed) ? parsed : fallback;
        },

        postJson: async function (url, body) {
            const response = await fetch(url, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(body || {})
            });

            const payload = await response.json().catch(function () {
                return {};
            });

            return { response: response, payload: payload };
        },

        escapeHtml: function (value) {
            return String(value || "")
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }
    };

    /* =====================================================
       02. Flash Messages
       ===================================================== */
    CRS.flash = {
        init: function () {
            CRS.util.qsa(".flash-message").forEach(function (message) {
                setTimeout(function () {
                    message.style.transition = "opacity 0.35s ease, transform 0.35s ease";
                    message.style.opacity = "0";
                    message.style.transform = "translateY(-4px)";

                    setTimeout(function () {
                        if (message && message.parentNode) {
                            message.remove();
                        }
                    }, 380);
                }, 4500);
            });
        }
    };

    /* =====================================================
       03. Confirmation Framework
       - form[data-confirm] confirms only on submit
       - a/button[data-confirm] confirms only on click
       ===================================================== */
    CRS.confirm = {
        init: function () {
            CRS.util.qsa("form[data-confirm]").forEach(function (form) {
                form.addEventListener("submit", function (event) {
                    const message = form.getAttribute("data-confirm");

                    if (message && !window.confirm(message)) {
                        event.preventDefault();
                    }
                });
            });

            CRS.util.qsa("a[data-confirm], button[data-confirm]").forEach(function (element) {
                const parentConfirmForm = element.closest("form[data-confirm]");
                const isSubmitButton = String(element.getAttribute("type") || "").toLowerCase() === "submit";

                if (parentConfirmForm && isSubmitButton) {
                    return;
                }

                element.addEventListener("click", function (event) {
                    const message = element.getAttribute("data-confirm");

                    if (message && !window.confirm(message)) {
                        event.preventDefault();
                    }
                });
            });
        }
    };

    /* =====================================================
       04. Header Dropdown Menus
       ===================================================== */
    CRS.dropdown = {
        init: function () {
            CRS.util.qsa(".dropdown").forEach(function (dropdown) {
                let closeTimer = null;

                dropdown.addEventListener("mouseenter", function () {
                    if (closeTimer) {
                        clearTimeout(closeTimer);
                    }
                    dropdown.classList.add("dropdown-open");
                });

                dropdown.addEventListener("mouseleave", function () {
                    closeTimer = setTimeout(function () {
                        dropdown.classList.remove("dropdown-open");
                    }, 450);
                });
            });
        }
    };

    /* =====================================================
       05. Subtle Card Animation
       ===================================================== */
    CRS.cards = {
        init: function () {
            CRS.util.qsa(".dashboard-card").forEach(function (card, index) {
                card.style.opacity = "0";
                card.style.transform = "translateY(8px)";

                setTimeout(function () {
                    card.style.transition = "opacity 0.25s ease, transform 0.25s ease";
                    card.style.opacity = "1";
                    card.style.transform = "translateY(0)";
                }, Math.min(index * 45, 300));
            });
        }
    };

    /* =====================================================
       06. Login Attempt Alert Acknowledge
       ===================================================== */
    CRS.loginAlerts = {
        init: function () {
            document.addEventListener("submit", async function (event) {
                const form = event.target;

                if (!form || !form.classList || !form.classList.contains("login-attempt-alert-form")) {
                    return;
                }

                event.preventDefault();
                await CRS.loginAlerts.acknowledge(form);
            });
        },

        acknowledge: async function (form) {
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

                const payload = await response.json().catch(function () {
                    return {};
                });

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
                    alertCard.style.transform = "translateY(-4px)";
                    setTimeout(function () {
                        alertCard.remove();
                    }, 200);
                }
            } catch (error) {
                if (button) {
                    button.disabled = false;
                    button.textContent = originalText || "Acknowledge";
                }
            }
        },

        show: function (alerts) {
            if (!alerts || !alerts.length) {
                return;
            }

            let stack = CRS.util.qs(".login-attempt-alert-stack");
            const mainContainer = CRS.util.qs(".main-container");

            if (!stack) {
                stack = document.createElement("div");
                stack.className = "login-attempt-alert-stack";
                if (mainContainer) {
                    mainContainer.prepend(stack);
                } else {
                    document.body.appendChild(stack);
                }
            }

            alerts.forEach(function (alert) {
                if (!alert || !alert.id) {
                    return;
                }

                if (CRS.util.qs('[data-login-alert-id="' + alert.id + '"]')) {
                    return;
                }

                const workstation = CRS.util.escapeHtml(alert.attempted_workstation_name || "Unknown workstation");
                const clientIp = CRS.util.escapeHtml(alert.attempted_client_ip || "-");
                const attemptedAt = CRS.util.escapeHtml(alert.attempted_at || "");

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

    /* =====================================================
       07. Session Countdown + Browser Heartbeat
       ===================================================== */
    CRS.session = {
        init: function () {
            const countdown = CRS.util.qs("#session-countdown");
            if (!countdown) {
                return;
            }

            const countdownValue = CRS.util.qs("#session-countdown-value");
            const settingsPreview = CRS.util.qs("#session-settings-countdown");

            let timeoutSeconds = CRS.util.toInt(countdown.getAttribute("data-timeout-seconds"), 1800);
            let lastActivityEpoch = CRS.util.toInt(countdown.getAttribute("data-last-activity-epoch"), Math.floor(Date.now() / 1000));
            let deadlineEpoch = lastActivityEpoch + timeoutSeconds;
            let lastHeartbeatMs = 0;
            let userActivitySinceHeartbeat = false;
            let expireInProgress = false;
            const heartbeatIntervalMs = 15000;

            function formatSeconds(totalSeconds) {
                const safeSeconds = Math.max(0, Math.floor(totalSeconds));
                const minutes = Math.floor(safeSeconds / 60);
                const seconds = safeSeconds % 60;
                return String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0");
            }

            function renderCountdown() {
                const nowEpoch = Math.floor(Date.now() / 1000);
                const remainingSeconds = deadlineEpoch - nowEpoch;
                const displayValue = formatSeconds(remainingSeconds);

                if (countdownValue) {
                    countdownValue.textContent = displayValue;
                }

                if (settingsPreview) {
                    settingsPreview.textContent = displayValue;
                }

                countdown.classList.remove("session-countdown-warning", "session-countdown-danger");

                if (remainingSeconds <= 60) {
                    countdown.classList.add("session-countdown-danger");
                } else if (remainingSeconds <= 180) {
                    countdown.classList.add("session-countdown-warning");
                }

                if (remainingSeconds <= 0 && !expireInProgress) {
                    expireInProgress = true;
                    expireSessionFromClientTimer();
                }
            }

            async function heartbeat(forceActivity) {
                const nowMs = Date.now();
                if (!forceActivity && nowMs - lastHeartbeatMs < heartbeatIntervalMs) {
                    return;
                }

                lastHeartbeatMs = nowMs;
                const hadUserActivity = Boolean(forceActivity || userActivitySinceHeartbeat);
                userActivitySinceHeartbeat = false;

                try {
                    const result = await CRS.util.postJson("/session-heartbeat", {
                        user_activity: hadUserActivity
                    });

                    if (!result.response.ok || !result.payload.ok) {
                        window.location.href = result.payload.redirect || "/login";
                        return;
                    }

                    timeoutSeconds = CRS.util.toInt(result.payload.timeout_seconds, timeoutSeconds);
                    lastActivityEpoch = CRS.util.toInt(result.payload.last_activity_epoch, lastActivityEpoch);
                    deadlineEpoch = lastActivityEpoch + timeoutSeconds;

                    countdown.setAttribute("data-timeout-seconds", String(timeoutSeconds));
                    countdown.setAttribute("data-last-activity-epoch", String(lastActivityEpoch));

                    if (result.payload.login_attempt_alerts) {
                        CRS.loginAlerts.show(result.payload.login_attempt_alerts);
                    }

                    renderCountdown();
                } catch (error) {
                    // Local countdown continues; server will enforce timeout on next request.
                }
            }

            async function expireSessionFromClientTimer() {
                if (countdownValue) {
                    countdownValue.textContent = "00:00";
                }

                try {
                    await fetch("/session-auto-expire", {
                        method: "POST",
                        headers: { "X-Requested-With": "XMLHttpRequest" }
                    });
                } catch (error) {
                    // Redirect still protects UI.
                }

                window.location.href = "/login";
            }

            function markUserActivity() {
                userActivitySinceHeartbeat = true;
            }

            ["click", "keydown", "scroll", "touchstart"].forEach(function (eventName) {
                document.addEventListener(eventName, markUserActivity, { passive: true });
            });

            // Mousemove can be noisy. Use pointerdown/click/keyboard/scroll for idle reset.
            setInterval(function () {
                heartbeat(false);
            }, heartbeatIntervalMs);

            setInterval(function () {
                renderCountdown();
                if (userActivitySinceHeartbeat) {
                    heartbeat(true);
                }
            }, 1000);

            heartbeat(false);
            renderCountdown();
        }
    };

    /* =====================================================
       08. Loading Overlay Public Hooks
       ===================================================== */
    window.showLoading = function () {
        if (CRS.util.qs("#loading-overlay")) {
            return;
        }

        const overlay = document.createElement("div");
        overlay.id = "loading-overlay";
        overlay.style.position = "fixed";
        overlay.style.inset = "0";
        overlay.style.zIndex = "99999";
        overlay.style.display = "flex";
        overlay.style.alignItems = "center";
        overlay.style.justifyContent = "center";
        overlay.style.background = "rgba(255, 255, 255, 0.72)";
        overlay.innerHTML = "<h2>Loading...</h2>";
        document.body.appendChild(overlay);
    };

    window.hideLoading = function () {
        const overlay = CRS.util.qs("#loading-overlay");
        if (overlay) {
            overlay.remove();
        }
    };
})();
