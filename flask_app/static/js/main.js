/* =====================================================
   Apollo CRS
   Version 0.1 Beta
   ===================================================== */

document.addEventListener(

    "DOMContentLoaded",

    function () {

        initializeFlashMessages();

        initializeConfirmButtons();

        initializeDropdownMenus();

        initializeCardAnimations();

        initializeSessionCountdown();

        initializeLoginAttemptAlertAcknowledge();

    }

);


/* =====================================================
   Login Attempt Alert Acknowledge
   ===================================================== */

function initializeLoginAttemptAlertAcknowledge() {
    document.addEventListener("submit", async function (event) {
        const form = event.target;

        if (!form || !form.classList || !form.classList.contains("login-attempt-alert-form")) {
            return;
        }

        event.preventDefault();

        const alertCard = form.closest(".login-attempt-alert");
        const button = form.querySelector("button[type='submit']");

        if (button) {
            button.disabled = true;
            button.textContent = "Acknowledging...";
        }

        try {
            const response = await fetch(form.action, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
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
                    button.textContent = "Acknowledge";
                }
                return;
            }

            if (alertCard) {
                alertCard.style.transition = "opacity 0.2s ease, transform 0.2s ease";
                alertCard.style.opacity = "0";
                alertCard.style.transform = "translateY(-6px)";
                setTimeout(function () {
                    alertCard.remove();
                }, 220);
            }
        } catch (error) {
            if (button) {
                button.disabled = false;
                button.textContent = "Acknowledge";
            }
        }
    });
}

/* =====================================================
   Auto Hide Flash Messages
   ===================================================== */

function initializeFlashMessages() {

    const messages = document.querySelectorAll(
        ".flash-message"
    );

    messages.forEach(

        function (message) {

            setTimeout(

                function () {

                    message.style.transition =
                        "opacity 0.5s ease";

                    message.style.opacity = "0";

                    setTimeout(

                        function () {

                            message.remove();

                        },

                        500

                    );

                },

                4000

            );

        }

    );

}

/* =====================================================
   Confirmation Dialog Framework
   ===================================================== */

function initializeConfirmButtons() {

    /*
     * Confirm handling must be submit-safe.
     * Older logic attached a click handler to every [data-confirm] element.
     * When data-confirm was placed on a form, every click inside inputs opened
     * the browser confirm dialog. This version confirms only on actual form
     * submit, and only once per submit attempt.
     */

    const confirmedForms = new WeakSet();

    document.querySelectorAll("form[data-confirm]").forEach(
        function (form) {
            form.addEventListener(
                "submit",
                function (event) {
                    if (confirmedForms.has(form)) {
                        return;
                    }

                    const message = form.getAttribute("data-confirm");

                    if (message && !confirm(message)) {
                        event.preventDefault();
                        return;
                    }

                    confirmedForms.add(form);
                }
            );
        }
    );

    document.querySelectorAll("a[data-confirm], button[data-confirm]").forEach(
        function (element) {
            const parentForm = element.closest("form[data-confirm]");

            if (parentForm && element.type === "submit") {
                return;
            }

            element.addEventListener(
                "click",
                function (event) {
                    const message = element.getAttribute("data-confirm");

                    if (message && !confirm(message)) {
                        event.preventDefault();
                    }
                }
            );
        }
    );

}

/* =====================================================
   Header Dropdown Hold Delay
   ===================================================== */

function initializeDropdownMenus() {

    const dropdowns =
        document.querySelectorAll(
            ".dropdown"
        );

    dropdowns.forEach(

        function (dropdown) {

            let closeTimer = null;

            dropdown.addEventListener(

                "mouseenter",

                function () {

                    if (closeTimer) {

                        clearTimeout(
                            closeTimer
                        );

                    }

                    dropdown.classList.add(
                        "dropdown-open"
                    );

                }

            );

            dropdown.addEventListener(

                "mouseleave",

                function () {

                    closeTimer = setTimeout(

                        function () {

                            dropdown.classList.remove(
                                "dropdown-open"
                            );

                        },

                        850

                    );

                }

            );

        }

    );

}

/* =====================================================
   Dashboard Card Animation
   ===================================================== */

function initializeCardAnimations() {

    const cards =
        document.querySelectorAll(
            ".dashboard-card"
        );

    cards.forEach(

        function (

            card,

            index

        ) {

            card.style.opacity = "0";

            card.style.transform =
                "translateY(15px)";

            setTimeout(

                function () {

                    card.style.transition =
                        "all 0.4s ease";

                    card.style.opacity = "1";

                    card.style.transform =
                        "translateY(0px)";

                },

                index * 100

            );

        }

    );

}

/* =====================================================
   Loading Overlay Support
   ===================================================== */

function showLoading() {

    const existing =
        document.getElementById(
            "loading-overlay"
        );

    if (existing) {

        return;

    }

    const overlay =
        document.createElement("div");

    overlay.id =
        "loading-overlay";

    overlay.style.position =
        "fixed";

    overlay.style.top = "0";

    overlay.style.left = "0";

    overlay.style.width = "100%";

    overlay.style.height = "100%";

    overlay.style.background =
        "rgba(255,255,255,0.7)";

    overlay.style.display =
        "flex";

    overlay.style.justifyContent =
        "center";

    overlay.style.alignItems =
        "center";

    overlay.style.zIndex =
        "9999";

    overlay.innerHTML =
        "<h2>Loading...</h2>";

    document.body.appendChild(
        overlay
    );

}

