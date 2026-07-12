(function () {
    "use strict";

    function syncTarget(select) {
        if (!select || !select.form) return;
        const parts = String(select.value || "").split("|");
        const machineId = select.form.querySelector('input[name="machine_id"]');
        const stageId = select.form.querySelector('input[name="stage_id"]');
        if (machineId) machineId.value = parts.length === 2 ? parts[0] : "";
        if (stageId) stageId.value = parts.length === 2 ? parts[1] : "";
    }

    document.querySelectorAll("select[data-target-sync]").forEach(function (select) {
        select.addEventListener("change", function () {
            syncTarget(select);
        });
        syncTarget(select);
    });

    const form = document.getElementById('recipe-import-mode-form');
    if (!form) return;

    form.addEventListener("submit", function () {
        syncTarget(form.querySelector('select[name="target"]'));
    });

    const createFields = form.querySelector('[data-import-fields="create_new"]');
    const updateFields = form.querySelector('[data-import-fields="update_existing"]');
    const recipeCode = form.querySelector('input[name="recipe_code"]');
    const recipeName = form.querySelector('input[name="recipe_name"]');
    const target = form.querySelector('select[name="target"]');
    const existingRecipe = form.querySelector('select[name="existing_recipe_id"]');

    function selectedMode() {
        const checked = form.querySelector('input[name="import_mode"]:checked');
        return checked ? checked.value : 'create_new';
    }

    function syncMode() {
        const mode = selectedMode();
        const isUpdate = mode === 'update_existing';
        if (createFields) createFields.style.display = isUpdate ? 'none' : '';
        if (updateFields) updateFields.style.display = isUpdate ? '' : 'none';
        if (recipeCode) recipeCode.required = !isUpdate;
        if (recipeName) recipeName.required = !isUpdate;
        if (target) target.required = !isUpdate;
        if (existingRecipe) existingRecipe.required = isUpdate;
    }

    form.querySelectorAll('input[name="import_mode"]').forEach(function (input) {
        input.addEventListener('change', syncMode);
    });
    syncMode();
})();
