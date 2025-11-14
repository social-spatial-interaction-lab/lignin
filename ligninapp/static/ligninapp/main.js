// === globals / setup ===
const csrftoken = Cookies.get('csrftoken');
let table;

const findResults = $("#find-results");
const paperTable = $("#paper-table");
const snowballResults = $("#snowball-results");

// --- Busy overlay helpers ---
function showBusy(message) {
  const m = document.getElementById("busyModal");
  if (!m) return;
  const p = m.querySelector(".msg");
  if (p && message) p.textContent = message;
  m.style.display = "block";
}

function hideBusy() {
  const m = document.getElementById("busyModal");
  if (!m) return;
  m.style.display = "none";
}

// The page usually injects questionID in the template; if not, you can extract it from the URL instead.
const questionID = window.questionID || (location.pathname.match(/question\/(\d+)/) || [])[1];

function escapeHtml(s){
  return String(s).replace(/[&<>"]/g, c => (
    { "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[c]
  ));
}

document.getElementById('confirm-generate-btn')?.addEventListener('click', async function () {
  try {
    // Collect column names from the current table
    const columns = (table?.getColumns() || [])
      .map(col => col.getField())
      .filter(f => f && f !== 'entry_id');

    // try extracting file_url (or file_name) from each row as urls.
    const data = table?.getData() || [];
    const urls = data.map(r => r.file_url || r.file || r.url || "").filter(Boolean);

    const res = await fetch(`/question/${questionID}/generate-request-accept/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrftoken,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        columns,
        urls,
      }),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`HTTP ${res.status}: ${text}`);
    }

    const out = await res.json();
    console.log("server response:", out);
    if (out.ok) {
      console.log("[LLM text]:", out.llm_text);
      alert("Generation request accepted — see console for details.");
    } else {
      alert("Server error: " + (out.error || "unknown"));
    }
  } catch (err) {
    console.error(err);
    alert("Failed: " + err.message);
  }
});

function toggleModal(modalId, show) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = show ? 'block' : 'none';
  }
}

$(document).on('click', '#open-question-editor', function () {
  toggleModal("question-editor-modal", true);
});

$(document).ready(() => {
  const addBtn = document.getElementById("add-question-btn");
  const inputBox = document.getElementById("new-question");
  const questionList = document.getElementById("question-list");

  if (addBtn && inputBox && questionList) {
    addBtn.addEventListener("click", () => {
      const questionText = inputBox.value.trim();
      if (!questionText) return;

      const questionEl = document.createElement("div");
      questionEl.className = "question-entry";
      questionEl.innerHTML = `
        <span class="question-text">${questionText}</span>
        <button class="delete-question-btn" style="margin-left: 10px;">❌</button>
      `;

      questionEl.querySelector(".delete-question-btn").addEventListener("click", () => {
        questionList.removeChild(questionEl);
      });

      questionList.appendChild(questionEl);
      inputBox.value = "";
    });
  }

  reloadPapers();
});


function reloadPapers() {
  if (!questionID) { console.warn("reloadPapers(): missing questionID"); return; }

  $.get(`/question/${questionID}/papers/`, {}, function (payload) {
    if (table && typeof table.destroy === "function") {
      try { table.destroy(); } catch (e) {}
      $("#paper-table").empty();
    }

    const meta = Array.isArray(payload.columns_meta) ? payload.columns_meta : null;
    const fieldToColId = Object.fromEntries(
      (meta || []).map(({ id, name }) => [name, id])
    );
    // --- DEBUG: inspect column id mapping ---
    window.DEBUG_EDITED = true; // turn off by setting false
    if (window.DEBUG_EDITED) {
      try {
        console.group("[EditedDebug] fieldToColId mapping");
        console.table((meta || []).map(({ id, name, title }) => ({ field: name, column_pk: id, title })));
        console.log("fieldToColId keys:", Object.keys(fieldToColId));
        console.groupEnd();
      } catch (e) { console.warn("[EditedDebug] mapping log failed", e); }
  }
    // NEW: Cache the edited_map returned by the backend (sparse structure)
    const editedMap = (payload && payload.edited_map) ? payload.edited_map : {};
    const isEdited = (entryId, field) => {
      const m = editedMap[String(entryId)];
      return !!(m && m[field] === true);
    };
    window.isEdited = isEdited;
    const setEdited = (entryId, field, bool) => {
      const key = String(entryId);
      if (!editedMap[key]) editedMap[key] = {};
      if (bool) editedMap[key][field] = true;
      else delete editedMap[key][field]; // Sparse structure: remove the key directly when false
    };

    // NEW: Utility – render an “Edited” badge at the bottom-left of a cell (hover → ✕, click → unlock)
    function renderEditedBadge(cell) {
      const colDef  = cell.getColumn().getDefinition();
      const field   = colDef.field;
      const rowData = cell.getRow().getData();
      const entryId = rowData.entry_id;
      console.debug("11");
      if (!entryId || !field || field === "file_name") return;
      const el = cell.getElement();
      // If not locked, remove any existing badge

      if (!isEdited(entryId, field)) {
        const prev = cell.getElement().querySelector(".cell-edited-badge");
        if (prev) {
          console.debug("[EditedBadge] removed");
          prev.remove();
          el.classList.remove("has-edited-badge");
          el.style.removeProperty("--edited-badge-space");
        }
        return;
      }

      // If locked: create a badge if none exists
      let badge = cell.getElement().querySelector(".cell-edited-badge");
      if (!badge) {
        badge = document.createElement("span");
        badge.className = "cell-edited-badge";
        badge.textContent = "Edited";
        console.debug("badge created");
        // Simple inline styles (can be moved to CSS)
        Object.assign(badge.style, {
          position: "absolute",
          left: "4px",
          bottom: "2px",
          fontSize: "11px",
          padding: "0 6px",
          lineHeight: "16px",
          border: "1px solid #bbb",
          borderRadius: "10px",
          background: "#f5f5f5",
          color: "#444",
          cursor: "pointer",
          userSelect: "none",
          zIndex: "100  ",
          pointerEvents: "auto",
        });
        badge.addEventListener("mouseenter", () => { badge.textContent = "✕"; });
        badge.addEventListener("mouseleave", () => { badge.textContent = "Edited"; });

        // NEW 1: 提前在捕获阶段拦住按下事件，避免单元格先进入编辑
        badge.addEventListener("pointerdown", (ev) => {
          ev.preventDefault();
          ev.stopPropagation();
        }, { capture: true });

        badge.addEventListener("click", async (ev) => {
          ev.preventDefault(); ev.stopPropagation();

          const colId = fieldToColId[field];
          // --- DEBUG: log click context ---
          if (window.DEBUG_EDITED) {
            console.debug("[EditedDebug] click badge", { entryId, field, colId, knownFields: Object.keys(fieldToColId) });
          }

          // 强制在解析失败时给出提示，并阻止误删徽标
          if (!colId) {
            console.error(`[EditedDebug] Missing column_pk for field="${field}". Known fields:`, Object.keys(fieldToColId));
            alert(`Cannot unlock: missing backend column id for field "${field}".`);
            return;
          }
          const url = `/values/${encodeURIComponent(entryId)}/${encodeURIComponent(colId)}/edited/`;
          try {
            //const res = await fetch(`/values/${encodeURIComponent(entryId)}/${encodeURIComponent(colId)}/edited/`, {
            const res = await fetch(url, {
              method: "POST",
              headers: { "X-CSRFToken": csrftoken, "Content-Type": "application/json" },
              body: JSON.stringify({ edited: false }),
            });


            const raw = await res.clone().text(); // 先读原文，方便排查 302/HTML 等情况
            let out = null;
            try { out = JSON.parse(raw); } catch (_) {}

            if (window.DEBUG_EDITED) {
              console.debug("[EditedDebug] response", { status: res.status, ok: res.ok, out, rawSnippet: raw?.slice(0, 200) });
            }

            //if (!res.ok) throw new Error(`HTTP ${res.status}`);
            //const out = await res.json();
            if (res.ok && out && out.ok && out.edited === false) {
              setEdited(entryId, field, false);
              badge.remove();
              el.classList.remove("has-edited-badge");
              el.style.removeProperty("--edited-badge-space");
            } else {
              console.warn("unlock failed payload:", out);
              alert((out && out.error) || "Failed to unlock this cell.");
            }
          } catch (e) {
            console.error("unlock failed", e);
            alert("Unlock failed: " + e.message);
          }
        });
        // The container must be set to relative positioning to place the absolutely positioned badge
        //const el = cell.getElement();
        if (getComputedStyle(el).position === "static") el.style.position = "relative";
        el.appendChild(badge);
      }
      el.classList.add("has-edited-badge");
      const h = Math.ceil((badge.offsetHeight || 18) + 4);
      el.style.setProperty("--edited-badge-space", `${h}px`);
    }


    const dynamicCols = meta
      ? meta.map(({ id, name }) => {
          const titleText = (name === "file_name") ? "File name" : name;

          // If this is the "File name" column, return a custom formatter that adds a hyperlink
          if (name === "file_name") {
            return {
              title: titleText,
              field: name,
              editor: false,
              formatter: function(cell) {
                const fileName = cell.getValue();
                if (!fileName) return "";
                const link = document.createElement("a");
                link.textContent = fileName;
                link.href = "#";
                link.style.color = "#007bff";
                link.style.textDecoration = "underline";
                link.addEventListener("click", function (e) {
                  e.preventDefault();
                  const rowData = cell.getRow().getData();
                  const entryId = rowData.entry_id;
                  const fileUrl = `/media/uploaded_papers/${encodeURIComponent(fileName)}`;
                  openPaperModal({
                    id: entryId,
                    url: fileUrl,
                    name: fileName,
                    abstract: ""
                  });
                });
                return link;
              },
              titleFormatter: function() {
                const span = document.createElement('span');
                span.textContent = titleText;
                span.style.fontWeight = 'bold';
                return span;
              }
            };
          }

          // Otherwise, follow the original logic (with a delete button)
          return {
            title: titleText,
            field: name,
            editor: "input",

            // Render a title and a small button in the column header
            titleFormatter: function(cell, formatterParams, onRendered) {
              // Determine whether the column is protected
              if (name === "file_name" || titleText === "File name") {
                // Return only the title text, do not render the button
                const span = document.createElement('span');
                span.textContent = titleText;
                span.style.fontWeight = 'bold';
                return span;
              }
              const wrap = document.createElement('div');
              wrap.style.display = 'flex';
              wrap.style.alignItems = 'center';
              wrap.style.gap = '6px';

              const span = document.createElement('span');
              span.textContent = titleText;

              const btn = document.createElement('button');
              btn.textContent = '✕';
              btn.title = 'Remove this column from this review';
              btn.style.padding = '0 6px';
              btn.style.lineHeight = '18px';
              btn.style.color = '#b00';
              btn.style.background = '#f7f7f7'
              btn.style.border = '1px solid #ccc';
              btn.style.borderRadius = '4px';
              btn.style.background = '#f7f7f7';
              btn.style.cursor = 'pointer';

              btn.addEventListener('click', async (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                if (!confirm(`Remove column "${name}" from this review? This will delete its cells in this review.`)) return;
                try {
                  const res = await fetch(`/review/${encodeURIComponent(questionID)}/columns/${encodeURIComponent(id)}/remove/`, {
                    method: "POST",
                    headers: { "X-CSRFToken": csrftoken },
                  });
                  if (!res.ok) {
                    const txt = await res.text();
                    throw new Error(`HTTP ${res.status}: ${txt}`);
                  }
                  const out = await res.json();
                  if (out.ok) {
                    reloadPapers();
                  } else {
                    alert(out.error || "Failed to remove column.");
                  }
                } catch (err) {
                  console.error(err);
                  alert("Remove failed: " + err.message);
                }
              });

              wrap.appendChild(span);
              wrap.appendChild(btn);
              return wrap;
            }
          };
        })
      : (Array.isArray(payload.columns) ? payload.columns.map((name) => ({
          title: (name === "file_name") ? "File name" : name,
          field: name,
          editor: false,
        })) : []);


    const deleteColumn = {
      title: "", // Do not display a header title
      field: "delete",
      width: 50,
      hozAlign: "center",
      formatter: function(cell) {
        const btn = document.createElement("button");
        btn.textContent = "✕";
        btn.title = "Remove this row (entry)";
        btn.style.color = "#a00";
        btn.style.background = "#fff";
        btn.style.border = "1px solid #ccc";
        btn.style.borderRadius = "4px";
        btn.style.cursor = "pointer";
        btn.style.fontWeight = "bold";
        btn.addEventListener("mouseenter", () => btn.style.background = "#eee");
        btn.addEventListener("mouseleave", () => btn.style.background = "#fff");
        
        btn.addEventListener("click", async (ev) => {
          ev.preventDefault();
          ev.stopPropagation();
        
          const row = cell.getRow();
          const data = row.getData();
          const entryId = data.entry_id;
          if (!entryId) return;
        
          if (!confirm(`Delete entry #${entryId}? This will remove the row and its values.`)) return;
        
          try {
            const res = await fetch(`/review/${encodeURIComponent(questionID)}/entries/${encodeURIComponent(entryId)}/remove/`, {
              method: "POST",
              headers: { "X-CSRFToken": csrftoken },
            });
            const out = await res.json();
            if (out.ok) {
              row.delete(); // Immediately remove from frontend
              console.log(`Entry ${entryId} removed.`);
            } else {
              alert(out.error || "Failed to delete row.");
            }
          } catch (err) {
            console.error(err);
            alert("Delete failed: " + err.message);
          }
        });
        
        return btn;
      }
    };
        



    
    const columns = [
      deleteColumn,
      { title: "Entry ID", field: "entry_id", visible: false },
      ...dynamicCols
    ];

    table = new Tabulator("#paper-table", {
      height: "80vh",
      data: Array.isArray(payload.rows) ? payload.rows : [],
      layout: "fitColumns",
      renderHorizontal: "virtual",
      variableHeight: true,
      columns,
      rowFormatter: function(row) {
        const cells = row.getCells();
    
        cells.forEach(function(cell) {
          const colDef = cell.getColumn().getDefinition();
          const field  = colDef && colDef.field;
    
          // Skip non-data / special columns
          if (!field || field === "file_name") return;
          if (!colDef.editor) return;  // only for editable columns
    
          if (window.DEBUG_EDITED) {
            const entryId = cell.getRow().getData().entry_id;
            console.debug("[EditedDebug] rowFormatter for cell", {
              field,
              entryId,
              isEditedFlag: isEdited(entryId, field),
            });
          }
    
          // This will check isEdited(...) internally and add/remove the badge
          renderEditedBadge(cell);
        });
      },
    });
    let reverting = false; //  Placed in module scope

    table.on("cellEdited", async function (cell) {

      if (reverting) return;  //  Prevent rollback from triggering again
    
      const colDef  = cell.getColumn().getDefinition();
      const field   = colDef.field;
      const colId   = fieldToColId[field];  // Retrieve backend column ID via column name
      const rowData = cell.getRow().getData();
      const entryId = rowData.entry_id;

      if (!entryId || !colId || field === "file_name") return;
    
      const newVal = cell.getValue();
      const oldVal = cell.getOldValue();
    
      try {
        const res = await fetch(`/values/${encodeURIComponent(entryId)}/${encodeURIComponent(colId)}/`, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrftoken,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            value: (newVal ?? "").toString(),
            notes: "",
            lock_after_save: true
          }),
        });
    
        if (!res.ok) {
          //  Use restoreOldValue() and a flag to prevent triggering cellEdited again
          reverting = true;
          cell.restoreOldValue();
          reverting = false;
    
          const text = await res.text();
          throw new Error(`HTTP ${res.status}: ${text}`);
        }

        //renderEditedBadge(cell);
        setEdited(entryId, field, true); 
        renderEditedBadge(cell);  
        // NEW: After successful save, explicitly set the lock (the backend also defaults to true, but this explicit call ensures immediate frontend sync)
        //try {
          //const res2 = await fetch(`/values/${encodeURIComponent(entryId)}/${encodeURIComponent(colId)}/edited/`, {
            //method: "POST",
            //headers: { "X-CSRFToken": csrftoken, "Content-Type": "application/json" },
            //body: JSON.stringify({ edited: true }),
          //});
          //const out2 = await res2.json().catch(() => ({}));
          //if (res2.ok && out2 && out2.ok) {
            //setEdited(entryId, field, true);
            // Re-render the badge (the cell DOM still exists)
            //renderEditedBadge(cell);
          //} else {
            //console.warn("set edited=true failed", res2.status, out2);
          //}
        //} catch (e) {
          //console.warn("set edited=true error", e);
        //}

      } catch (err) {
        console.error("[save cell] failed:", err);
        alert("save failed" + err.message);
      }
    });
    
  }, 'json');
}