function hideLoading() {

    const overlay =
        document.getElementById(
            "loading-overlay"
        );

    if (

        overlay

    ) {

        overlay.remove();

    }

}

/* =====================================================
   Future CRS Hooks
   ===================================================== */

/*

Future Features

- PLC Upload Progress
- Dashboard Charts
- Recipe Search
- Live PLC Status
- Approval Workflow Notifications
- User Activity Dashboard

*/


/* =====================================================
   Session Countdown + Heartbeat
   ===================================================== */

function initializeSessionCountdown() {

    const countdown = document.getElementById(
        "session-countdown"
    );

    if (!countdown) {
        return;
    }

    const countdownValue = document.getElementById(
        "session-countdown-value"
    );

    const settingsPreview = document.getElementById(
        "session-settings-countdown"
    );

    let timeoutSeconds = parseInt(
        countdown.getAttribute("data-timeout-seconds") || "1800",
        10
    );

    let lastActivityEpoch = parseInt(
        countdown.getAttribute("data-last-activity-epoch") || "0",
        10
    );

    if (!lastActivityEpoch) {
        lastActivityEpoch = Math.floor(Date.now() / 1000);
    }

    let deadlineEpoch = lastActivityEpoch + timeoutSeconds;
    let lastHeartbeatMs = 0;
    let userActivitySinceHeartbeat = false;
    let expireInProgress = false;
    const heartbeatIntervalMs = 15000;

    function formatSeconds(totalSeconds) {
        totalSeconds = Math.max(0, Math.floor(totalSeconds));

        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;

        return String(minutes).padStart(2, "0") + ":" +
            String(seconds).padStart(2, "0");
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

        countdown.classList.remove(
            "session-countdown-warning",
            "session-countdown-danger"
        );

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

    function showLoginAttemptAlerts(alerts) {
        if (!alerts || !alerts.length) {
            return;
        }

        let stack = document.querySelector(".login-attempt-alert-stack");
        if (!stack) {
            stack = document.createElement("div");
            stack.className = "login-attempt-alert-stack";

            const mainContainer = document.querySelector(".main-container");
            if (mainContainer) {
                mainContainer.prepend(stack);
            } else {
                document.body.appendChild(stack);
            }
        }

        alerts.forEach(function (alert) {
            if (document.querySelector('[data-login-alert-id="' + alert.id + '"]')) {
                return;
            }

            const item = document.createElement("div");
            item.className = "login-attempt-alert";
            item.setAttribute("role", "alert");
            item.setAttribute("data-login-alert-id", alert.id);

            const workstation = alert.attempted_workstation_name || "Unknown workstation";
            const clientIp = alert.attempted_client_ip || "-";
            const attemptedAt = alert.attempted_at || "";

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

    async function heartbeat(forceActivity) {
        const nowMs = Date.now();

        if (!forceActivity && nowMs - lastHeartbeatMs < heartbeatIntervalMs) {
            return;
        }

        lastHeartbeatMs = nowMs;
        const hadUserActivity = Boolean(forceActivity || userActivitySinceHeartbeat);
        userActivitySinceHeartbeat = false;

        try {
            const response = await fetch(
                "/session-heartbeat",
                {
                    method: "POST",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        user_activity: hadUserActivity
                    })
                }
            );

            if (!response.ok) {
                window.location.href = "/login";
                return;
            }

            const payload = await response.json();

            if (!payload.ok) {
                window.location.href = payload.redirect || "/login";
                return;
            }

            timeoutSeconds = parseInt(
                payload.timeout_seconds || timeoutSeconds,
                10
            );

            lastActivityEpoch = parseInt(
                payload.last_activity_epoch || lastActivityEpoch,
                10
            );

            deadlineEpoch = lastActivityEpoch + timeoutSeconds;

            countdown.setAttribute(
                "data-timeout-seconds",
                String(timeoutSeconds)
            );

            countdown.setAttribute(
                "data-last-activity-epoch",
                String(lastActivityEpoch)
            );

            if (payload.login_attempt_alerts) {
                showLoginAttemptAlerts(payload.login_attempt_alerts);
            }

            renderCountdown();
        } catch (error) {
            // Keep local countdown running; server will enforce timeout on next request.
        }
    }

    async function expireSessionFromClientTimer() {
        if (countdownValue) {
            countdownValue.textContent = "00:00";
        }

        try {
            await fetch(
                "/session-auto-expire",
                {
                    method: "POST",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    }
                }
            );
        } catch (error) {
            // Ignore network errors; redirect still protects the UI.
        }

        window.location.href = "/login";
    }

    function markUserActivity() {
        userActivitySinceHeartbeat = true;
    }

    [
        "click",
        "keydown",
        "mousemove",
        "scroll",
        "touchstart"
    ].forEach(
        function (eventName) {
            document.addEventListener(
                eventName,
                markUserActivity,
                { passive: true }
            );
        }
    );

    // Passive heartbeat proves the browser tab is still open, without extending
    // the idle auto-logout timer. User activity is sent separately.
    setInterval(
        function () {
            heartbeat(false);
        },
        heartbeatIntervalMs
    );

    setInterval(
        function () {
            renderCountdown();

            if (userActivitySinceHeartbeat) {
                heartbeat(true);
            }
        },
        1000
    );

    heartbeat(false);
    renderCountdown();
}
