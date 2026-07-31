(function () {
    "use strict";

    var action = document.getElementById("plcBufferAction");
    var busyStatus = document.getElementById("plcBufferBusyStatus");

    if (!action || !busyStatus) {
        return;
    }

    var statusUrl = action.dataset.accessStatusUrl || "";
    var refreshMs = Number.parseInt(action.dataset.refreshMs || "2000", 10);
    var requestRunning = false;
    var stopped = false;

    if (!statusUrl) {
        return;
    }

    if (!Number.isFinite(refreshMs) || refreshMs < 1000) {
        refreshMs = 2000;
    }

    function applyAvailability(payload) {
        var available = Boolean(payload && payload.plc_buffer_available);

        action.hidden = !available;
        action.setAttribute("aria-hidden", available ? "false" : "true");
        action.setAttribute("tabindex", available ? "0" : "-1");

        busyStatus.hidden = available;
        busyStatus.textContent = available
            ? "PLC Buffer Available"
            : "PLC Buffer In Use";
    }

    async function refreshAvailability() {
        if (stopped || requestRunning || document.hidden) {
            return;
        }

        requestRunning = true;
        try {
            var response = await fetch(statusUrl, {
                method: "GET",
                credentials: "same-origin",
                cache: "no-store",
                headers: {
                    "Accept": "application/json",
                    "X-CRS-Background": "1"
                }
            });

            if (response.status === 401 || response.status === 403) {
                stopped = true;
                return;
            }

            if (!response.ok) {
                return;
            }

            var payload = await response.json();
            if (payload && payload.success) {
                applyAvailability(payload);
            }
        } catch (_error) {
            // Keep the last known safe state during a temporary network issue.
        } finally {
            requestRunning = false;
        }
    }

    document.addEventListener("visibilitychange", function () {
        if (!document.hidden) {
            refreshAvailability();
        }
    });

    window.setInterval(refreshAvailability, refreshMs);
    refreshAvailability();
}());