function renderQATable(answerList) {
  const qaList = document.getElementById("qa-list");
  if (!qaList) return;
  qaList.innerHTML = "";
  if (!answerList.length) {
    qaList.innerHTML = "<p class='muted'>No answers generated.</p>";
    return;
  }
  const table = document.createElement("table");
  table.style.width = "100%";
  table.style.borderCollapse = "collapse";
  table.innerHTML = `
    <thead>
      <tr>
        <th style="text-align: left; padding: 8px;">Question</th>
        <th style="text-align: left; padding: 8px;">Answer</th>
      </tr>
    </thead>
    <tbody>
      ${answerList.map(entry => `
        <tr>
          <td style="padding: 8px; vertical-align: top;">${entry.question}</td>
          <td style="padding: 8px; vertical-align: top;">${entry.answer}</td>
        </tr>
      `).join('')}
    </tbody>
  `;
  qaList.appendChild(table);
}

function openPaperModal({ id, url, name, abstract = "" }) {
  document.getElementById("paperModalTitle").textContent = name || "Paper";
  document.getElementById("paperAbstract").textContent = abstract || "No abstract provided.";
  const absUrl = /^https?:\/\//i.test(url) ? url : `${window.location.origin}${url}`;
  const viewerUrl = `${STATIC_BASE}ligninapp/pdfjs/web/viewer.html?file=${encodeURIComponent(absUrl)}#zoom=page-width`;
  const viewer = document.getElementById("paperViewer");
  viewer.src = viewerUrl;
  let input = document.getElementById("paperModalPaperId");
  if (!input) {
    input = document.createElement("input");
    input.type = "hidden";
    input.id = "paperModalPaperId";
    document.getElementById("paperModal").appendChild(input);
  }
  input.value = id || "";
  document.getElementById("paperModal").style.display = "block";
  // 1) Retrieve the highlights for this row
  async function fetchEntryHighlights(reviewId, entryId) {
    const res = await fetch(`/review/${encodeURIComponent(reviewId)}/entries/${encodeURIComponent(entryId)}/highlights/`, {
      method: "GET",
      headers: { "X-CSRFToken": csrftoken },
    });
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`HTTP ${res.status}: ${txt}`);
    }
    return await res.json();
  }

  // 2) Inject (wait until PDF.js is ready)
  async function injectHighlightsIntoPdfViewer(iframe, highlightsByColumn) {
    // 0) Wait for PDF.js to be ready
    const app = await new Promise((resolve, reject) => {
      const win = iframe.contentWindow;
      let tries = 0;
      const t = setInterval(() => {
        tries++;
        try {
          if (win && win.PDFViewerApplication && win.PDFViewerApplication.pdfViewer) {
            clearInterval(t);
            resolve(win.PDFViewerApplication);
            return;
          }
        } catch (e) {}
        if (tries > 200) { clearInterval(t); reject(new Error("PDF.js not ready")); }
      }, 50);
    });
    const viewer = app.pdfViewer;
  
    // 1) Wait for document/pages to be ready (ensure total pages & views are available)
    await new Promise((resolve) => {
      if (viewer._pages && viewer._pages.length) resolve();
      else app.eventBus.on("pagesinit", resolve);
    });
    const totalPages = viewer._pages?.length || app.pdfDocument?.numPages || 0;
    console.log("[HL] totalPages =", totalPages);
  
    // 2) Now perform "grouping + page index validation"
    const grouped = {}; // pageIndex(0-based) -> rect[]
    Object.entries(highlightsByColumn || {}).forEach(([col, arr]) => {
      (arr || []).forEach(it => {
        if (!it || !Array.isArray(it.rect)) return;
        let p = Number(it.page);
        if (!Number.isFinite(p)) return;
  
        // Both 0-based and 1-based page indexes are supported, judged based on totalPages
        let pageIndex;
        if (p >= 1 && p <= totalPages) pageIndex = p - 1;          // 1-based
        else if (p >= 0 && p < totalPages) pageIndex = p;          // 0-based
        else {
          console.warn("[HL] page out of range:", p, "total:", totalPages);
          return;
        }
        (grouped[pageIndex] ||= []).push(it.rect.slice(0, 4));
      });
    });
  
    const pagesWithHL = Object.keys(grouped).map(n => +n);
    if (!pagesWithHL.length) {
      console.log("[HL] no highlights to draw");
      return;
    }
    console.log("[HL] pages to draw:", pagesWithHL, "counts:", pagesWithHL.map(i => grouped[i].length));
  
    // 3) Draw rectangles (and redraw on pagerendered/textlayerrendered/scalechanging)
    function drawForPage(pageIndex) {
      const pv = viewer.getPageView(pageIndex);
      if (!pv || !pv.div) return;
      const list = grouped[pageIndex];
      if (!list || !list.length) return;
  
      pv.div.querySelectorAll(".lignin-highlight").forEach(n => n.remove());
      const host = pv.div.querySelector(".textLayer") || pv.div;
      if (getComputedStyle(host).position === "static") host.style.position = "relative";
  
      list.forEach(rect => {
        let r = rect;
        if ((r[2] - r[0]) < 2 && (r[3] - r[1]) < 2) r = [r[0], r[1], r[0] + 6, r[1] + 12];
  
        const vr = pv.viewport.convertToViewportRectangle(r);
        const x = Math.min(vr[0], vr[2]);
        const y = Math.min(vr[1], vr[3]);
        const w = Math.abs(vr[0] - vr[2]);
        const h = Math.abs(vr[1] - vr[3]);
  
        const el = document.createElement("div");
        el.className = "lignin-highlight";
        el.style.cssText = `position:absolute;left:${x}px;top:${y}px;width:${w}px;height:${h}px;pointer-events:none;background:rgba(255,230,0,.35);border:1px solid rgba(180,160,0,.7);border-radius:2px;z-index:7`;
        host.appendChild(el);
      });
  
      console.log(`[HL] drawn page ${pageIndex + 1} (${list.length} rects)`);
    }
  
    // First draw highlights on pages that have already rendered
    for (const i of pagesWithHL) {
      const pv = viewer.getPageView(i);
      if (pv && pv.renderingState === 3 /* FINISHED */) drawForPage(i);
    }
  
    // For subsequently rendered pages
    app.eventBus.on("pagerendered", e => {
      const i = (e?.pageNumber ?? 1) - 1;
      if (grouped[i]) {
        const doDraw = () => drawForPage(i);
        app.eventBus.on("textlayerrendered", ev => { if ((ev?.pageNumber ?? 1) - 1 === i) doDraw(); });
        setTimeout(doDraw, 100);
      }
    });
  
    // Redraw on zoom/rotation changes
    app.eventBus.on("scalechanging", () => pagesWithHL.forEach(drawForPage));
    app.eventBus.on("rotationchanging", () => pagesWithHL.forEach(drawForPage));
  }
  
  

  // === Place at the end of openPaperModal: fetch and inject after iframe onload ===
  const once = (node, type) =>
    new Promise(resolve => node.addEventListener(type, function h(e){ node.removeEventListener(type, h); resolve(e); }));

  (async () => {
    try {
      await new Promise((resolve) => {
        const d = viewer.contentDocument;
        if (d && d.readyState === "complete") {
          resolve();
        } else {
          const done = () => resolve();
          viewer.addEventListener("load", done, { once: true });
          setTimeout(resolve, 1500);
        }
      });

      const payload = await fetchEntryHighlights(questionID, id);
      if (!payload.ok) throw new Error(payload.error || "highlight fetch failed");

      console.log("[HL] will fetch & inject for entry", id);
      await injectHighlightsIntoPdfViewer(viewer, payload.by_column || {});
    } catch (err) {
      console.warn("[highlight] skip:", err);
    }
  })();

}

