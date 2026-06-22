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
