(function () {
    async function load() {
        var root = document.querySelector("[data-module-page=\"gestion\"]");
        if (!root || !window.CarteraPrestamosUI) {
            return;
        }
        var ui = window.CarteraPrestamosUI;
        var data = await ui.fetchJSON("/api/cartera-prestamos/gestion");
        var totalPipeline = Object.values(data.pipeline_colocacion || {}).reduce(function (sum, item) { return sum + item; }, 0);
        var scorePromedio = data.score_riesgo ? data.score_riesgo.promedio : 0;

        ui.setText(root, "desembolsos_monto", ui.formatMoney((data.desembolsos_periodo || {}).monto || 0));
        ui.setText(root, "score_promedio", "Score promedio " + scorePromedio);
        ui.setText(root, "pipeline_label", totalPipeline + " expedientes en pipeline");
        ui.setText(root, "renovaciones", String(data.renovaciones || 0));
        ui.setText(root, "doc_incompleta", (data.casos_documentacion_incompleta || 0) + " con documentos pendientes");
        ui.setText(root, "desembolsos_cantidad", String((data.desembolsos_periodo || {}).cantidad || 0));
        ui.setText(root, "reestructuras_periodo", (data.reestructuras_periodo || 0) + " reestructuras del periodo");
        ui.setText(root, "riesgo_promedio", ui.formatNumber(scorePromedio));
        ui.setText(root, "riesgo_distribucion", Object.entries((data.score_riesgo || {}).distribucion || {}).map(function (entry) {
            return entry[0] + ": " + entry[1];
        }).join(" · "));

        var progress = root.querySelector("[data-role=\"pipeline_progress\"]");
        if (progress) {
            progress.style.width = Math.min(100, totalPipeline * 5) + "%";
        }

        var body = root.querySelector("#cp-gestion-expedientes-body");
        if (body && Array.isArray(data.expedientes)) {
            body.innerHTML = "";
            data.expedientes.slice(0, 10).forEach(function (item) {
                var stateClass = item.documentacion_completa ? "is-green" : "is-red";
                var riesgoClass = item.nivel_riesgo === "critico" ? "is-red" : item.nivel_riesgo === "alto" ? "is-orange" : "is-blue";
                var row = document.createElement("tr");
                row.innerHTML =
                    "<td>" + item.cliente + "</td>" +
                    "<td>" + ui.formatNumber(item.score_riesgo) + "</td>" +
                    "<td><span class=\"cp-gestion-pill " + riesgoClass + "\">" + item.nivel_riesgo + "</span></td>" +
                    "<td><span class=\"cp-gestion-pill " + stateClass + "\">" + (item.documentacion_completa ? "Completa" : "Incompleta") + "</span></td>" +
                    "<td><span class=\"cp-gestion-pill is-blue\">Expediente " + item.numero_credito + "</span></td>";
                body.appendChild(row);
            });
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        var root = document.querySelector("[data-module-page=\"gestion\"]");
        if (!root) {
            return;
        }
        load().catch(console.error);
        root.addEventListener("cp:refresh", function () {
            load().catch(console.error);
        });
    });
})();
