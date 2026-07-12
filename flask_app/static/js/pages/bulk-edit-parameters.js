(function () {
    const form = document.getElementById("bulk-parameter-edit-form");
    const table = document.getElementById("bulk-parameter-table");
    const tbody = table ? table.querySelector("tbody") : null;
    const selectAllParameters = document.getElementById("select-all-parameters");
    const visibleCounter = document.getElementById("bulk-visible-counter");
    let currentFilter = "all";
    let currentSortKey = "tag";
    let currentSortDirection = "asc";

    function normalize(value) {
        return (value === null || value === undefined) ? "" : String(value).trim();
    }

    function getRows() {
        if (!tbody) {
            return [];
        }
        return Array.prototype.slice.call(tbody.querySelectorAll("tr[data-bulk-row='1']"));
    }

    function isRowVisible(row) {
        return row && !row.classList.contains("bulk-row-hidden");
    }

    function getVisibleRows() {
        return getRows().filter(isRowVisible);
    }

    function getRowSelector(inputOrRow) {
        const row = inputOrRow && inputOrRow.closest ? inputOrRow.closest("tr") : inputOrRow;
        return row ? row.querySelector(".bulk-row-selector") : null;
    }

    function markRowSelected(inputOrRow) {
        const selector = getRowSelector(inputOrRow);
        if (!selector) {
            return;
        }
        selector.checked = true;
        const row = selector.closest("tr");
        if (row) {
            row.classList.add("bulk-row-dirty");
        }
    }

    function preserveWindowScroll(callback) {
        const scrollX = window.scrollX || window.pageXOffset || 0;
        const scrollY = window.scrollY || window.pageYOffset || 0;
        if (typeof callback === "function") {
            callback();
        }
        window.requestAnimationFrame(function () {
            window.scrollTo(scrollX, scrollY);
            window.setTimeout(function () {
                window.scrollTo(scrollX, scrollY);
            }, 0);
        });
    }

    function parseNumber(value) {
        const n = Number(String(value || "").replace(/,/g, ""));
        return Number.isFinite(n) ? n : null;
    }

    function getSortValue(row, key) {
        const raw = row.dataset[key] || "";
        if (["tag", "plc", "value", "min", "max", "default", "used", "modified"].includes(key)) {
            const n = parseNumber(raw);
            return n === null ? Number.NEGATIVE_INFINITY : n;
        }
        return String(raw).toUpperCase();
    }

    function updateCounter() {
        const count = getVisibleRows().length;
        if (visibleCounter) {
            visibleCounter.textContent = count;
        }
        if (selectAllParameters) {
            const visible = getVisibleRows();
            const selectedVisible = visible.filter(function (row) {
                const selector = getRowSelector(row);
                return selector && selector.checked;
            });
            selectAllParameters.checked = visible.length > 0 && selectedVisible.length === visible.length;
            selectAllParameters.indeterminate = selectedVisible.length > 0 && selectedVisible.length < visible.length;
        }
    }

    function updateRowStatusForUsed(row) {
        const used = row.dataset.used === "1";
        const statusCell = row.querySelector("[data-status-cell]");
        if (!statusCell) {
            return;
        }
        if (!used) {
            statusCell.innerHTML = '<span class="status-badge status-neutral">Inactive</span>';
            row.dataset.status = "inactive";
            row.classList.add("row-inactive");
            return;
        }
        row.classList.remove("row-inactive");
        const originalStatus = row.dataset.modified === "1" ? "modified" : "ok";
        row.dataset.status = originalStatus;
        if (originalStatus === "modified") {
            statusCell.innerHTML = '<span class="status-badge status-warning">Modified</span>';
        } else {
            statusCell.innerHTML = '<span class="status-badge status-success">OK</span>';
        }
    }

    function updateToggleText(input) {
        const label = input.closest(".parameter-used-switch");
        const text = label ? label.querySelector("[data-used-label]") : null;
        if (text) {
            text.textContent = input.checked ? "Used" : "Not Used";
        }
    }

    function updateRowDataFromInput(input) {
        const row = input.closest("tr[data-bulk-row='1']");
        if (!row) {
            return;
        }
        const key = input.dataset.sortKey;
        if (key) {
            row.dataset[key] = input.value || "";
        }
    }

    function updateRowDataFromToggle(input) {
        const row = input.closest("tr[data-bulk-row='1']");
        if (!row) {
            return;
        }
        row.dataset.used = input.checked ? "1" : "0";
        updateToggleText(input);
        updateRowStatusForUsed(row);
    }

    function rowPassesFilter(row, filterName) {
        const selector = getRowSelector(row);
        if (filterName === "used") {
            return row.dataset.used === "1";
        }
        if (filterName === "unused") {
            return row.dataset.used !== "1";
        }
        if (filterName === "modified") {
            return row.dataset.modified === "1" || row.classList.contains("bulk-row-dirty");
        }
        if (filterName === "selected") {
            return !!(selector && selector.checked);
        }
        return true;
    }

    function applyCurrentFilter() {
        getRows().forEach(function (row) {
            if (rowPassesFilter(row, currentFilter)) {
                row.classList.remove("bulk-row-hidden");
            } else {
                row.classList.add("bulk-row-hidden");
            }
        });
        updateCounter();
    }

    function selectChangedRows() {
        document.querySelectorAll(".bulk-edit-track").forEach(function (input) {
            if (normalize(input.value) !== normalize(input.dataset.originalValue)) {
                markRowSelected(input);
            }
        });
        document.querySelectorAll(".bulk-active-toggle").forEach(function (input) {
            const original = normalize(input.dataset.originalChecked);
            const current = input.checked ? "1" : "0";
            if (current !== original) {
                markRowSelected(input);
            }
        });
    }

    function sortRows(sortKey) {
        preserveWindowScroll(function () {
            if (!tbody) {
                return;
            }
            if (currentSortKey === sortKey) {
                currentSortDirection = currentSortDirection === "asc" ? "desc" : "asc";
            } else {
                currentSortKey = sortKey;
                currentSortDirection = "asc";
            }
            document.querySelectorAll(".bulk-sort-button").forEach(function (button) {
                button.classList.remove("sort-asc", "sort-desc");
                if (button.dataset.sortKey === currentSortKey) {
                    button.classList.add(currentSortDirection === "asc" ? "sort-asc" : "sort-desc");
                }
            });
            const rows = getRows();
            rows.sort(function (a, b) {
                const av = getSortValue(a, currentSortKey);
                const bv = getSortValue(b, currentSortKey);
                if (av < bv) {
                    return currentSortDirection === "asc" ? -1 : 1;
                }
                if (av > bv) {
                    return currentSortDirection === "asc" ? 1 : -1;
                }
                return 0;
            });
            rows.forEach(function (row) {
                tbody.appendChild(row);
            });
            applyCurrentFilter();
        });
    }

    function setRowsUsed(rows, used) {
        preserveWindowScroll(function () {
            rows.forEach(function (row) {
                const toggle = row.querySelector(".bulk-active-toggle");
                if (!toggle || toggle.disabled) {
                    return;
                }
                toggle.checked = !!used;
                updateRowDataFromToggle(toggle);
                markRowSelected(row);
            });
            applyCurrentFilter();
        });
    }

    function getSelectedVisibleRows() {
        return getVisibleRows().filter(function (row) {
            const selector = getRowSelector(row);
            return selector && selector.checked;
        });
    }

    if (selectAllParameters) {
        selectAllParameters.addEventListener("change", function () {
            preserveWindowScroll(function () {
                getVisibleRows().forEach(function (row) {
                    const checkbox = getRowSelector(row);
                    if (checkbox) {
                        checkbox.checked = selectAllParameters.checked;
                    }
                });
                updateCounter();
            });
        });
    }

    document.querySelectorAll(".bulk-edit-track").forEach(function (input) {
        input.addEventListener("input", function () {
            updateRowDataFromInput(input);
            markRowSelected(input);
            applyCurrentFilter();
        });
        input.addEventListener("change", function () {
            updateRowDataFromInput(input);
            markRowSelected(input);
            applyCurrentFilter();
        });
    });

    document.querySelectorAll(".bulk-active-toggle").forEach(function (input) {
        input.addEventListener("mousedown", function () {
            input.dataset.scrollYBeforeToggle = String(window.scrollY || window.pageYOffset || 0);
        });
        input.addEventListener("click", function () {
            input.dataset.scrollYBeforeToggle = String(window.scrollY || window.pageYOffset || 0);
        });
        input.addEventListener("change", function () {
            const savedScroll = Number(input.dataset.scrollYBeforeToggle || window.scrollY || window.pageYOffset || 0);
            preserveWindowScroll(function () {
                updateRowDataFromToggle(input);
                markRowSelected(input);
                applyCurrentFilter();
            });
            window.requestAnimationFrame(function () {
                window.scrollTo(0, savedScroll);
                window.setTimeout(function () {
                    window.scrollTo(0, savedScroll);
                }, 0);
            });
        });
    });

    document.querySelectorAll(".bulk-row-selector").forEach(function (checkbox) {
        checkbox.addEventListener("change", function () {
            const row = checkbox.closest("tr[data-bulk-row='1']");
            if (row && checkbox.checked) {
                row.classList.add("bulk-row-dirty");
            }
            applyCurrentFilter();
        });
    });

    document.querySelectorAll(".bulk-chip-button[data-bulk-filter]").forEach(function (button) {
        button.addEventListener("click", function () {
            preserveWindowScroll(function () {
                currentFilter = button.dataset.bulkFilter || "all";
                document.querySelectorAll(".bulk-chip-button[data-bulk-filter]").forEach(function (item) {
                    item.classList.toggle("active", item === button);
                });
                applyCurrentFilter();
            });
        });
    });

    document.querySelectorAll(".bulk-sort-button[data-sort-key]").forEach(function (button) {
        button.addEventListener("click", function () {
            sortRows(button.dataset.sortKey);
        });
    });

    const selectVisibleButton = document.getElementById("bulk-select-visible");
    if (selectVisibleButton) {
        selectVisibleButton.addEventListener("click", function () {
            preserveWindowScroll(function () {
                getVisibleRows().forEach(function (row) {
                    const selector = getRowSelector(row);
                    if (selector) {
                        selector.checked = true;
                        row.classList.add("bulk-row-dirty");
                    }
                });
                updateCounter();
            });
        });
    }

    const clearVisibleButton = document.getElementById("bulk-clear-visible");
    if (clearVisibleButton) {
        clearVisibleButton.addEventListener("click", function () {
            preserveWindowScroll(function () {
                getVisibleRows().forEach(function (row) {
                    const selector = getRowSelector(row);
                    if (selector) {
                        selector.checked = false;
                    }
                });
                updateCounter();
            });
        });
    }

    const markSelectedUsedButton = document.getElementById("bulk-mark-selected-used");
    if (markSelectedUsedButton) {
        markSelectedUsedButton.addEventListener("click", function () {
            setRowsUsed(getSelectedVisibleRows(), true);
        });
    }

    const markSelectedUnusedButton = document.getElementById("bulk-mark-selected-unused");
    if (markSelectedUnusedButton) {
        markSelectedUnusedButton.addEventListener("click", function () {
            setRowsUsed(getSelectedVisibleRows(), false);
        });
    }

    const markVisibleUsedButton = document.getElementById("bulk-mark-visible-used");
    if (markVisibleUsedButton) {
        markVisibleUsedButton.addEventListener("click", function () {
            setRowsUsed(getVisibleRows(), true);
        });
    }

    const markVisibleUnusedButton = document.getElementById("bulk-mark-visible-unused");
    if (markVisibleUnusedButton) {
        markVisibleUnusedButton.addEventListener("click", function () {
            setRowsUsed(getVisibleRows(), false);
        });
    }

    if (form) {
        form.addEventListener("submit", function () {
            selectChangedRows();
        });
    }

    applyCurrentFilter();
})();
