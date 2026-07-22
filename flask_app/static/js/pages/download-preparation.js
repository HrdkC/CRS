
document.addEventListener(
    "DOMContentLoaded",
    function () {

        var liveStatusPanel = document.getElementById("livePlcStatusPanel");
        var liveStatusTimer = null;
        var liveStatusInFlight = false;
        var liveStatusStopped = false;
        var liveStatusFailureCount = 0;

        function formatLiveValue(value) {
            if (value === null || typeof value === "undefined") {
                return "-";
            }
            if (value === true) {
                return "True";
            }
            if (value === false) {
                return "False";
            }
            return String(value);
        }

        function applyStatusPill(element, status, text) {
            if (!element) {
                return;
            }
            element.classList.remove("status-ready", "status-blocked", "status-neutral");
            if (status === "ok" || status === "READY") {
                element.classList.add("status-ready");
            } else if (status === "bad" || status === "missing" || status === "BLOCKED") {
                element.classList.add("status-blocked");
            } else {
                element.classList.add("status-neutral");
            }
            element.textContent = text;
        }

        function renderLiveStatus(payload) {
            if (!liveStatusPanel || !payload) {
                return;
            }

            liveStatusPanel.classList.remove("is-live-refresh-error");

            var overallPill = document.getElementById("liveStatusOverallPill");
            var overallText = payload.status === "READY"
                ? "LIVE HEALTHY"
                : (payload.status === "BLOCKED" ? "CHECK REQUIRED" : "NOT CHECKED");
            applyStatusPill(overallPill, payload.status, overallText);

            var summary = document.getElementById("liveStatusSummary");
            if (summary) {
                summary.textContent = payload.summary || "Live PLC status updated.";
            }

            var connection = document.getElementById("liveStatusConnection");
            if (connection) {
                connection.textContent = payload.connected ? "PLC connected" : "PLC not connected";
            }

            var updatedAt = document.getElementById("liveStatusUpdatedAt");
            if (updatedAt) {
                updatedAt.textContent = "Updated " + new Date().toLocaleTimeString();
            }

            var itemsByPurpose = {};
            (payload.groups || []).forEach(function (group) {
                (group.items || []).forEach(function (item) {
                    if (item && item.purpose) {
                        itemsByPurpose[item.purpose] = item;
                    }
                });
            });

            var issuesDetails = document.getElementById("liveStatusIssuesDetails");
            var issuesList = document.getElementById("liveStatusIssuesList");
            var issues = Array.isArray(payload.issues) ? payload.issues : [];
            if (issuesDetails && issuesList) {
                issuesList.replaceChildren();
                issues.slice(0, 8).forEach(function (issue) {
                    var listItem = document.createElement("li");
                    listItem.textContent = String(issue);
                    issuesList.appendChild(listItem);
                });
                issuesDetails.hidden = issues.length === 0;
                if (issues.length === 0) {
                    issuesDetails.open = false;
                }
            }

            liveStatusPanel.querySelectorAll("[data-live-purpose]").forEach(function (row) {
                var purpose = row.getAttribute("data-live-purpose");
                var item = itemsByPurpose[purpose];
                if (!item) {
                    return;
                }

                row.classList.remove(
                    "live-status-item-ok",
                    "live-status-item-bad",
                    "live-status-item-missing"
                );
                row.classList.add("live-status-item-" + (item.status || "missing"));

                var value = row.querySelector(".live-status-value");
                if (value) {
                    value.textContent = formatLiveValue(item.value);
                }

                var tagName = row.querySelector(".live-status-tag-name");
                if (tagName) {
                    tagName.textContent = item.tag_name || "Not mapped";
                }

                var expected = row.querySelector(".live-status-expected");
                if (expected) {
                    expected.textContent = "Expected " + (item.expected_text || "Readable");
                }

                var state = row.querySelector(".live-status-state");
                if (state) {
                    state.textContent = item.status_text || "Not Checked";
                }

                var message = row.querySelector(".live-status-message");
                if (message) {
                    message.textContent = item.message || "";
                }

                applyStatusPill(
                    row.querySelector(".live-status-pill"),
                    item.status,
                    item.status_text || "Not Checked"
                );
            });
        }

        function selectedLivePlcId() {
            var select = document.getElementById("bufferPlcSelect");
            return select ? select.value : "";
        }

        function scheduleLiveStatusRefresh(delayMs) {
            if (!liveStatusPanel || liveStatusStopped) {
                return;
            }
            if (liveStatusTimer) {
                window.clearTimeout(liveStatusTimer);
            }
            liveStatusTimer = window.setTimeout(function () {
                liveStatusTimer = null;
                fetchLiveStatus(false);
            }, Math.max(250, delayMs));
        }

        function fetchLiveStatus(manualRefresh) {
            if (!liveStatusPanel || liveStatusStopped || liveStatusInFlight) {
                return;
            }
            if (document.hidden && !manualRefresh) {
                scheduleLiveStatusRefresh(2000);
                return;
            }

            var baseUrl = liveStatusPanel.dataset.liveStatusUrl;
            var plcId = selectedLivePlcId();
            if (!baseUrl || !plcId) {
                return;
            }

            liveStatusInFlight = true;
            var refreshButton = document.getElementById("liveStatusRefreshButton");
            if (refreshButton) {
                refreshButton.classList.add("is-refreshing");
                refreshButton.disabled = true;
            }

            var separator = baseUrl.indexOf("?") >= 0 ? "&" : "?";
            var url = baseUrl + separator
                + "plc_id=" + encodeURIComponent(plcId)
                + "&_=" + Date.now();

            fetch(url, {
                method: "GET",
                credentials: "same-origin",
                cache: "no-store",
                headers: {
                    "Accept": "application/json",
                    "X-CRS-Background": "1"
                }
            })
                .then(function (response) {
                    var contentType = response.headers.get("content-type") || "";
                    if (
                        response.status === 401
                        || response.status === 403
                        || response.redirected
                        || contentType.indexOf("application/json") === -1
                    ) {
                        liveStatusStopped = true;
                    }
                    if (contentType.indexOf("application/json") === -1) {
                        throw new Error("Session ended or server returned a non-JSON response.");
                    }
                    return response.json().then(function (data) {
                        return { response: response, data: data };
                    });
                })
                .then(function (result) {
                    if (!result.response.ok || !result.data.success) {
                        throw new Error(result.data.message || "Live PLC status refresh failed.");
                    }
                    liveStatusFailureCount = 0;
                    renderLiveStatus(result.data.live_status);
                })
                .catch(function (error) {
                    liveStatusFailureCount += 1;
                    liveStatusPanel.classList.add("is-live-refresh-error");
                    var updatedAt = document.getElementById("liveStatusUpdatedAt");
                    if (updatedAt) {
                        updatedAt.textContent = "Refresh unavailable: " + error.message;
                    }
                })
                .finally(function () {
                    liveStatusInFlight = false;
                    if (refreshButton) {
                        refreshButton.classList.remove("is-refreshing");
                        refreshButton.disabled = false;
                    }
                    if (!liveStatusStopped) {
                        var normalDelay = Number(liveStatusPanel.dataset.refreshMs || 2000);
                        var retryDelay = Math.min(15000, normalDelay * Math.max(1, liveStatusFailureCount));
                        scheduleLiveStatusRefresh(retryDelay);
                    }
                });
        }

        if (liveStatusPanel) {
            var liveRefreshButton = document.getElementById("liveStatusRefreshButton");
            var livePlcSelect = document.getElementById("bufferPlcSelect");

            if (liveRefreshButton) {
                liveRefreshButton.addEventListener("click", function () {
                    fetchLiveStatus(true);
                });
            }

            if (livePlcSelect) {
                livePlcSelect.addEventListener("change", function () {
                    liveStatusFailureCount = 0;
                    fetchLiveStatus(true);
                });
            }

            document.addEventListener("visibilitychange", function () {
                if (!document.hidden) {
                    fetchLiveStatus(true);
                }
            });

            window.addEventListener("pagehide", function () {
                liveStatusStopped = true;
                if (liveStatusTimer) {
                    window.clearTimeout(liveStatusTimer);
                }
            });

            scheduleLiveStatusRefresh(Number(liveStatusPanel.dataset.refreshMs || 2000));
        }

        var form = document.getElementById(
            "bufferOperationForm"
        );

        if (!form) {
            return;
        }

        var operationLockActive = false;
        var operationLockReleaseTimer = null;
        var pollTimer = null;
        var activeStatusUrl = null;
        var activeButtons = null;
        var pollInFlight = false;
        var pollFailureCount = 0;

        function blockNavigationWhileRunning(event) {
            if (!operationLockActive) {
                return;
            }

            var target = event.target;
            var link = target && target.closest ? target.closest("a") : null;

            if (link) {
                event.preventDefault();
                event.stopPropagation();
                updateOperationLockMessage(
                    "Operation is still running. Please wait until the result reaches 100% success or failure."
                );
            }
        }

        function blockRefreshKeysWhileRunning(event) {
            if (!operationLockActive) {
                return;
            }

            var key = event.key;
            var isRefresh = key === "F5" || (event.ctrlKey && key && key.toLowerCase() === "r");
            var isBack = event.altKey && key === "ArrowLeft";
            var isForward = event.altKey && key === "ArrowRight";
            var isEscape = key === "Escape";

            if (isRefresh || isBack || isForward || isEscape) {
                event.preventDefault();
                event.stopPropagation();
                updateOperationLockMessage(
                    "Navigation is locked while PLC communication is active. Wait for completion."
                );
            }
        }

        function beforeUnloadWhileRunning(event) {
            if (!operationLockActive) {
                return;
            }

            event.preventDefault();
            event.returnValue = "PLC buffer operation is running. Leaving this page may interrupt operator visibility.";
            return event.returnValue;
        }

        document.addEventListener(
            "click",
            blockNavigationWhileRunning,
            true
        );

        document.addEventListener(
            "keydown",
            blockRefreshKeysWhileRunning,
            true
        );

        window.addEventListener(
            "beforeunload",
            beforeUnloadWhileRunning
        );

        document.addEventListener("visibilitychange", function () {
            if (!document.hidden && operationLockActive && activeStatusUrl) {
                schedulePoll(activeStatusUrl, activeButtons, 0);
            }
        });

        function activateOperationLock(operationTitle) {
            operationLockActive = true;

            if (operationLockReleaseTimer) {
                window.clearTimeout(operationLockReleaseTimer);
                operationLockReleaseTimer = null;
            }

            document.body.classList.add("operation-running");

            var overlay = document.getElementById("operationLockOverlay");
            var title = document.getElementById("operationLockTitle");
            var text = document.getElementById("operationLockText");
            var fill = document.getElementById("operationLockFill");
            var percent = document.getElementById("operationLockPercent");

            if (title) {
                title.textContent = operationTitle || "PLC Buffer Operation Running";
            }

            if (text) {
                text.textContent = "Please wait. Do not refresh, close, go back, or click another menu until this operation finishes with success or failure.";
            }

            if (fill) {
                fill.style.width = "0%";
            }

            if (percent) {
                percent.textContent = "0%";
            }

            if (overlay) {
                overlay.classList.add("is-active");
            }
        }

        function updateOperationLockMessage(message) {
            var text = document.getElementById("operationLockText");
            if (text && message) {
                text.textContent = message;
            }
        }

        function updateOperationLockProgress(percentValue, message) {
            var percent = Number(percentValue || 0);
            if (percent < 0) {
                percent = 0;
            }
            if (percent > 100) {
                percent = 100;
            }

            var fill = document.getElementById("operationLockFill");
            var percentText = document.getElementById("operationLockPercent");

            if (fill) {
                fill.style.width = percent + "%";
            }

            if (percentText) {
                percentText.textContent = percent + "%";
            }

            if (message) {
                updateOperationLockMessage(message);
            }
        }

        function releaseOperationLock(finalStatus, finalMessage) {
            activeStatusUrl = null;
            activeButtons = null;
            pollFailureCount = 0;
            if (pollTimer) {
                window.clearTimeout(pollTimer);
                pollTimer = null;
            }
            updateOperationLockProgress(
                finalStatus === "ERROR" || finalStatus === "BLOCKED" ? 100 : 100,
                finalMessage || "Operation completed. Screen unlocked."
            );

            operationLockReleaseTimer = window.setTimeout(
                function () {
                    operationLockActive = false;
                    document.body.classList.remove("operation-running");

                    var overlay = document.getElementById("operationLockOverlay");
                    if (overlay) {
                        overlay.classList.remove("is-active");
                    }
                },
                900
            );
        }

        form.addEventListener(
            "submit",
            function (event) {

                event.preventDefault();

                var submitter = event.submitter;

                if (!submitter) {
                    return;
                }

                var selectedAction = document.getElementById(
                    "selectedAction"
                );

                if (selectedAction) {
                    selectedAction.value = submitter.value;
                }

                if (
                    submitter.dataset.confirmMessage
                    &&
                    !window.confirm(
                        submitter.dataset.confirmMessage
                    )
                ) {
                    return;
                }

                activateOperationLock(
                    submitter.dataset.loadingTitle
                    || "PLC Buffer Operation"
                );

                var panel = document.getElementById(
                    "liveProgress"
                );

                var title = document.getElementById(
                    "liveProgressTitle"
                );

                var fill = document.getElementById(
                    "liveProgressFill"
                );

                var percentText = document.getElementById(
                    "liveProgressPercent"
                );

                var text = document.getElementById(
                    "liveProgressText"
                );

                var statusContainer = document.getElementById(
                    "liveProgressStatus"
                );

                var metricStrip = document.getElementById(
                    "liveMetricStrip"
                );

                var stepList = document.getElementById(
                    "liveStepList"
                );

                var issueList = document.getElementById(
                    "liveIssueList"
                );

                if (panel) {
                    panel.style.display = "block";
                    panel.classList.remove(
                        "result-success",
                        "result-blocked"
                    );
                }

                var oldResultPanel = document.getElementById(
                    "operationResultPanel"
                );

                if (oldResultPanel) {
                    oldResultPanel.style.display = "none";
                }

                if (title) {
                    title.textContent = (
                        submitter.dataset.loadingTitle
                        || "PLC Buffer Operation"
                    );
                }

                if (text) {
                    text.textContent = (
                        "Backend validation, PLC connection, interlock checks, "
                        + "buffer transfer, and readback verification are running."
                    );
                }

                if (fill) {
                    fill.style.width = "0%";
                }

                if (percentText) {
                    percentText.textContent = "0%";
                }

                if (statusContainer) {
                    statusContainer.innerHTML = "";
                    appendStatusPill(
                        statusContainer,
                        "QUEUED"
                    );
                }

                if (metricStrip) {
                    metricStrip.innerHTML = "";
                    metricStrip.style.display = "none";
                }

                if (stepList) {
                    stepList.innerHTML = "";
                }

                if (issueList) {
                    issueList.innerHTML = "";
                    issueList.style.display = "none";
                }

                var buttons = form.querySelectorAll(
                    "button"
                );

                buttons.forEach(
                    function (button) {
                        button.disabled = true;
                    }
                );

                buttons.forEach(
                    function (button) {
                        if (!button.dataset.originalText) {
                            button.dataset.originalText = button.textContent;
                        }
                    }
                );

                submitter.textContent = "Running...";

                var formData = new FormData(
                    form
                );

                formData.set(
                    "action",
                    submitter.value
                );

                fetch(
                    form.dataset.startUrl,
                    {
                        method: "POST",
                        body: formData,
                        headers: {
                            "X-Requested-With": "XMLHttpRequest"
                        }
                    }
                )
                    .then(
                        function (response) {
                            return response.json().then(
                                function (payload) {
                                    if (!response.ok) {
                                        throw new Error(
                                            payload.message
                                            || "Operation could not start."
                                        );
                                    }
                                    return payload;
                                }
                            );
                        }
                    )
                    .then(
                        function (payload) {
                            pollOperation(
                                payload.status_url,
                                buttons
                            );
                        }
                    )
                    .catch(
                        function (error) {
                            renderFailure(
                                error.message,
                                buttons
                            );
                        }
                    );

            }
        );

        function pollOperation(
            statusUrl,
            buttons
        ) {

            activeStatusUrl = statusUrl;
            activeButtons = buttons;

            if (document.hidden) {
                schedulePoll(statusUrl, buttons, 1500);
                return;
            }

            if (pollInFlight) {
                return;
            }

            pollInFlight = true;

            var separator = statusUrl.indexOf("?") >= 0 ? "&" : "?";
            var requestUrl = statusUrl + separator + "_crs_status_ts=" + Date.now();
            var controller = window.AbortController ? new AbortController() : null;
            var requestTimeout = window.setTimeout(function () {
                if (controller) {
                    controller.abort();
                }
            }, 8000);

            fetch(
                requestUrl,
                {
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "Cache-Control": "no-cache"
                    },
                    credentials: "same-origin",
                    cache: "no-store",
                    signal: controller ? controller.signal : undefined
                }
            )
                .then(function (response) {
                    return response.text().then(function (bodyText) {
                        var payload = null;
                        try {
                            payload = bodyText ? JSON.parse(bodyText) : {};
                        } catch (parseError) {
                            var invalidResponse = new Error(
                                "CRS returned an invalid status response."
                            );
                            invalidResponse.retryable = response.status >= 500;
                            throw invalidResponse;
                        }
                        return {
                            response: response,
                            payload: payload
                        };
                    });
                })
                .then(function (statusResponse) {
                    window.clearTimeout(requestTimeout);
                    pollInFlight = false;

                    var response = statusResponse.response;
                    var payload = statusResponse.payload || {};

                    if (!response.ok) {
                        if (payload.retryable || response.status >= 500) {
                            var retryError = new Error(
                                payload.message
                                || "PLC operation status is temporarily unavailable."
                            );
                            retryError.retryable = true;
                            throw retryError;
                        }

                        activeStatusUrl = null;
                        renderFailure(
                            payload.message
                            || "Operation status could not be read.",
                            buttons
                        );
                        return;
                    }

                    if (!payload.success) {
                        if (payload.retryable) {
                            var payloadRetryError = new Error(
                                payload.message
                                || "PLC operation status is temporarily unavailable."
                            );
                            payloadRetryError.retryable = true;
                            throw payloadRetryError;
                        }

                        activeStatusUrl = null;
                        renderFailure(
                            payload.message
                            || "Operation status could not be read.",
                            buttons
                        );
                        return;
                    }

                    pollFailureCount = 0;
                    renderJob(payload.job);

                    if (payload.done) {
                        var finalStatus = (
                            payload.job
                            && (
                                payload.job.status
                                || (
                                    payload.job.result
                                    && payload.job.result.status
                                )
                            )
                        ) || "SUCCESS";

                        var finalMessage = "Operation finished. Screen unlocked.";

                        if (
                            payload.job
                            && payload.job.result
                            && payload.job.result.current_step
                        ) {
                            finalMessage = payload.job.result.current_step;
                        }

                        releaseOperationLock(
                            finalStatus,
                            finalMessage
                        );

                        restoreButtons(buttons);
                        return;
                    }

                    schedulePoll(statusUrl, buttons, 750);
                })
                .catch(function (error) {
                    window.clearTimeout(requestTimeout);
                    pollInFlight = false;
                    pollFailureCount += 1;

                    var detail = error && error.message
                        ? " " + error.message
                        : "";
                    updateOperationLockMessage(
                        "PLC operation is continuing. CRS is retrying the "
                        + "status connection (attempt " + pollFailureCount + ")."
                        + detail
                    );

                    schedulePoll(
                        statusUrl,
                        buttons,
                        pollFailureCount < 5 ? 1000 : 2500
                    );
                });

        }

        function schedulePoll(statusUrl, buttons, delayMs) {
            if (!operationLockActive || !statusUrl) {
                return;
            }
            if (pollTimer) {
                window.clearTimeout(pollTimer);
            }
            pollTimer = window.setTimeout(function () {
                pollTimer = null;
                pollOperation(statusUrl, buttons);
            }, Math.max(0, Number(delayMs) || 0));
        }

        function renderJob(
            job
        ) {

            var result = job.result || {};

            var status = (
                job.status
                || result.status
                || "RUNNING"
            );

            var percent = Number(
                result.progress_percent
                || job.progress_percent
                || 0
            );

            updateOperationLockProgress(
                percent,
                result.current_step || job.current_step || "PLC operation is running. Please wait."
            );

            var panel = document.getElementById(
                "liveProgress"
            );

            var title = document.getElementById(
                "liveProgressTitle"
            );

            var fill = document.getElementById(
                "liveProgressFill"
            );

            var percentText = document.getElementById(
                "liveProgressPercent"
            );

            var text = document.getElementById(
                "liveProgressText"
            );

            var statusContainer = document.getElementById(
                "liveProgressStatus"
            );

            if (panel) {
                panel.classList.remove(
                    "result-success",
                    "result-blocked"
                );
                if (status == "SUCCESS") {
                    panel.classList.add(
                        "result-success"
                    );
                }
                if (
                    status == "BLOCKED"
                    ||
                    status == "ERROR"
                ) {
                    panel.classList.add(
                        "result-blocked"
                    );
                }
            }

            if (title) {
                title.textContent = (
                    result.title
                    || job.title
                    || "PLC Buffer Operation"
                );
            }

            if (fill) {
                fill.style.width = percent + "%";
            }

            if (percentText) {
                percentText.textContent = percent + "%";
            }

            if (text) {
                text.textContent = (
                    result.current_step
                    || job.current_step
                    || ""
                );
            }

            if (statusContainer) {
                statusContainer.innerHTML = "";
                appendStatusPill(
                    statusContainer,
                    status
                );
            }

            renderSteps(
                result.steps
                || []
            );

            renderMetrics(
                result
            );

            renderIssues(
                result
            );

        }

        function appendStatusPill(
            container,
            status
        ) {

            var pill = document.createElement(
                "span"
            );

            pill.className = "status-pill ";

            if (status == "SUCCESS") {
                pill.className += "status-ready";
            } else if (
                status == "BLOCKED"
                ||
                status == "ERROR"
            ) {
                pill.className += "status-blocked";
            } else {
                pill.className += "status-neutral";
            }

            pill.textContent = status;

            container.appendChild(
                pill
            );

        }

        function renderSteps(
            steps
        ) {

            var stepList = document.getElementById(
                "liveStepList"
            );

            if (!stepList) {
                return;
            }

            stepList.innerHTML = "";

            steps.forEach(
                function (step) {

                    var row = document.createElement(
                        "div"
                    );

                    row.className = "step-item";

                    var percent = document.createElement(
                        "div"
                    );
                    percent.className = "step-percent";
                    percent.textContent = step.percent + "%";

                    var state = document.createElement(
                        "div"
                    );
                    state.className = (
                        "step-state "
                        + (
                            step.status == "OK"
                            ? "step-ok"
                            : "step-failed"
                        )
                    );
                    state.textContent = step.status;

                    var body = document.createElement(
                        "div"
                    );

                    var label = document.createElement(
                        "strong"
                    );
                    label.textContent = step.label;

                    var message = document.createElement(
                        "div"
                    );
                    message.className = "step-message";
                    message.textContent = step.message;

                    body.appendChild(
                        label
                    );
                    body.appendChild(
                        message
                    );

                    row.appendChild(
                        percent
                    );
                    row.appendChild(
                        state
                    );
                    row.appendChild(
                        body
                    );

                    stepList.appendChild(
                        row
                    );

                }
            );

        }

        function renderMetrics(
            result
        ) {

            var metricStrip = document.getElementById(
                "liveMetricStrip"
            );

            if (!metricStrip) {
                return;
            }

            metricStrip.innerHTML = "";

            addMetric(
                metricStrip,
                "DB Changes",
                result.metrics
                &&
                result.metrics.changed_parameters
            );

            addMetric(
                metricStrip,
                "DB Verified",
                result.metrics
                &&
                result.metrics.verified_parameters
            );

            addMetric(
                metricStrip,
                "Upload Candidates",
                result.metrics
                &&
                result.metrics.upload_candidate_changes
            );

            addMetric(
                metricStrip,
                "Upload Validated",
                result.metrics
                &&
                result.metrics.validated_parameters
            );

            if (
                result.payload_compare
                &&
                result.payload_compare.checked
            ) {
                addMetric(
                    metricStrip,
                    "Mismatches",
                    result.payload_compare.mismatch_count
                );
            }

            if (
                result.destination_compare
                &&
                result.destination_compare.checked
            ) {
                addMetric(
                    metricStrip,
                    "PLC Mismatches",
                    result.destination_compare.mismatch_count
                );
            }

            metricStrip.style.display = (
                metricStrip.children.length
                ? "grid"
                : "none"
            );

        }

        function addMetric(
            container,
            labelText,
            value
        ) {

            if (
                value === undefined
                ||
                value === null
            ) {
                return;
            }

            var chip = document.createElement(
                "div"
            );
            chip.className = "metric-chip";

            var label = document.createElement(
                "div"
            );
            label.className = "metric-label";
            label.textContent = labelText;

            var metricValue = document.createElement(
                "div"
            );
            metricValue.className = "metric-value";
            metricValue.textContent = value;

            chip.appendChild(
                label
            );
            chip.appendChild(
                metricValue
            );
            container.appendChild(
                chip
            );

        }

        function renderIssues(
            result
        ) {

            var issueList = document.getElementById(
                "liveIssueList"
            );

            if (!issueList) {
                return;
            }

            issueList.innerHTML = "";

            var issues = [];

            if (result.errors) {
                issues = issues.concat(
                    result.errors
                );
            }

            if (
                result.payload_compare
                &&
                result.payload_compare.mismatches
            ) {
                issues = issues.concat(
                    result.payload_compare.mismatches
                );
            }

            if (
                result.destination_compare
                &&
                result.destination_compare.mismatches
            ) {
                issues = issues.concat(
                    result.destination_compare.mismatches
                );
            }

            if (!issues.length) {
                issueList.style.display = "none";
                return;
            }

            var details = document.createElement(
                "details"
            );
            details.className = "compact-details";
            details.open = true;

            var summary = document.createElement(
                "summary"
            );
            summary.textContent = "Blocking Issues";

            var list = document.createElement(
                "ul"
            );
            list.className = "issue-list";

            issues.slice(
                0,
                10
            ).forEach(
                function (issue) {
                    var item = document.createElement(
                        "li"
                    );
                    item.textContent = issue;
                    list.appendChild(
                        item
                    );
                }
            );

            details.appendChild(
                summary
            );
            details.appendChild(
                list
            );

            issueList.appendChild(
                details
            );
            issueList.style.display = "block";

        }

        function renderFailure(
            message,
            buttons
        ) {

            var panel = document.getElementById(
                "liveProgress"
            );
            var title = document.getElementById(
                "liveProgressTitle"
            );
            var text = document.getElementById(
                "liveProgressText"
            );
            var fill = document.getElementById(
                "liveProgressFill"
            );
            var percentText = document.getElementById(
                "liveProgressPercent"
            );

            if (panel) {
                panel.style.display = "block";
                panel.classList.add(
                    "result-blocked"
                );
            }
            if (title) {
                title.textContent = "PLC Buffer Operation";
            }
            if (text) {
                text.textContent = message;
            }
            if (fill) {
                fill.style.width = "5%";
            }
            if (percentText) {
                percentText.textContent = "5%";
            }

            renderIssues({
                errors: [
                    message
                ]
            });

            releaseOperationLock(
                "ERROR",
                message || "Operation failed. Screen unlocked."
            );

            restoreButtons(
                buttons
            );

        }

        function restoreButtons(
            buttons
        ) {

            buttons.forEach(
                function (button) {
                    button.disabled = false;
                    if (button.dataset.originalText) {
                        button.textContent = button.dataset.originalText;
                    }
                }
            );

        }

    }
);
