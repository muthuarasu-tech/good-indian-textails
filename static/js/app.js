(function () {
    "use strict";

    const body = document.body;
    const sidebarOpeners = document.querySelectorAll("[data-sidebar-open]");
    const sidebarClosers = document.querySelectorAll("[data-sidebar-close]");

    function openSidebar() {
        body.classList.add("sidebar-open");
    }

    function closeSidebar() {
        body.classList.remove("sidebar-open");
    }

    sidebarOpeners.forEach(function (button) {
        button.addEventListener("click", openSidebar);
    });

    sidebarClosers.forEach(function (element) {
        element.addEventListener("click", closeSidebar);
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeSidebar();
        }
    });

    document.querySelectorAll("[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const message = form.getAttribute("data-confirm");
            if (message && !window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll(".alert-success").forEach(function (alert) {
        window.setTimeout(function () {
            alert.style.transition = "opacity 300ms ease, transform 300ms ease";
            alert.style.opacity = "0";
            alert.style.transform = "translateY(-4px)";
            window.setTimeout(function () {
                alert.remove();
            }, 300);
        }, 6000);
    });
})();
