// ChainLens frontend — minimal vanilla JS

const $ = (sel) => document.querySelector(sel);

const form = $("#scanForm");
const btn = $("#scanBtn");
const result = $("#result");
const exportBtn = $("#exportBtn");

let lastReport = null;

// Click example to autofill
document.querySelectorAll(".example-input").forEach(el => {
  el.addEventListener("click", () => {
    $("#address").value = el.textContent.trim();
  });
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const address = $("#address").value.trim();
  const chain = $("#chain").value;
  if (!address) return;

  btn.disabled = true;
  btn.textContent = "Analyzing...";
  result.classList.add("hidden");

  try {
    const r = await fetch("/api/scan", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ address, chain }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${r.status}`);
    }
    const data = await r.json();
    lastReport = data;
    render(data);
  } catch (err) {
    alert("Scan failed: " + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Analyze";
  }
});

function render(d) {
  // Verdict badge
  const badge = $("#verdictBadge");
  badge.textContent = `${d.risk_score} (${d.score_value}/100)`;
  badge.dataset.level = d.risk_score;

  // Latency
  $("#latencyTag").textContent = `Type: ${d.metadata?.type || "?"} · ${d.latency_ms}ms`;

  // Summary
  $("#summaryText").textContent = d.summary || "No summary available.";

  // Signals
  const list = $("#signalList");
  list.innerHTML = "";
  $("#signalCount").textContent = `(${d.signals.length})`;
  if (d.signals.length === 0) {
    list.innerHTML = "<li><span class='sig-label muted'>No risk signals detected.</span></li>";
  } else {
    for (const s of d.signals) {
      const li = document.createElement("li");
      li.innerHTML = `
        <span class="sev sev-${s.severity}">${s.severity}</span>
        <span class="sig-label">${escape(s.label)}</span>
        <span class="sig-source">${escape(s.source)}</span>
      `;
      list.appendChild(li);
    }
  }

  // Metadata
  $("#metaJson").textContent = JSON.stringify(d.metadata, null, 2);

  result.classList.remove("hidden");
  result.scrollIntoView({ behavior: "smooth", block: "start" });
}

function escape(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"
  }[c]));
}

exportBtn.addEventListener("click", () => {
  if (!lastReport) return;
  const blob = new Blob([JSON.stringify(lastReport, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `chainlens-${lastReport.address.slice(0,8)}-${Date.now()}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
});
