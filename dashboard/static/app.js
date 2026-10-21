// TrafficLens Dashboard Controller JavaScript

let delayEnabled = false;
let stopEnabled = false;
let pollingInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  fetchDashboardData();
  pollingInterval = setInterval(fetchDashboardData, 1000);
});

// Theme Management
function initTheme() {
  const savedTheme = localStorage.getItem("trafficlens_theme") || "light";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeButtonLabel(savedTheme);
}

function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
  const newTheme = currentTheme === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", newTheme);
  localStorage.setItem("trafficlens_theme", newTheme);
  updateThemeButtonLabel(newTheme);
}

function updateThemeButtonLabel(theme) {
  const btn = document.getElementById("btnThemeToggle");
  if (btn) {
    btn.innerHTML = theme === "light" ? "🌙 Dark Mode" : "☀️ Light Mode";
  }
}

// Master Dashboard Refresh
async function fetchDashboardData() {
  const liveDot = document.getElementById("liveDot");
  const liveText = document.getElementById("liveText");

  try {
    const [summaryRes, latencyRes, throughputRes, distRes, statusRes, healthRes, bwRes, connRes] = await Promise.all([
      fetch('/api/summary').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/api/latency-history').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/api/throughput-history').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/api/traffic-distribution').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/api/status-codes').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/api/backend-health').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/api/bandwidth').then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/api/connection-comparison').then(r => r.ok ? r.json() : null).catch(() => null)
    ]);

    const anySuccess = Boolean(summaryRes || latencyRes || throughputRes || distRes || statusRes || healthRes || bwRes || connRes);

    if (anySuccess) {
      if (liveDot && liveText) {
        liveDot.classList.remove("disconnected");
        liveText.innerText = "Live (1s polling)";
      }

      if (summaryRes) updateKPIs(summaryRes);
      if (latencyRes) renderLatencyChart(latencyRes.points || []);
      if (throughputRes) renderThroughputChart(throughputRes.points || []);
      if (distRes) renderTrafficDistribution(distRes.services || []);
      if (statusRes) updateStatusCodes(statusRes.categories || []);
      if (healthRes) updateHealthTable(healthRes.services || []);
      if (bwRes) renderBandwidth(bwRes.services || []);
      if (connRes) updateConnectionComparison(connRes);
    } else {
      if (liveDot && liveText) {
        liveDot.classList.add("disconnected");
        liveText.innerText = "API Disconnected";
      }
    }

  } catch (err) {
    console.warn("Dashboard API polling warning:", err);
    if (liveDot && liveText) {
      liveDot.classList.add("disconnected");
      liveText.innerText = "API Disconnected";
    }
  }
}

// 1. KPI Cards Updates
function updateKPIs(data) {
  document.getElementById("kpiTotalRequests").innerText = Number(data.total_requests || 0).toLocaleString();
  document.getElementById("kpiRps").innerText = Number(data.requests_per_second || 0).toFixed(1);
  document.getElementById("kpiP50").innerText = `${Math.round(data.p50_latency_ms || 0)} ms`;
  document.getElementById("kpiP95").innerText = `${Math.round(data.p95_latency_ms || 0)} ms`;
  document.getElementById("kpiErrorRate").innerText = `${Number(data.error_rate_percent || 0).toFixed(1)}%`;
  
  const bwBytes = data.total_bandwidth_bytes || 0;
  if (bwBytes > 1024 * 1024) {
    document.getElementById("kpiBandwidth").innerText = `${(bwBytes / (1024 * 1024)).toFixed(2)} MB`;
  } else {
    document.getElementById("kpiBandwidth").innerText = `${(bwBytes / 1024).toFixed(1)} KB`;
  }
}

