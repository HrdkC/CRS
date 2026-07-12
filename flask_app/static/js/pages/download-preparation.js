
document.addEventListener(
    "DOMContentLoaded",
    function () {

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

            fetch(
                statusUrl,
                {
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    }
                }
            )
                .then(
                    function (response) {
                        return response.json();
                    }
                )
                .then(
                    function (payload) {

                        pollInFlight = false;
                        pollFailureCount = 0;

                        if (!payload.success) {
                            activeStatusUrl = null;
                            renderFailure(
                                payload.message
                                || "Operation status could not be read.",
                                buttons
                            );
                            return;
                        }

                        renderJob(
                            payload.job
                        );

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

                            restoreButtons(
                                buttons
                            );
                            return;
                        }

                        schedulePoll(statusUrl, buttons, 1000);

                    }
                )
                .catch(
                    function (error) {
                        pollInFlight = false;
                        pollFailureCount += 1;
                        updateOperationLockMessage(
                            "Status connection interrupted. CRS is retrying; the PLC operation remains locked."
                        );
                        schedulePoll(
                            statusUrl,
                            buttons,
                            pollFailureCount < 5 ? 1500 : 5000
                        );
                    }
                );

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
