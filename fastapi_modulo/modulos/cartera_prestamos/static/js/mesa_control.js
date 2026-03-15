(function () {
    async function load() {
        var root = document.querySelector("[data-module-page=\"mesa-control\"]");
        if (!root || !window.CarteraPrestamosUI) {
            return;
        }
        var ui = window.CarteraPrestamosUI;
        var data = await ui.fetchJSON("/api/cartera-prestamos/mesa-control");
        var riesgo = Math.min(Math.round((data.indice_morosidad || 0) * 1000), 100);

        ui.setText(root, "riesgo_global", riesgo >= 60 ? "Riesgo alto" : riesgo >= 35 ? "Medio controlado" : "Bajo control");
        ui.setText(root, "indice_morosidad", "Indice de morosidad " + ui.formatPercent(data.indice_morosidad || 0, 2));
        ui.setText(root, "indice_morosidad_score", riesgo + "/100");
        ui.setText(root, "cartera_vencida", ui.formatMoney(data.cartera_vencida || 0));
        ui.setText(root, "casos_criticos", (data.buckets_mora || []).reduce(function (sum, item) { return sum + (item.casos || 0); }, 0) + " casos en buckets");
        ui.setText(root, "cartera_total", ui.formatMoney(data.cartera_total || 0));
        ui.setText(root, "cartera_vigente", "Vigente " + ui.formatMoney(data.cartera_vigente || 0));
        ui.setText(root, "recuperacion_periodo", ui.formatMoney(data.recuperacion_periodo || 0));
        ui.setText(root, "cobertura", "Cobertura " + ui.formatPercent(data.cobertura || 0, 2));

        var bar = root.querySelector("[data-role=\"indice_morosidad_bar\"]");
        if (bar) {
            bar.style.width = Math.max(8, riesgo) + "%";
        }

        var body = root.querySelector("#cp-mesa-casos-body");
        if (body && Array.isArray(data.buckets_mora)) {
            body.innerHTML = "";
            data.buckets_mora.slice(0, 8).forEach(function (item, index) {
                var row = document.createElement("tr");
                row.innerHTML =
                    "<td>Bucket " + item.bucket + "</td>" +
                    "<td>" + (data.saldo_por_sucursal[index] ? data.saldo_por_sucursal[index].nombre : "Sin sucursal") + "</td>" +
                    "<td>" + ui.formatMoney(item.saldo || 0) + "</td>" +
                    "<td>" + (item.casos || 0) + " casos</td>" +
                    "<td><span class=\"cp-mesa-pill is-yellow\">" + (item.bucket || "").replaceAll("_", " ") + "</span></td>";
                body.appendChild(row);
            });
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        var root = document.querySelector("[data-module-page=\"mesa-control\"]");
        if (!root) {
            return;
        }
        load().catch(console.error);
        root.addEventListener("cp:refresh", function () {
            load().catch(console.error);
        });
    });
})();
