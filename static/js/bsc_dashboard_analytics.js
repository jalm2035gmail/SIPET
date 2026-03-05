(function () {
  "use strict";

  class BscDashboardAnalytics {
    constructor(config) {
      const cfg = config || {};
      this.state = cfg.state || {
        year: new Date().getFullYear(),
        periodLabel: "Ene-Dic",
        axisLabel: "Todos",
        kpis: {
          global: 0,
          metaGlobal: 85,
          objetivos: 0,
          actividades: 0,
          riesgo: 0,
          presEjecutado: 0,
        },
      };
      this.payload = cfg.payload || {};
      this.refs = cfg.refs || {};
      this.charts = [];
    }

    mount() {
      this.renderCharts();
    }

    destroy() {
      this.charts.forEach((chart) => {
        try {
          chart.destroy();
        } catch (_err) {
          // Ignore chart destroy errors to avoid blocking rerender.
        }
      });
      this.charts = [];
    }

    _canvas(name) {
      return this.refs[name] || null;
    }

    _makeChart(canvas, cfg) {
      if (!canvas || !window.Chart) {
        return null;
      }
      const chart = new window.Chart(canvas, cfg);
      this.charts.push(chart);
      return chart;
    }

    renderCharts() {
      if (!window.Chart) {
        return;
      }
      // Disable datalabels globally; enable selectively per chart
      if (window.ChartDataLabels) {
        window.Chart.defaults.set('plugins.datalabels', { display: false });
      }
      this.destroy();

      const payload = this.payload || {};
      const baseOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { boxWidth: 12, color: "#42526e" } },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: "#4b5c77" } },
          y: {
            grid: { color: "rgba(148,163,184,.28)" },
            ticks: { color: "#4b5c77" },
            beginAtZero: true,
            max: 100,
          },
        },
      };

      this._makeChart(this._canvas("trendCanvas"), {
        type: "line",
        data: {
          labels: ((payload.trend && payload.trend.labels) || []),
          datasets: [
            {
              label: "Avance real",
              data: ((payload.trend && payload.trend.real) || []),
              borderColor: "#2e7cc9",
              backgroundColor: "rgba(46,124,201,.18)",
              borderWidth: 2,
              tension: 0.35,
              fill: false,
              pointRadius: 3,
            },
            {
              label: "Avance esperado",
              data: ((payload.trend && payload.trend.expected) || []),
              borderColor: "#72b8bf",
              backgroundColor: "rgba(114,184,191,.16)",
              borderDash: [5, 5],
              borderWidth: 2,
              tension: 0.35,
              fill: false,
              pointRadius: 2,
            },
          ],
        },
        options: Object.assign({}, baseOptions, {
          plugins: Object.assign({}, baseOptions.plugins, {
            annotation: {
              annotations: {
                metaLine: {
                  type: 'line',
                  yMin: (this.state.kpis && this.state.kpis.metaGlobal) || 85,
                  yMax: (this.state.kpis && this.state.kpis.metaGlobal) || 85,
                  borderColor: 'rgba(239,68,68,0.65)',
                  borderWidth: 1.5,
                  borderDash: [6, 4],
                  label: {
                    display: true,
                    content: 'Meta ' + ((this.state.kpis && this.state.kpis.metaGlobal) || 85) + '%',
                    position: 'end',
                    backgroundColor: 'rgba(239,68,68,0.75)',
                    color: '#fff',
                    font: { size: 10, weight: '600' },
                    padding: { x: 6, y: 2 },
                  },
                },
              },
            },
          }),
        }),
      });

      this._makeChart(this._canvas("radarCanvas"), {
        type: "radar",
        data: {
          labels: ((payload.perspectives && payload.perspectives.labels) || []),
          datasets: [
            {
              label: "Avance",
              data: ((payload.perspectives && payload.perspectives.avance) || []),
              borderColor: "#4f89d6",
              backgroundColor: "rgba(79,137,214,.22)",
              borderWidth: 2,
              pointBackgroundColor: "#4f89d6",
            },
            {
              label: "Meta",
              data: ((payload.perspectives && payload.perspectives.meta) || []),
              borderColor: "#86bdbf",
              backgroundColor: "rgba(134,189,191,.14)",
              borderWidth: 1,
              pointRadius: 0,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            r: {
              beginAtZero: true,
              max: 100,
              grid: { color: "rgba(148,163,184,.26)" },
              angleLines: { color: "rgba(148,163,184,.26)" },
              pointLabels: { color: "#455672", font: { size: 12 } },
              ticks: { backdropColor: "transparent", color: "#64748b", stepSize: 20 },
            },
          },
          plugins: { legend: { position: "bottom" } },
        },
      });

      this._makeChart(this._canvas("barsCanvas"), {
        type: "bar",
        data: {
          labels: ((payload.perspectives && payload.perspectives.labels) || []),
          datasets: [
            {
              label: "Avance",
              data: ((payload.perspectives && payload.perspectives.avance) || []),
              backgroundColor: "rgba(113,199,190,.7)",
              borderColor: "rgba(84,163,154,1)",
              borderWidth: 1,
            },
            {
              label: "Meta",
              data: ((payload.perspectives && payload.perspectives.meta) || []),
              backgroundColor: "rgba(82,143,211,.6)",
              borderColor: "rgba(67,121,184,1)",
              borderWidth: 1,
            },
          ],
        },
        options: Object.assign({}, baseOptions, {
          plugins: Object.assign({}, baseOptions.plugins, {
            datalabels: {
              display: true,
              anchor: 'end',
              align: 'end',
              color: '#334155',
              font: { weight: '600', size: 10 },
              formatter: v => v + '%',
            },
          }),
        }),
      });

      this._makeChart(this._canvas("donutCanvas"), {
        type: "doughnut",
        data: {
          labels: ((payload.status && payload.status.labels) || []),
          datasets: [
            {
              data: ((payload.status && payload.status.values) || []),
              backgroundColor: ["#cbd5e1", "#facc15", "#fb923c", "#22c55e", "#ef4444"],
              borderColor: "#ffffff",
              borderWidth: 2,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "62%",
          plugins: {
            legend: { position: "bottom" },
            datalabels: {
              display: true,
              color: '#fff',
              font: { weight: '700', size: 12 },
              formatter: (v, ctx) => {
                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                return total ? Math.round(v / total * 100) + '%' : '';
              },
            },
          },
        },
      });

      this._makeChart(this._canvas("budgetCanvas"), {
        type: "bar",
        data: {
          labels: ((payload.budget && payload.budget.labels) || []),
          datasets: [
            {
              label: "Aprobado",
              data: ((payload.budget && payload.budget.aprobado) || []),
              backgroundColor: "rgba(93,139,213,.7)",
              borderColor: "rgba(70,115,186,1)",
              borderWidth: 1,
            },
            {
              label: "Ejercido",
              data: ((payload.budget && payload.budget.ejercido) || []),
              backgroundColor: "rgba(115,194,178,.7)",
              borderColor: "rgba(80,162,146,1)",
              borderWidth: 1,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "bottom" },
            datalabels: {
              display: true,
              anchor: 'end',
              align: 'end',
              color: '#334155',
              font: { weight: '600', size: 10 },
              formatter: v => (v ? v.toLocaleString() : ''),
            },
          },
          scales: {
            x: { grid: { display: false }, ticks: { color: "#4b5c77" } },
            y: {
              grid: { color: "rgba(148,163,184,.28)" },
              ticks: { color: "#4b5c77" },
              beginAtZero: true,
            },
          },
        },
      });
    }
  }

  window.BscDashboardAnalytics = BscDashboardAnalytics;
})();
