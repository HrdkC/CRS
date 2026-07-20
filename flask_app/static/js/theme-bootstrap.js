(function () {
    "use strict";
    try {
        var root = document.documentElement;
        var theme = localStorage.getItem("crs-theme") || "system";
        var fontStep = parseInt(localStorage.getItem("crs-font-step") || "0", 10);
        var systemDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;

        if (["system", "light", "dark"].indexOf(theme) === -1) theme = "system";
        if (isNaN(fontStep)) fontStep = 0;
        fontStep = Math.max(-4, Math.min(4, fontStep));

        root.setAttribute("data-crs-theme", theme);
        root.setAttribute("data-crs-resolved-theme", theme === "dark" || (theme === "system" && systemDark) ? "dark" : "light");
        root.setAttribute("data-crs-font-step", String(fontStep));
        root.style.setProperty("--crs-font-adjust", String(fontStep) + "px");
    } catch (error) {
        document.documentElement.setAttribute("data-crs-theme", "system");
        document.documentElement.setAttribute("data-crs-resolved-theme", "light");
    }
})();
