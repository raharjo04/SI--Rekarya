(function () {
  "use strict";

  const numberFormat = new Intl.NumberFormat("id-ID", {
    maximumFractionDigits: 2,
  });
  const percentFormat = new Intl.NumberFormat("id-ID", {
    maximumFractionDigits: 1,
  });

  function chartOptions() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 250 },
      interaction: { intersect: false, mode: "nearest" },
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: "#334155",
            boxWidth: 12,
            boxHeight: 12,
            padding: 17,
            font: { size: 13, weight: "600" },
          },
        },
        tooltip: {
          backgroundColor: "#fff",
          titleColor: "#1e293b",
          bodyColor: "#334155",
          borderColor: "#cbd5e1",
          borderWidth: 1,
          padding: 11,
          titleFont: { size: 13, weight: "700" },
          bodyFont: { size: 13 },
        },
      },
      scales: {
        x: {
          grid: { color: "#edf1f6" },
          ticks: {
            color: "#475569",
            font: { size: 13 },
            callback: (value) => numberFormat.format(value),
          },
          title: { display: true, color: "#334155", font: { size: 14, weight: "600" } },
        },
        y: {
          grid: { color: "#edf1f6" },
          ticks: {
            color: "#475569",
            font: { size: 13 },
            callback: (value) => numberFormat.format(value),
          },
          title: { display: true, color: "#334155", font: { size: 14, weight: "600" } },
        },
      },
    };
  }

  const projectLabelPlugin = {
    id: "projectLabels",
    afterDatasetsDraw(chart) {
      const dataset = chart.data.datasets[0];
      if (!dataset || !dataset.counts) return;
      const meta = chart.getDatasetMeta(0);
      const { ctx } = chart;
      ctx.save();
      ctx.font = "600 13px Inter, system-ui, sans-serif";
      ctx.fillStyle = "#334155";
      ctx.textBaseline = "middle";
      meta.data.forEach((bar, index) => {
        const label = `${percentFormat.format(dataset.data[index])}% · n=${numberFormat.format(dataset.counts[index])}`;
        ctx.fillText(label, Math.min(bar.x + 7, chart.chartArea.right - 120), bar.y);
      });
      ctx.restore();
    },
  };

  const projectBenchmarkPlugin = {
    id: "projectBenchmark",
    afterDatasetsDraw(chart) {
      const rate = chart.options.plugins.projectBenchmark;
      if (typeof rate !== "number") return;
      const x = chart.scales.x.getPixelForValue(rate);
      if (x < chart.chartArea.left || x > chart.chartArea.right) return;
      const { ctx } = chart;
      ctx.save();
      ctx.strokeStyle = "#1e3a8a";
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 4]);
      ctx.beginPath();
      ctx.moveTo(x, chart.chartArea.top);
      ctx.lineTo(x, chart.chartArea.bottom);
      ctx.stroke();
      ctx.restore();
    },
  };

  const comparisonValuePlugin = {
    id: "comparisonValues",
    afterDatasetsDraw(chart) {
      const { ctx } = chart;
      ctx.save();
      ctx.font = "700 12px Inter, system-ui, sans-serif";
      ctx.fillStyle = "#334155";
      ctx.textBaseline = "middle";
      chart.data.datasets.forEach((dataset, datasetIndex) => {
        chart.getDatasetMeta(datasetIndex).data.forEach((bar, index) => {
          const label = `${numberFormat.format(dataset.data[index])}%`;
          const x = Math.min(
            bar.x + 7,
            chart.width - ctx.measureText(label).width - 5,
          );
          ctx.fillText(label, x, bar.y);
        });
      });
      ctx.restore();
    },
  };

  const centerLabelPlugin = {
    id: "centerLabels",
    afterDatasetsDraw(chart) {
      const { ctx } = chart;
      chart.data.datasets.forEach((dataset, index) => {
        if (!dataset.isCenter) return;
        const point = chart.getDatasetMeta(index).data[0];
        if (!point) return;
        const label = dataset.centerLabel;
        ctx.save();
        ctx.font = "700 12px Inter, system-ui, sans-serif";
        const width = ctx.measureText(label).width + 16;
        const left = point.x - width / 2;
        const top = point.y - 32;
        ctx.fillStyle = "#fff";
        ctx.strokeStyle = dataset.backgroundColor;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.roundRect(left, top, width, 23, 5);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = dataset.backgroundColor;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(label, point.x, top + 12);
        ctx.restore();
      });
    },
  };

  const workloadThresholdPlugin = {
    id: "workloadThreshold",
    beforeDatasetsDraw(chart) {
      const threshold = chart.options.plugins.workloadThreshold;
      if (!threshold || !chart.scales.x || !chart.scales.y) return;
      const x = chart.scales.x.getPixelForValue(threshold.hours);
      const y = chart.scales.y.getPixelForValue(threshold.satisfaction);
      if (
        x < chart.chartArea.left || x > chart.chartArea.right
        || y < chart.chartArea.top || y > chart.chartArea.bottom
      ) return;
      const { ctx } = chart;
      ctx.save();
      ctx.fillStyle = "rgba(185, 28, 28, 0.06)";
      ctx.beginPath();
      ctx.rect(x, y, chart.chartArea.right - x, chart.chartArea.bottom - y);
      ctx.fill();
      ctx.strokeStyle = "#7f1d1d";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([5, 4]);
      ctx.beginPath();
      ctx.moveTo(x, chart.chartArea.top);
      ctx.lineTo(x, chart.chartArea.bottom);
      ctx.moveTo(chart.chartArea.left, y);
      ctx.lineTo(chart.chartArea.right, y);
      ctx.stroke();
      ctx.restore();
    },
  };

  function makeChart(canvas) {
    if (!window.Chart || canvas.chartInstance) return;
    let payload;
    try {
      payload = JSON.parse(canvas.dataset.chartPayload || "null");
    } catch (error) {
      console.error("Data grafik tidak dapat dibaca.", error);
      return;
    }

    const type = canvas.dataset.chart;
    const options = chartOptions();
    let config;
    if (type === "project-turnover") {
      const values = payload.rates;
      const maximum = Math.max(45, Math.ceil(Math.max(...values) / 10) * 10 + 15);
      options.indexAxis = "y";
      options.plugins.legend.display = false;
      options.plugins.projectLabels = true;
      options.plugins.projectBenchmark = payload.overall_rate;
      options.layout = { padding: { right: 112 } };
      options.scales.x.title.text = "Pernah keluar (%)";
      options.scales.x.min = 0;
      options.scales.x.max = maximum;
      options.scales.x.ticks.callback = (value) => `${numberFormat.format(value)}%`;
      options.scales.y.title.display = false;
      options.plugins.tooltip.callbacks = {
        label(context) {
          const count = datasetCount(context.dataset, context.dataIndex);
          return `${percentFormat.format(context.parsed.x)}% karyawan · n=${numberFormat.format(count)}`;
        },
      };
      config = {
        type: "bar",
        data: {
          labels: payload.labels,
          datasets: [{
            data: values,
            counts: payload.counts,
            backgroundColor: values.map((value) => value > 30 ? "#b91c1c" : "#0f766e"),
            borderRadius: 6,
            barPercentage: 0.67,
            clip: false,
          }],
        },
        options,
        plugins: [projectLabelPlugin, projectBenchmarkPlugin],
      };
    } else if (type === "workload-bubbles") {
      options.plugins.legend.display = false;
      options.plugins.workloadThreshold = { hours: 250, satisfaction: 0.4 };
      options.scales.x.title.text = "Jam kerja bulanan";
      options.scales.y.title.text = "Tingkat kepuasan";
      options.scales.x.min = 96;
      options.scales.x.max = 310;
      options.scales.y.min = 0;
      options.scales.y.max = 1;
      options.scales.y.ticks.callback = (value) => numberFormat.format(value);
      options.plugins.tooltip.callbacks = {
        title(context) {
          const point = context[0].raw;
          return `Jam ${point.hourRange} · kepuasan ${point.satisfactionRange}`;
        },
        label(context) {
          const point = context.raw;
          return [
            `${numberFormat.format(point.count)} karyawan;`,
            `${numberFormat.format(point.exits)} pernah keluar (${percentFormat.format(point.exitRate)}%).`,
          ];
        },
      };
      config = {
        type: "bubble",
        data: {
          datasets: [{
            label: "Karyawan per rentang",
            data: payload.points,
            pointBackgroundColor: (context) => `${context.raw.color}B8`,
            pointBorderColor: "#FFFFFF",
            pointBorderWidth: 1,
            pointHoverBorderWidth: 2,
          }],
        },
        options,
        plugins: [workloadThresholdPlugin],
      };
    } else if (type === "persona-map") {
      options.scales.x.title.text = "Peta kemiripan — arah 1";
      options.scales.y.title.text = "Peta kemiripan — arah 2";
      options.plugins.legend.display = false;
      options.plugins.tooltip.callbacks = {
        title(context) {
          const dataset = context[0].dataset;
          if (dataset.isEmployee) return "Karyawan yang dianalisis";
          return dataset.isCenter
            ? `Pusat kelompok — ${dataset.centerLabel}`
            : dataset.label;
        },
        label(context) {
          const dataset = context.dataset;
          if (dataset.isEmployee) return "Profil input untuk dibandingkan.";
          return [
            `${numberFormat.format(dataset.employeeCount)} karyawan (${percentFormat.format(dataset.teamPercentage)}% dari data).`,
            `${percentFormat.format(dataset.turnoverPercent)}% pernah keluar; risiko historis ${dataset.riskLevel.toLowerCase()}.`,
          ];
        },
      };
      config = {
        type: "scatter",
        data: { datasets: payload },
        options,
        plugins: [centerLabelPlugin],
      };
    } else if (type === "employee-comparison") {
      options.indexAxis = "y";
      options.scales.x.title.text = "Profil sebagai % rata-rata kelompok (100% = rata-rata)";
      options.scales.x.beginAtZero = true;
      options.scales.x.max = Math.max(
        130,
        Math.ceil(Math.max(...payload.relative_input) / 10) * 10 + 20,
      );
      options.scales.x.ticks.callback = (value) => `${numberFormat.format(value)}%`;
      options.scales.y.title.display = false;
      options.layout = { padding: { right: 48 } };
      options.plugins.tooltip.callbacks = {
        label(context) {
          const index = context.dataIndex;
          const input = numberFormat.format(payload.input_values[index]);
          const mean = numberFormat.format(payload.group_means[index]);
          return context.datasetIndex === 0
            ? `Input: ${input} · ${numberFormat.format(payload.relative_input[index])}% dari rata-rata (${mean})`
            : `Rata-rata kelompok: ${mean} (100%)`;
        },
      };
      config = {
        type: "bar",
        data: {
          labels: payload.labels,
          datasets: [
            {
              label: "Input karyawan",
              data: payload.relative_input,
              backgroundColor: "#0f766e",
              borderRadius: 4,
            },
            {
              label: "Rata-rata kelompok",
              data: payload.group_average,
              backgroundColor: "#1e3a8a",
              borderRadius: 4,
            },
          ],
        },
        options,
        plugins: [comparisonValuePlugin],
      };
    } else if (type === "persona-distribution") {
      options.plugins.legend.position = "right";
      options.plugins.legend.labels.generateLabels = () => payload.map((item, index) => ({
        text: `${item.label} (${numberFormat.format(item.count)})`,
        fillStyle: item.color,
        strokeStyle: "#fff",
        lineWidth: 1,
        index,
        hidden: false,
      }));
      options.plugins.tooltip.callbacks = {
        label(context) {
          const total = context.dataset.data.reduce((sum, value) => sum + value, 0);
          const proportion = total ? (context.raw / total) * 100 : 0;
          return `${context.label}: ${numberFormat.format(context.raw)} karyawan (${percentFormat.format(proportion)}%)`;
        },
      };
      config = {
        type: "doughnut",
        data: {
          labels: payload.map((item) => item.label),
          datasets: [{
            data: payload.map((item) => item.count),
            backgroundColor: payload.map((item) => item.color),
            borderColor: "#fff",
            borderWidth: 3,
          }],
        },
        options: {
          ...options,
          cutout: "62%",
          scales: {},
        },
      };
    }
    if (config) canvas.chartInstance = new window.Chart(canvas, config);
  }

  function datasetCount(dataset, index) {
    return dataset.counts ? dataset.counts[index] : 0;
  }

  function initializeCharts(root) {
    if (!root || !root.querySelectorAll) return;
    if (root.matches && root.matches("canvas[data-chart]")) makeChart(root);
    root.querySelectorAll("canvas[data-chart]").forEach(makeChart);
  }

  document.addEventListener("DOMContentLoaded", () => initializeCharts(document));
  document.body.addEventListener("htmx:afterSwap", (event) => initializeCharts(event.target));
  document.body.addEventListener("htmx:beforeRequest", (event) => {
    if (!event.detail.elt.closest(".upload-form")) return;
    const steps = document.querySelectorAll("#audit-results .stepper li");
    steps.forEach((step, index) => {
      step.classList.toggle("is-active", index === 1);
      step.classList.toggle("is-complete", index === 0);
      if (index === 1) step.setAttribute("aria-current", "step");
      else step.removeAttribute("aria-current");
    });
  });

  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-tab]").forEach((tab) => {
        const selected = tab === button;
        tab.classList.toggle("is-active", selected);
        tab.setAttribute("aria-selected", String(selected));
      });
      document.querySelectorAll(".tab-panel").forEach((panel) => {
        const selected = panel.id === button.dataset.tab;
        panel.hidden = !selected;
        panel.classList.toggle("is-active", selected);
      });
      initializeCharts(document.getElementById(button.dataset.tab));
    });
  });
})();