function closePaperModal() {
  const modal = document.getElementById("paperModal");
  const viewer = document.getElementById("paperViewer");
  viewer.src = "about:blank";
  modal.style.display = "none";
}

function openNestedModal() {
  document.getElementById("nested-edit-modal").style.display = "block";
}

function closeNestedModal() {
  document.getElementById("nested-edit-modal").style.display = "none";
}

function addQuestionInput() {
  const container = document.getElementById("questions-container");
  const div = document.createElement("div");
  div.innerHTML = `<input type="text" placeholder="Enter question" class="question-input">
                   <button onclick="this.parentElement.remove()">Remove</button>`;
  container.appendChild(div);
}

let qaRendered = false;

function confirmQuestions() {
  const inputs = document.querySelectorAll('.question-input');
  const questions = Array.from(inputs).map(i => i.value.trim()).filter(Boolean);
  const container = document.getElementById("questions-container");

  if (questions.length === 0) {
    container.innerHTML = `<p style="color: red;">Please add at least one question.</p>`;
    return;
  }

  // Render inside modal
  container.innerHTML = "";
  const qaTable = document.createElement('div');
  qaTable.style.border = '1px solid #ccc';
  qaTable.style.borderRadius = '6px';
  qaTable.style.padding = '10px';
  qaTable.style.marginTop = '20px';

  questions.forEach((q, idx) => {
    const qaRow = document.createElement('div');
    qaRow.style.marginBottom = '10px';
    qaRow.innerHTML = `<strong>Q${idx + 1}:</strong> ${q}<br><strong>A:</strong> [Answer will go here]`;
    qaTable.appendChild(qaRow);
  });

  container.appendChild(qaTable);

  const qaList = document.getElementById("qa-list");
if (qaList) {
  qaList.innerHTML = "";

  const table = document.createElement("table");
  table.style.width = "100%";
  table.style.borderCollapse = "collapse";
  table.innerHTML = `
    <thead>
      <tr>
        <th style="text-align: left; padding: 8px;">Question</th>
        <th style="text-align: left; padding: 8px;">Answer</th>
      </tr>
    </thead>
    <tbody>
      ${questions.map((q, idx) => `
        <tr>
          <td style="padding: 8px;">Q${idx + 1}: ${q}</td>
          <td style="padding: 8px;">[Answer will go here]</td>
        </tr>
      `).join("")}
    </tbody>
  `;
  qaList.appendChild(table);
}
}

