async function loadJSON(p) {
  try { const r = await fetch(p); if (!r.ok) throw 0; return await r.json(); }
  catch { return []; }
}

async function loadText(p) {
  try { const r = await fetch(p); if (!r.ok) throw 0; return await r.text(); }
  catch { return ""; }
}

function primaryId(row) {
  let doi = (row.doi || "").trim().toLowerCase();
  if (doi.startsWith("https://doi.org/")) doi = doi.split("https://doi.org/")[1];
  const ax = (row.arxiv_id || "").trim().toLowerCase();
  return row.primary_id || doi || (ax ? `arxiv:${ax}` : "");
}

function rowYear(row) {
  const p = row.published || "";
  return /^\d{4}/.test(p) ? parseInt(p.slice(0,4), 10) : null;
}

function authorText(row) {
  if (Array.isArray(row.authors)) return row.authors.filter(Boolean).join("; ");
  return row.authors || "";
}

function doiLink(doi) {
  if (!doi) return "";
  const clean = doi.toLowerCase().replace(/^https:\/\/doi\.org\//,"");
  return `<a href="https://doi.org/${clean}" target="_blank" rel="noopener">${clean}</a>`;
}

function arxivLink(ax) {
  if (!ax) return "";
  return `<a href="https://arxiv.org/abs/${ax}" target="_blank" rel="noopener">${ax}</a>`;
}

function buildRow(row) {
  const y = rowYear(row) ?? "";
  const title = row.title || "";
  const authors = authorText(row);
  const venue = row.venue || "";
  const src = row.source || "";
  const idhtml = row.doi ? doiLink(row.doi) : (row.arxiv_id ? arxivLink(row.arxiv_id) : "");
  return `<tr data-year="${y}" data-source="${src}" data-venue="${(venue||"").toLowerCase()}"
              data-pid="${primaryId(row)}">
      <td>${y}</td>
      <td>${title}</td>
      <td>${authors}</td>
      <td>${venue}</td>
      <td>${src}</td>
      <td>${idhtml}</td>
    </tr>`;
}

(async function main(){
  // Show the query (templated by StorageAgent)
  document.getElementById("q").textContent = "{{QUERY}}";

  const data = await loadJSON("results.json");
  const tbody = document.querySelector("#tbl tbody");
  tbody.innerHTML = data.map(buildRow).join("");

  // diff.csv presence?
  const diff = await loadText("diff.csv");
  let newIds = new Set();
  if (diff && diff.trim().length) {
    const lines = diff.split(/\r?\n/);
    const head = (lines.shift() || "").split(",");
    const pidIndex = head.findIndex(h => h.trim().toLowerCase() === "primary_id");
    if (pidIndex >= 0) {
      lines.forEach(line => {
        const cols = line.split(",");
        if (cols[pidIndex]) newIds.add(cols[pidIndex].trim().toLowerCase());
      });
      document.getElementById("dl-diff").classList.remove("hidden");
    }
  }

  // filtering
  function applyFilter(){
    const yMin = parseInt(document.getElementById("year-min").value || "0", 10) || null;
    const yMax = parseInt(document.getElementById("year-max").value || "0", 10) || null;
    const src = (document.getElementById("source").value || "").toLowerCase();
    const vNeedle = (document.getElementById("venue").value || "").toLowerCase();
    const onlyNew = document.getElementById("only-new").checked;

    document.querySelectorAll("#tbl tbody tr").forEach(tr => {
      const y = parseInt(tr.getAttribute("data-year") || "0", 10) || null;
      const s = tr.getAttribute("data-source") || "";
      const v = tr.getAttribute("data-venue") || "";
      const pid = (tr.getAttribute("data-pid") || "").toLowerCase();
      let ok = true;

      if (yMin !== null && (y === null || y < yMin)) ok = false;
      if (yMax !== null && (y === null || y > yMax)) ok = false;
      if (src && s !== src) ok = false;
      if (vNeedle && !v.includes(vNeedle)) ok = false;
      if (onlyNew && !newIds.has(pid)) ok = false;

      tr.style.display = ok ? "" : "none";
    });
  }

  document.getElementById("apply").addEventListener("click", applyFilter);
  document.getElementById("clear").addEventListener("click", () => {
    document.getElementById("year-min").value = "";
    document.getElementById("year-max").value = "";
    document.getElementById("source").value = "";
    document.getElementById("venue").value = "";
    document.getElementById("only-new").checked = false;
    applyFilter();
  });
})();
