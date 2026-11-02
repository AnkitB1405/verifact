/* VeriFact dashboard.
 *
 * Owner: P2 (FR-53…FR-60). Plain ES modules, no framework and no build step
 * (ADR-007).
 *
 * One rule governs this file: **every number shown comes from the API payload**
 * (FR-56). Nothing is computed, rounded into a different meaning, or inferred
 * here. If a value is not in the response it is not displayed, because a
 * dashboard that invents a figure for a hallucination-detection system would be
 * the one unverified claim in the product.
 */

const $ = (id) => document.getElementById(id);

const STATUSES = [
  "SUPPORTED", "CONTRADICTED", "UNVERIFIABLE",
  "INSUFFICIENT_EVIDENCE", "OUTDATED", "AMBIGUOUS",
];

/** Human wording for each status, matching docs/requirements/verification-statuses.md. */
const MEANING = {
  SUPPORTED: "trusted sources support this",
  CONTRADICTED: "trusted sources contradict this",
  UNVERIFIABLE: "no trusted source covering this was found — it may still be true",
  INSUFFICIENT_EVIDENCE: "sources were found but settle nothing",
  OUTDATED: "supported by older sources; newer ones disagree",
  AMBIGUOUS: "cannot be given one verdict as written",
};

let state = { run: null, claims: [], verdicts: {}, corrections: {}, passages: {} };

const text = (el, value) => { el.textContent = value == null ? "" : String(value); };

function show(id, visible) { $(id).hidden = !visible; }

function fail(message) {
  const box = $("error");
  text(box, message);
  box.hidden = false;
}

function busy(on) {
  show("spinner", on);
  $("run").disabled = on;
  $("run-one").disabled = on;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    // The API returns a typed error body; surface its message, not a raw status.
    throw new Error(body.message || `request failed (${response.status})`);
  }
  return body;
}

/* ---------------------------------------------------------------- rendering */

function renderCounts(counts) {
  const host = $("counts");
  host.replaceChildren();
  STATUSES.filter((s) => counts[s]).forEach((status) => {
    const chip = document.createElement("span");
    chip.className = `chip s-${status}`;
    chip.title = MEANING[status];
    chip.innerHTML = `<b>${counts[status]}</b> ${status.replace(/_/g, " ").toLowerCase()}`;
    host.append(chip);
  });
  if (!host.childElementCount) text(host, "No verdicts yet.");
}

function renderProvenance(run) {
  const p = run.provenance;
  if (!p) { text($("provenance"), ""); return; }
  const models = Object.entries(p.model_versions || {})
    .map(([k, v]) => `${k}=${v}`).join(", ");
  const total = p.timings_ms?.total_ms;
  text(
    $("provenance"),
    `config ${p.config_hash} · ${models}` + (total ? ` · ${Math.round(total)} ms` : ""),
  );
}

function renderClaims() {
  const host = $("claims");
  host.replaceChildren();
  state.claims.forEach((claim, index) => {
    const verdict = state.verdicts[claim.id];
    const li = document.createElement("li");
    li.setAttribute("role", "button");
    li.tabIndex = 0;
    li.dataset.claimId = claim.id;

    const head = document.createElement("div");
    head.className = "claim-head";
    const label = document.createElement("span");
    label.className = "claim-text" + (claim.checkworthy ? "" : " skipped");
    text(label, `${index + 1}. ${claim.text}`);
    head.append(label);

    const badge = document.createElement("span");
    if (verdict) {
      badge.className = `chip s-${verdict.status}`;
      // The confidence wording follows `calibrated` exactly — never "probability".
      const note = verdict.calibrated ? "calibrated" : "uncalibrated";
      badge.innerHTML = `${verdict.status.replace(/_/g, " ").toLowerCase()} ` +
        `<b>${verdict.confidence.toFixed(2)}</b> <small>${note}</small>`;
    } else {
      badge.className = "chip";
      text(badge, claim.checkworthy ? "pending" : `skipped · ${claim.claim_type}`);
    }
    head.append(badge);
    li.append(head);

    li.addEventListener("click", () => selectClaim(claim.id));
    li.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectClaim(claim.id); }
    });
    host.append(li);
  });
  show("claims-view", state.claims.length > 0);
}

