(function () {
    async function load() {
        var root = document.querySelector("[data-module-page=\"recuperacion\"]");
        if (!root || !window.CarteraPrestamosUI) {
            return;
        }
        var ui = window.CarteraPrestamosUI;
        var data = await ui.fetchJSON("/api/cartera-prestamos/recuperacion");
        var primerTramo = (data.cartera_vencida_por_tramo || [])[0];

        ui.setText(root, "gestiones_dia", String(data.gestiones_dia || 0));
        ui.setText(root, "visitas_programadas", (data.visitas_programadas || 0) + " visitas programadas");
        ui.setText(root, "promesas_activas", String(data.promesas_pago_activas || 0));
        ui.setText(root, "efectividad_cobranza", "Efectividad " + ui.formatPercent(data.efectividad_cobranza || 0, 2));
        ui.setText(root, "recuperado_periodo", ui.formatMoney((data.recuperado_vs_meta || {}).recuperado || 0));
        ui.setText(root, "avance_meta", "Meta " + ui.formatPercent((data.recuperado_vs_meta || {}).avance || 0, 2));
        ui.setText(root, "casos_criticos_total", String((data.casos_criticos || []).length));
        ui.setText(root, "tramo_principal", primerTramo ? (primerTramo.tramo + " · " + ui.formatMoney(primerTramo.saldo || 0)) : "Sin tramos vencidos");

        var body = root.querySelector("#cp-recuperacion-casos-body");
        if (body && Array.isArray(data.casos_criticos)) {
            body.innerHTML = "";
            data.casos_criticos.slice(0, 10).forEach(function (item) {
                var row = document.createElement("tr");
                row.innerHTML =
                    "<td><div class=\"cp-cobranza-client\">" + item.cliente + "</div></td>" +
                    "<td>" + ui.formatMoney(0) + "</td>" +
                    "<td>" + item.dias_mora + " dias</td>" +
                    "<td><span class=\"cp-cobranza-status is-pink\">" + item.bucket_mora + "</span></td>" +
                    "<td><button type=\"button\" class=\"cp-cobranza-row-btn\">Gestionar</button></td>";
                body.appendChild(row);
            });
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        var root = document.querySelector("[data-module-page=\"recuperacion\"]");
        if (!root) {
            return;
        }
        load().catch(console.error);
        root.addEventListener("cp:refresh", function () {
            load().catch(console.error);
        });
    });
})();