// 2. Latency SVG Chart Renderer
function renderLatencyChart(points) {
  const svg = document.getElementById("latencyChartSvg");
  if (!svg) return;

  if (!points || points.length === 0) {
    svg.innerHTML = '<text x="250" y="90" text-anchor="middle" class="chart-axis-text">No data</text>';
    return;
  }

  const width = 500;
  const height = 180;
  const padding = { top: 15, right: 15, bottom: 25, left: 35 };
  const graphW = width - padding.left - padding.right;
  const graphH = height - padding.top - padding.bottom;

  let maxLat = 10.0;
  points.forEach(p => {
    maxLat = Math.max(maxLat, p.p50_latency_ms, p.p95_latency_ms, p.p99_latency_ms);
  });
  maxLat = Math.ceil(maxLat * 1.15);

  // SVG grid lines
  let innerHtml = `
    <line x1="${padding.left}" y1="${padding.top}" x2="${width - padding.right}" y2="${padding.top}" class="chart-grid-line" />
    <line x1="${padding.left}" y1="${padding.top + graphH / 2}" x2="${width - padding.right}" y2="${padding.top + graphH / 2}" class="chart-grid-line" />
    <line x1="${padding.left}" y1="${padding.top + graphH}" x2="${width - padding.right}" y2="${padding.top + graphH}" class="chart-grid-line" />
    
    <text x="${padding.left - 5}" y="${padding.top + 4}" text-anchor="end" class="chart-axis-text">${maxLat}ms</text>
    <text x="${padding.left - 5}" y="${padding.top + graphH / 2 + 3}" text-anchor="end" class="chart-axis-text">${Math.round(maxLat / 2)}ms</text>
    <text x="${padding.left - 5}" y="${padding.top + graphH}" text-anchor="end" class="chart-axis-text">0ms</text>
  `;

  // Draw lines
  function getPathD(key) {
    return points.map((pt, idx) => {
      const x = padding.left + (idx / Math.max(points.length - 1, 1)) * graphW;
      const val = pt[key] || 0;
      const y = padding.top + graphH - (val / maxLat) * graphH;
      return `${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(" ");
  }

  innerHtml += `<path d="${getPathD('p50_latency_ms')}" fill="none" stroke="var(--secondary-accent)" stroke-width="2" />`;
  innerHtml += `<path d="${getPathD('p95_latency_ms')}" fill="none" stroke="var(--primary-accent)" stroke-width="2" />`;
  innerHtml += `<path d="${getPathD('p99_latency_ms')}" fill="none" stroke="var(--warning-accent)" stroke-width="2" />`;

  svg.innerHTML = innerHtml;
}

// 3. Throughput SVG Chart Renderer
function renderThroughputChart(points) {
  const svg = document.getElementById("throughputChartSvg");
  if (!svg) return;

  if (!points || points.length === 0) {
    svg.innerHTML = '<text x="250" y="90" text-anchor="middle" class="chart-axis-text">No data</text>';
    return;
  }

  const width = 500;
  const height = 180;
  const padding = { top: 15, right: 15, bottom: 25, left: 35 };
  const graphW = width - padding.left - padding.right;
  const graphH = height - padding.top - padding.bottom;

  let maxRps = 5;
  points.forEach(p => { maxRps = Math.max(maxRps, p.requests_per_second); });
  maxRps = Math.ceil(maxRps * 1.2);

  let innerHtml = `
    <line x1="${padding.left}" y1="${padding.top}" x2="${width - padding.right}" y2="${padding.top}" class="chart-grid-line" />
    <line x1="${padding.left}" y1="${padding.top + graphH / 2}" x2="${width - padding.right}" y2="${padding.top + graphH / 2}" class="chart-grid-line" />
    <line x1="${padding.left}" y1="${padding.top + graphH}" x2="${width - padding.right}" y2="${padding.top + graphH}" class="chart-grid-line" />
    
    <text x="${padding.left - 5}" y="${padding.top + 4}" text-anchor="end" class="chart-axis-text">${maxRps}</text>
    <text x="${padding.left - 5}" y="${padding.top + graphH / 2 + 3}" text-anchor="end" class="chart-axis-text">${Math.round(maxRps / 2)}</text>
    <text x="${padding.left - 5}" y="${padding.top + graphH}" text-anchor="end" class="chart-axis-text">0</text>
  `;

  const pathD = points.map((pt, idx) => {
    const x = padding.left + (idx / Math.max(points.length - 1, 1)) * graphW;
    const y = padding.top + graphH - (pt.requests_per_second / maxRps) * graphH;
    return `${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");

  innerHtml += `<path d="${pathD}" fill="none" stroke="var(--primary-accent)" stroke-width="2" />`;
  svg.innerHTML = innerHtml;
}

// 4. Traffic Distribution Progress Bars
function renderTrafficDistribution(services) {
  const container = document.getElementById("trafficDistList");
  if (!container) return;

  if (services.length === 0) {
    container.innerHTML = '<div style="color: var(--muted-text); font-size: 12px;">No endpoint traffic recorded</div>';
    return;
  }

  container.innerHTML = services.map(item => `
    <div class="progress-item">
      <div class="progress-header">
        <span><strong>${item.service}</strong> ${item.endpoint}</span>
        <span>${item.request_count} reqs (${item.percentage}%)</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" style="width: ${item.percentage}%;"></div>
      </div>
    </div>
  `).join("");
}

// 5. Status Codes Distribution
function updateStatusCodes(categories) {
  let p2xx = 0, p429 = 0, p5xx = 0;
  categories.forEach(cat => {
    if (cat.category === "2xx") p2xx = cat.percentage;
    if (cat.category === "429") p429 = cat.percentage;
    if (cat.category === "5xx") p5xx = cat.percentage;
  });

  const s2xx = document.getElementById("seg2xx");
  const s429 = document.getElementById("seg429");
  const s5xx = document.getElementById("seg5xx");

  if (s2xx) s2xx.style.width = `${p2xx}%`;
  if (s429) s429.style.width = `${p429}%`;
  if (s5xx) s5xx.style.width = `${p5xx}%`;

  document.getElementById("lbl2xx").innerText = `${p2xx}%`;
  document.getElementById("lbl429").innerText = `${p429}%`;
  document.getElementById("lbl5xx").innerText = `${p5xx}%`;
}

// 6. Backend Health Table
function updateHealthTable(services) {
  const tbody = document.getElementById("healthTableBody");
  if (!tbody) return;

  if (services.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--muted-text);">No active backends registered</td></tr>';
    return;
  }

  tbody.innerHTML = services.map(item => {
    const badgeClass = item.status.toLowerCase();
    return `
      <tr>
        <td><strong>${item.service}</strong> <br><small style="color: var(--muted-text);">${item.endpoint}</small></td>
        <td><span class="badge ${badgeClass}">${item.status}</span></td>
        <td>${item.request_count}</td>
        <td>${item.average_latency_ms} ms</td>
        <td>${item.error_rate_percent}%</td>
        <td>${item.active_connections}</td>
        <td>${item.rate_limited_count}</td>
      </tr>
    `;
  }).join("");
}

// 7. Connection Comparison
function updateConnectionComparison(data) {
  document.getElementById("compPersistentLat").innerText = `${data.persistent_median_latency_ms} ms`;
  document.getElementById("compNewConnLat").innerText = `${data.new_connection_median_latency_ms} ms`;
  document.getElementById("compDiffVal").innerText = `${data.difference_ms} ms`;
}

// 8. Bandwidth per Endpoint Progress Bars
function renderBandwidth(services) {
  const container = document.getElementById("bandwidthList");
  if (!container) return;

  if (services.length === 0) {
    container.innerHTML = '<div style="color: var(--muted-text); font-size: 12px;">No bandwidth recorded</div>';
    return;
  }

  container.innerHTML = services.map(item => `
    <div class="progress-item">
      <div class="progress-header">
        <span><strong>${item.service}</strong> ${item.endpoint}</span>
        <span>${item.megabytes} MB (${item.percentage}%)</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill secondary" style="width: ${item.percentage}%;"></div>
      </div>
    </div>
  `).join("");
}

// Interactive Experiments Handlers
async function toggleDelayExperiment() {
  const btn = document.getElementById("btnDelayToggle");
  delayEnabled = !delayEnabled;
  
  if (btn) {
    if (delayEnabled) {
      btn.classList.add("active");
      btn.innerText = "Remove delay from Orders";
    } else {
      btn.classList.remove("active");
      btn.innerText = "Add 300 ms delay to Orders";
    }
  }

  try {
    await fetch('/api/experiments/delay', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: delayEnabled, delay_ms: 300 })
    });
  } catch (err) {
    console.error("Failed to toggle delay experiment:", err);
  }
}

async function toggleStopExperiment() {
  const btn = document.getElementById("btnStopToggle");
  stopEnabled = !stopEnabled;

  if (btn) {
    if (stopEnabled) {
      btn.classList.add("active");
      btn.innerText = "Restart Notifications service";
    } else {
      btn.classList.remove("active");
      btn.innerText = "Stop Notifications service";
    }
  }

  try {
    await fetch('/api/experiments/stop-service', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: stopEnabled })
    });
  } catch (err) {
    console.error("Failed to toggle stop experiment:", err);
  }
}