function scoreRow(label, value, help) {
  const pct = Math.max(0, Math.min(1, Number(value) || 0));
  return `<tr title="${help || ""}">
    <th>${label}</th>
    <td class="num">${Number(value).toFixed(3)}</td>
    <td><span class="bar"><i style="width:${(pct * 100).toFixed(0)}%"></i></span></td>
  </tr>`;
}

function renderPassages(verdict, passages) {
  const forIds = new Set(verdict.evidence_for || []);
  const againstIds = new Set(verdict.evidence_against || []);
  if (!passages.length) return "<p class='note'>No evidence passages were retrieved.</p>";
  return passages.map((p) => {
    const side = forIds.has(p.id) ? "for" : againstIds.has(p.id) ? "against" : "";
    const role = side === "for" ? "supports" : side === "against" ? "contradicts" : "neutral";
    const date = p.published_at || "undated";
    const link = p.url ? `<a href="${p.url}" target="_blank" rel="noopener">${p.title || p.url}</a>`
                       : (p.title || "(no title)");
    const scores = p.scores || {};
    const detail = [
      `relevance ${(scores.relevance ?? 0).toFixed(2)}`,
      scores.bm25 != null ? `bm25 ${scores.bm25.toFixed(2)}` : null,
      scores.dense != null ? `dense ${scores.dense.toFixed(2)}` : null,
    ].filter(Boolean).join(" · ");
    return `<div class="passage ${side}">
      <div class="meta">${p.source_id} · ${date} · ${role} · ${detail}</div>
      <div>${link}</div>
      <div>${p.text}</div>
    </div>`;
  }).join("");
}

function renderDetail(claim) {
  const verdict = state.verdicts[claim.id];
  const host = $("detail");
  if (!verdict) {
    host.innerHTML = `<p class="note">This claim was not verified (${claim.claim_type}).</p>`;
    show("detail-view", true);
    return;
  }
  const s = verdict.component_scores || {};
  const passages = (state.passages[claim.id] || []);
  const correction = state.corrections[claim.id];
  const kg = verdict.kg_check;

  host.innerHTML = `
    <p><strong>Claim:</strong> ${claim.text}</p>
    <p class="chip s-${verdict.status}">${verdict.status} — ${MEANING[verdict.status]}</p>
    <h3>Why</h3>
    <pre>${verdict.explanation || ""}</pre>
    <h3>Component scores</h3>
    <table>
      <tr><th>signal</th><th class="num">value</th><th></th></tr>
      ${scoreRow("weighted entailment (E)", s.weighted_entail, "Σ w·P(entail) / Σ w")}
      ${scoreRow("weighted contradiction (C)", s.weighted_contra, "Σ w·P(contradict) / Σ w")}
      ${scoreRow("evidence coverage", s.evidence_coverage, "Σ w / k requested")}
      ${scoreRow("similarity (max)", s.similarity_max, "is any passage on topic at all")}
      ${scoreRow("similarity (mean)", s.similarity_mean)}
      ${scoreRow("source reliability", s.source_reliability, "mean registry reliability")}
      ${scoreRow("recency", s.recency, "exponential decay on source half-life")}
      ${scoreRow("cross-source agreement", s.cross_source_agreement, "counted per source, not per passage")}
      <tr title="1 supported, -1 contradicted, 0 missing or not applicable">
        <th>knowledge graph</th><td class="num">${(s.kg_consistency ?? 0).toFixed(0)}</td>
        <td>${kg ? kg.status : "n/a"}</td>
      </tr>
    </table>
    <p class="note">Budget spent: ${verdict.budget_spent} passages ·
      confidence ${verdict.confidence.toFixed(3)}
      (${verdict.calibrated ? "calibrated" : "uncalibrated score, not a probability"})</p>
    ${kg && kg.path_evidence?.length ? `<h3>Knowledge-graph path</h3>
      <div class="kg-path">${kg.path_evidence.flat().join("<br>")}</div>` : ""}
    ${kg?.notes ? `<p class="note">${kg.notes}</p>` : ""}
    <h3>Evidence</h3>
    ${renderPassages(verdict, passages)}
    <h3>Correction</h3>
    ${correction
      ? (correction.abstained
          ? `<p class="note"><strong>Abstained.</strong> ${correction.abstain_reason}</p>`
          : `<p><strong>Proposed:</strong> ${correction.corrected_text}</p>
             <p class="note">Cites ${(correction.citations || []).map((c) => c.source_id).join(", ")}
             · ceiling ${correction.max_supportable_confidence.toFixed(2)}</p>`)
      : "<p class='note'>No correction was attempted.</p>"}
  `;
  show("detail-view", true);
}

