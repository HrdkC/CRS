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

    }

);

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

    const buttons =
        document.querySelectorAll(
            "[data-confirm]"
        );

    buttons.forEach(

        function (button) {

            button.addEventListener(

                "click",

                function (event) {

                    const message =
                        button.getAttribute(
                            "data-confirm"
                        );

                    if (

                        !confirm(message)

                    ) {

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

    async function heartbeat() {
        const nowMs = Date.now();

        if (nowMs - lastHeartbeatMs < 30000) {
            return;
        }

        lastHeartbeatMs = nowMs;
        userActivitySinceHeartbeat = false;

        try {
            const response = await fetch(
                "/session-heartbeat",
                {
                    method: "POST",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    }
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
                payload.last_activity_epoch ||
                Math.floor(Date.now() / 1000),
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
        heartbeat();
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

    setInterval(
        function () {
            renderCountdown();

            if (userActivitySinceHeartbeat) {
                heartbeat();
            }
        },
        1000
    );

    renderCountdown();
}