// Delegate click event for dynamically inserted #edit-btn
document.addEventListener("click", function (e) {
  if (e.target && e.target.id === "edit-btn") {
    openNestedModal();
  }
});

// Open/close the upload modal (if corresponding button exists on the page)
function toggleUploadModal(show) {
  const modal = document.getElementById("uploadModal");
  if (!modal) return;
  modal.style.display = show ? "block" : "none";
}

// Bind upload form for AJAX submission: automatically refresh EAV table upon success
function bindUploadFormAjax() {
  const uploadForm = document.querySelector('#uploadModal form');
  if (!uploadForm) return;

  uploadForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    const action = uploadForm.getAttribute('action') || uploadForm.action;
    const formData = new FormData(uploadForm);

    try {
      const res = await fetch(action, {
        method: "POST",
        headers: { "X-CSRFToken": csrftoken },
        body: formData
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Upload failed: HTTP ${res.status}: ${text}`);
      }

      // On success: close modal, clear file input, and refresh table
      toggleUploadModal(false);
      const fileInput = uploadForm.querySelector('input[type="file"]');
      if (fileInput) fileInput.value = "";
      reloadPapers();

      console.log("[upload] success");
    } catch (err) {
      console.error(err);
      alert("Upload failed: " + err.message);
    }
  });
}

// Display answers. Input: llmText = data.llm_text, table = your Tabulator instance
function applyLlmTextToTabulator(llmText, table, isEdited){
  if (!Array.isArray(llmText)) return;

  const FILE_COL_TITLE = "File name"; // If  column title differs, change it here


  const titleToField = new Map();
  table.getColumns().forEach(col => {
    const def = col.getDefinition();
    if (def && def.title) {
      titleToField.set(def.title, def.field || def.title);
    }
  });


  const fileField = titleToField.get(FILE_COL_TITLE) || FILE_COL_TITLE;


  const rowByFilename = new Map();
  table.getRows().forEach(row => {
    const d = row.getData();
    const fname = (d[fileField] || "").toString().trim(); // Use the field value!
    if (fname) rowByFilename.set(fname, row);
  });


  const filenameFromUrl = (url) => {
    if (!url) return null;
    try { return url.split("/").pop(); } catch { return null; }
  };

  llmText.forEach(item => {
    const fname = filenameFromUrl(item.url);
    if (!fname) return;

    const row = rowByFilename.get(fname);
    if (!row) {
      console.warn("No row matched file:", fname);
      return;
    }

    const q2ans = item.answers_by_question || {};
    const patch = {};
    const entryId = row.getData().entry_id; // NEW

    Object.entries(q2ans).forEach(([questionTitle, answer]) => {
      const field = titleToField.get(questionTitle) || questionTitle;
      if (answer !== undefined && answer !== null) {
        // NEW: if edited=true, skip
        if (typeof isEdited === "function" && isEdited(entryId, field)) return;
        patch[field] = (answer === "N/A") ? "" : answer;
      }
    });

    if (Object.keys(patch).length) {
      row.update(patch);
    }
  });
}

window.applyLlmTextToTabulator ||= applyLlmTextToTabulator;


// ========== Initial rendering after document is fully loaded ==========
$(document).ready(() => {
  reloadPapers();
  bindUploadFormAjax();   // Refresh after successful upload
});