function selectClaim(claimId) {
  document.querySelectorAll("#claims li").forEach((li) => {
    li.setAttribute("aria-selected", String(li.dataset.claimId === claimId));
  });
  const claim = state.claims.find((c) => c.id === claimId);
  if (claim) renderDetail(claim);
}

function renderDiff() {
  const rows = state.claims
    .map((c) => [c, state.corrections[c.id]])
    .filter(([, corr]) => corr && !corr.abstained);
  const host = $("diff");
  if (!rows.length) {
    host.innerHTML = "<div><p class='note'>No corrections were proposed. Every claim either " +
      "needed none or the evidence did not supply a grounded replacement.</p></div>";
  } else {
    host.innerHTML = `
      <div><h3>Original</h3>${rows.map(([c]) => `<p><del>${c.text}</del></p>`).join("")}</div>
      <div><h3>Corrected</h3>${rows.map(([, r]) =>
        `<p><ins>${r.corrected_text}</ins></p>`).join("")}</div>`;
  }
  show("diff-view", true);
}

/* ------------------------------------------------------------------ actions */

function ingest(run, statusCounts) {
  state = { run, claims: run.claims || [], verdicts: {}, corrections: {}, passages: {} };
  (run.verdicts || []).forEach((v) => { state.verdicts[v.claim_id] = v; });
  (run.corrections || []).forEach((c) => { state.corrections[c.claim_id] = c; });
  (run.passages || []).forEach((p) => {
    (state.passages[p.claim_id] = state.passages[p.claim_id] || []).push(p);
  });
  renderCounts(statusCounts || {});
  renderProvenance(run);
  text($("annotated"), run.annotated_text || run.document?.normalized_text || "");
  show("summary-view", true);
  renderClaims();
}

async function analyse() {
  $("error").hidden = true;
  busy(true);
  try {
    const body = { text: $("text").value };
    if ($("asof").value) body.asof = $("asof").value;
    const accepted = await api("/api/v1/analyze", { method: "POST", body: JSON.stringify(body) });
    // 202 + poll: a document is tens of seconds of work (ADR-004).
    for (let attempt = 0; attempt < 120; attempt += 1) {
      const result = await api(accepted.poll);
      ingest(result.run, result.status_counts);
      if (!result.partial) break;
      await new Promise((r) => setTimeout(r, 1000));
    }
  } catch (err) {
    fail(err.message);
  } finally {
    busy(false);
  }
}

async function verifyFirst() {
  $("error").hidden = true;
  busy(true);
  try {
    const first = $("text").value.split(/(?<=[.!?])\s+/)[0] || $("text").value;
    const body = { claim: first };
    if ($("asof").value) body.asof = $("asof").value;
    const result = await api("/api/v1/verify", { method: "POST", body: JSON.stringify(body) });
    state = {
      run: null,
      claims: [result.claim],
      verdicts: { [result.claim.id]: result.verdict },
      corrections: {},
      passages: { [result.claim.id]: result.passages },
    };
    renderCounts({ [result.verdict.status]: 1 });
    text($("provenance"), result.confidence_note);
    text($("annotated"), result.claim.text);
    show("summary-view", true);
    renderClaims();
    selectClaim(result.claim.id);
  } catch (err) {
    fail(err.message);
  } finally {
    busy(false);
  }
}

async function exportReport() {
  if (!state.run) { fail("Run a document analysis first."); return; }
  const report = await api(`/api/v1/results/${state.run.id}/export`);
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `verifact-${state.run.id.slice(0, 8)}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
}

$("run").addEventListener("click", analyse);
$("run-one").addEventListener("click", verifyFirst);
$("export").addEventListener("click", exportReport);
$("toggle-diff").addEventListener("click", renderDiff);
