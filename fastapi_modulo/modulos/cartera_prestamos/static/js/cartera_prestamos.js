(function () {
    function formatNumber(value, options) {
        if (typeof value !== "number") {
            return value;
        }
        return new Intl.NumberFormat("es-MX", options || {
            maximumFractionDigits: 2,
        }).format(value);
    }

    function formatMoney(value) {
        if (typeof value !== "number") {
            return value;
        }
        return new Intl.NumberFormat("es-MX", {
            style: "currency",
            currency: "MXN",
            maximumFractionDigits: 2,
        }).format(value);
    }

    function formatPercent(value, digits) {
        if (typeof value !== "number") {
            return value;
        }
        return (value * 100).toFixed(typeof digits === "number" ? digits : 2) + "%";
    }

    async function fetchJSON(url, options) {
        var response = await fetch(url, options);
        if (!response.ok) {
            throw new Error("No fue posible cargar " + url);
        }
        return response.json();
    }

    async function downloadFile(url, filename) {
        var response = await fetch(url);
        if (!response.ok) {
            throw new Error("No fue posible descargar " + url);
        }
        var blob = await response.blob();
        var link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = filename || "";
        link.click();
        URL.revokeObjectURL(link.href);
    }

    function setText(root, role, value) {
        if (!root) {
            return;
        }
        var node = root.querySelector("[data-role=\"" + role + "\"]");
        if (node) {
            node.textContent = value;
        }
    }

    function exportTableToCsv(selector, filename) {
        var table = document.querySelector(selector);
        if (!table) {
            return;
        }
        var rows = Array.from(table.querySelectorAll("tr")).map(function (row) {
            return Array.from(row.querySelectorAll("th,td")).map(function (cell) {
                return "\"" + cell.textContent.trim().replace(/"/g, "\"\"") + "\"";
            }).join(",");
        });
        var blob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8;" });
        var link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = filename || "export.csv";
        link.click();
        URL.revokeObjectURL(link.href);
    }

    function initTableSearch(scope) {
        Array.from(scope.querySelectorAll("[data-table-search]")).forEach(function (container, index) {
            var table = container.querySelector("table");
            if (!table || container.querySelector(".cp-table-search")) {
                return;
            }
            var label = container.getAttribute("data-table-search") || "Tabla";
            var input = document.createElement("input");
            input.type = "search";
            input.className = "cp-table-search";
            input.placeholder = "Buscar en " + label.toLowerCase();
            input.setAttribute("aria-label", "Buscar en " + label);
            input.style.width = "100%";
            input.style.marginBottom = "12px";
            input.style.padding = "10px 14px";
            input.style.borderRadius = "14px";
            input.style.border = "1px solid rgba(148,163,184,.25)";
            input.style.background = "#fff";
            input.dataset.searchIndex = String(index);
            container.prepend(input);
            input.addEventListener("input", function () {
                var needle = input.value.trim().toLowerCase();
                Array.from(table.tBodies[0].rows).forEach(function (row) {
                    row.style.display = row.textContent.toLowerCase().indexOf(needle) >= 0 ? "" : "none";
                });
            });
        });
    }

    function initExports(scope) {
        Array.from(scope.querySelectorAll("[data-export-target]")).forEach(function (button) {
            button.addEventListener("click", function () {
                var selector = button.getAttribute("data-export-target");
                var filename = button.getAttribute("data-export-filename") || "cartera_prestamos.csv";
                exportTableToCsv(selector, filename);
            });
        });
        Array.from(scope.querySelectorAll("[data-export-url]")).forEach(function (button) {
            button.addEventListener("click", function () {
                var url = button.getAttribute("data-export-url");
                var filename = button.getAttribute("data-export-filename") || "";
                downloadFile(url, filename).catch(console.error);
            });
        });
    }

    function initRefresh(scope) {
        Array.from(scope.querySelectorAll("[data-action=\"refresh\"]")).forEach(function (button) {
            button.addEventListener("click", function () {
                scope.dispatchEvent(new CustomEvent("cp:refresh", { bubbles: true }));
            });
        });
    }

    function mount(scope) {
        initTableSearch(scope);
        initExports(scope);
        initRefresh(scope);
    }

    window.CarteraPrestamosUI = {
        exportTableToCsv: exportTableToCsv,
        fetchJSON: fetchJSON,
        formatMoney: formatMoney,
        formatNumber: formatNumber,
        formatPercent: formatPercent,
        downloadFile: downloadFile,
        mount: mount,
        setText: setText,
    };

    document.addEventListener("DOMContentLoaded", function () {
        window.CarteraPrestamosUI.mount(document);
    });
})();
