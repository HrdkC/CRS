(function () {
    "use strict";

    function asNumber(value) {
        var number = Number(value);
        return Number.isFinite(number) ? number : null;
    }

    function setupWizard() {
        var form = document.getElementById("parameter-template-wizard");
        if (!form) {
            return;
        }

        var tagSelect = form.querySelector("#source_tag_id");
        var startInput = form.querySelector("#start_index");
        var endInput = form.querySelector("#end_index");
        var countOutput = form.querySelector("#parameter-template-row-count");
        var messageOutput = form.querySelector("#parameter-template-range-message");
        var submitButton = form.querySelector('button[type="submit"]');

        function selectedTag() {
            return tagSelect && tagSelect.options[tagSelect.selectedIndex];
        }

        function refreshRangeStatus() {
            var option = selectedTag();
            if (!option) {
                countOutput.textContent = "0";
                messageOutput.textContent = "No configured array selected.";
                submitButton.disabled = true;
                return;
            }

            var configuredStart = asNumber(option.dataset.startIndex);
            var configuredEnd = asNumber(option.dataset.endIndex);
            var start = asNumber(startInput.value);
            var end = asNumber(endInput.value);
            var valid = (
                configuredStart !== null &&
                configuredEnd !== null &&
                start !== null &&
                end !== null &&
                start >= configuredStart &&
                end <= configuredEnd &&
                end >= start
            );

            if (!valid) {
                countOutput.textContent = "0";
                messageOutput.textContent = "Range must stay inside " + configuredStart + " to " + configuredEnd + ".";
                messageOutput.classList.add("is-invalid");
                submitButton.disabled = true;
                return;
            }

            var count = end - start + 1;
            countOutput.textContent = String(count);
            messageOutput.textContent = (
                option.dataset.tagName + "[" + start + ".." + end + "] will create only missing rows."
            );
            messageOutput.classList.remove("is-invalid");
            submitButton.disabled = false;
        }

        function applySelectedTagDefaults() {
            var option = selectedTag();
            if (!option) {
                return;
            }
            startInput.value = option.dataset.startIndex || "0";
            endInput.value = option.dataset.endIndex || option.dataset.startIndex || "0";
            startInput.min = option.dataset.startIndex || "0";
            startInput.max = option.dataset.endIndex || "0";
            endInput.min = option.dataset.startIndex || "0";
            endInput.max = option.dataset.endIndex || "0";
            refreshRangeStatus();
        }

        tagSelect.addEventListener("change", applySelectedTagDefaults);
        startInput.addEventListener("input", refreshRangeStatus);
        endInput.addEventListener("input", refreshRangeStatus);
        applySelectedTagDefaults();
    }

    function setupBulkEditor() {
        var form = document.getElementById("parameter-template-bulk-form");
        if (!form) {
            return;
        }

        var rows = Array.prototype.slice.call(form.querySelectorAll("[data-parameter-row]"));
        var hiddenPayload = document.getElementById("parameter-template-changes-json");
        var dirtyOutput = document.getElementById("parameter-template-dirty-count");
        var saveButton = document.getElementById("parameter-template-save-button");
        var reasonInput = document.getElementById("parameter-template-change-reason");

        function rowSnapshot(row) {
            var snapshot = {};
            row.querySelectorAll("[data-template-field]").forEach(function (input) {
                var field = input.dataset.templateField;
                snapshot[field] = input.type === "checkbox" ? input.checked : input.value.trim();
            });
            return snapshot;
        }

        rows.forEach(function (row) {
            row.dataset.originalValues = JSON.stringify(rowSnapshot(row));
        });

        function isDirty(row) {
            return JSON.stringify(rowSnapshot(row)) !== row.dataset.originalValues;
        }

        function updateUsedLabel(row) {
            var checkbox = row.querySelector('[data-template-field="used"]');
            var labelText = row.querySelector(".parameter-template-used-toggle span");
            if (checkbox && labelText) {
                labelText.textContent = checkbox.checked ? "Used" : "Not Used";
            }
            row.classList.toggle("row-inactive", checkbox && !checkbox.checked);
        }

        function refreshDirtyState() {
            var dirtyRows = rows.filter(isDirty);
            rows.forEach(function (row) {
                row.classList.toggle("parameter-template-row-dirty", isDirty(row));
                updateUsedLabel(row);
            });
            if (dirtyOutput) {
                dirtyOutput.textContent = dirtyRows.length + (dirtyRows.length === 1 ? " changed" : " changed");
            }
            if (saveButton) {
                saveButton.disabled = dirtyRows.length === 0;
            }
            return dirtyRows;
        }

        rows.forEach(function (row) {
            row.querySelectorAll("[data-template-field]").forEach(function (input) {
                input.addEventListener("input", refreshDirtyState);
                input.addEventListener("change", refreshDirtyState);
            });
        });

        form.addEventListener("submit", function (event) {
            var dirtyRows = refreshDirtyState();
            if (!dirtyRows.length) {
                event.preventDefault();
                window.alert("No parameter changes were detected.");
                return;
            }

            if (!reasonInput || reasonInput.value.trim().length < 8) {
                event.preventDefault();
                if (reasonInput) {
                    reasonInput.focus();
                }
                return;
            }

            var changes = dirtyRows.map(function (row) {
                var values = rowSnapshot(row);
                values.id = Number(row.dataset.parameterId);
                return values;
            });
            hiddenPayload.value = JSON.stringify(changes);
        });

        refreshDirtyState();
    }

    document.addEventListener("DOMContentLoaded", function () {
        setupWizard();
        setupBulkEditor();
    });
}());
