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


function reloadPapers(callback) {
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

    const dynamicCols = meta
      // CHANGE: Destructure 'description' from the meta object as well
      ? meta.map(({ id, name, description }) => {
          const titleText = (name === "file_name") ? "File name" : name;

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
              openPaperModal({ id: rowData.entry_id, url: `/media/uploaded_papers/${encodeURIComponent(fileName)}`, name: fileName });
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

          // Otherwise, follow the original logic (with a delete button AND now an Edit button)
          return {
            title: titleText,
            field: name,
            editor: "textarea", 
            editorParams: {
                verticalNavigation: "editor", 
                shiftEnterSubmit: true,       
            },

            // Render a title and a small button in the column header
            titleFormatter: function (column, formatterParams, onRendered) {
              // ... existing protection check ...
              if (name === "file_name" || titleText === "File name") {
                 /* ... existing simple span return ... */
                 const span = document.createElement("span");
                 span.textContent = titleText;
                 span.style.fontWeight = "bold";
                 return span;
              }

              // Get the header cell element
              const headerEl = column && typeof column.getElement === "function"
                ? column.getElement()
                : null;
              
              if (headerEl) {
                  // Ensure relative positioning for the absolute delete button
                  if (getComputedStyle(headerEl).position === "static") {
                    headerEl.style.position = "relative";
                  }
                  // Adjust padding to prevent text from hitting the delete button
                  headerEl.style.paddingRight = "24px"; 
              }

              // --- START MODIFICATION: Layout for Edit Button + Text ---
              
              // 1. Create the main flex container
              const container = document.createElement("div");
              container.className = "custom-header-container"; // Use the class we defined in HTML

              // 2. Create the "Edit" button
              const editBtn = document.createElement("button");
              editBtn.textContent = "Edit";
              editBtn.className = "header-edit-btn"; // Use CSS class
              editBtn.title = "Edit column name/description";
              
              // Prevent click propagation (so it doesn't trigger Tabulator sorting immediately)
              editBtn.addEventListener("click", (e) => {
                  e.stopPropagation();
                  e.preventDefault();
                  // Call the global function defined in question.html
                  if (typeof window.openEditColumnModal === "function") {
                      // Pass the current description (ensure backend sends it in 'meta')
                      window.openEditColumnModal(id, name, description || "");
                  } else {
                      alert("Edit function not loaded.");
                  }
              });

              container.appendChild(editBtn);

              // 3. Create the text span
              const span = document.createElement("span");
              span.textContent = titleText;
              span.style.fontWeight = "bold";
              container.appendChild(span);

              // --- END MODIFICATION ---

              // ... existing Delete Button Logic ...
              const btn = document.createElement("button");
              btn.textContent = "✕";
              btn.title = "Remove this column from this review";
              btn.className = "column-remove-button"; 

              // Style: float above text, pinned to right side of header cell
              Object.assign(btn.style, {
                position: "absolute",
                top: "4px",        // Adjusted top position
                right: "4px",
                // ... other existing styles ...
                padding: "0 6px",
                lineHeight: "16px",
                color: "#b00",
                background: "#f7f7f7",
                border: "1px solid #ccc",
                borderRadius: "4px",
                cursor: "pointer",
                zIndex: "2",
              });

              btn.addEventListener("click", async (ev) => {
                  /* ... existing delete logic ... */
                  ev.preventDefault();
                  ev.stopPropagation();
                  if (!confirm(`Remove column "${name}" from this review?`)) return;
                  // ... fetch call ...
                  // (Keep existing fetch logic)
                  try {
                    const res = await fetch(
                      `/review/${encodeURIComponent(questionID)}/columns/${encodeURIComponent(id)}/remove/`,
                      { method: "POST", headers: { "X-CSRFToken": csrftoken } }
                    );
                    // ... handle response ...
                    if(res.ok) reloadPapers(); // etc
                  } catch(e) { console.error(e); }
              });

              // Attach the delete button (Keep existing logic)
              if (headerEl) {
                const existing = headerEl.querySelector(".column-remove-button");
                if (existing) existing.remove();
                headerEl.appendChild(btn);
              } else {
                // Fallback
                container.appendChild(btn); 
              }

              return container;
            },
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
      movableColumns: true,

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
            //lock_after_save: true
          }),
        });
    
        if (!res.ok) {

          reverting = true;
          cell.restoreOldValue();
          reverting = false;
    
          const text = await res.text();
          throw new Error(`HTTP ${res.status}: ${text}`);
        }
 

      } catch (err) {
        console.error("[save cell] failed:", err);
        alert("save failed" + err.message);
      }
    });

    if (typeof callback === "function") {
      console.log("Table reloaded, triggering callback...");
      // 稍微延迟 100ms 确保 DOM 渲染完毕，避免 generateAnswers 取不到元素
      setTimeout(callback, 100);
    }
    
  }, 'json');
}



function openPaperModal({ id, url, name, abstract = "" }) {
  document.getElementById("paperModalTitle").textContent = name || "Paper";
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
  // === Left pane: reset QA area and show loading ===
  const qaContainer = document.getElementById("paperModalQa");
  if (qaContainer) {
    // Clear any previous content
    qaContainer.innerHTML = "";

    // Show a lightweight loading placeholder
    const loadingBlock = document.createElement("div");
    loadingBlock.className = "qa-block";
    const p = document.createElement("p");
    p.className = "qa-empty-text";
    p.textContent = "Loading...";
    loadingBlock.appendChild(p);
    qaContainer.appendChild(loadingBlock);
  }

  // Column -> highlight list index for this entry (built from /highlights/ payload)
  let columnHighlightIndex = {};

  function getColumnHighlightList(colKey) {
    if (!colKey) return [];
    const idx = columnHighlightIndex || {};
    const list = idx[colKey];
    return Array.isArray(list) ? list : [];
  }

  function syncQaButtonsWithHighlights() {
    if (!qaContainer) return;
    const buttons = qaContainer.querySelectorAll(".qa-show-source[data-col-key]");
    buttons.forEach(btn => {
      const key = btn.getAttribute("data-col-key") || "";
      const hasHighlight = getColumnHighlightList(key).length > 0;
      btn.disabled = !hasHighlight;
      btn.title = hasHighlight
        ? "Show source text in PDF"
        : "No source text available for this column.";
    });
  }

  function jumpToHighlight(colKey) {
    const iframe = document.getElementById("paperViewer");
    if (!iframe || !iframe.contentWindow) {
      console.warn("[QA] jumpToHighlight: iframe not ready");
      return;
    }
    const win = iframe.contentWindow;
    const app = win.PDFViewerApplication;
    if (!app || !app.pdfViewer) {
      console.warn("[QA] jumpToHighlight: PDF.js application not ready");
      return;
    }
    const viewer = app.pdfViewer;

    const list = getColumnHighlightList(colKey);
    if (!list.length) {
      console.warn("[QA] jumpToHighlight: no highlight for column", colKey);
      return;
    }

    const totalPages = viewer._pages?.length || app.pdfDocument?.numPages || 0;
    let target = null;
    for (const item of list) {
      if (!item || !Array.isArray(item.rect) || item.rect.length < 4) continue;
      let p = Number(item.page);
      if (!Number.isFinite(p)) continue;
      let pageIndex;
      if (p >= 1 && p <= totalPages) pageIndex = p - 1;          // 1-based
      else if (p >= 0 && p < totalPages) pageIndex = p;          // 0-based
      else continue;
      target = { pageIndex, rect: item.rect.slice(0, 4) };
      break;
    }
    if (!target) {
      console.warn("[QA] jumpToHighlight: could not resolve page for column", colKey);
      return;
    }

    const pv = viewer.getPageView(target.pageIndex);
    if (!pv || !pv.div) {
      if (app.pdfLinkService && typeof app.pdfLinkService.goToPage === "function") {
        app.pdfLinkService.goToPage(target.pageIndex + 1);
      }
      return;
    }

    const viewport = pv.viewport;
    const vr = viewport.convertToViewportRectangle(target.rect);
    const x = Math.min(vr[0], vr[2]);
    const y = Math.min(vr[1], vr[3]);

    const host = pv.div.querySelector(".textLayer") || pv.div;
    const doc = host.ownerDocument;
    const view = doc.defaultView || win;

    if (view.getComputedStyle(host).position === "static") {
      host.style.position = "relative";
    }

    let anchor = host.querySelector(".qa-jump-anchor");
    if (!anchor) {
      anchor = doc.createElement("div");
      anchor.className = "qa-jump-anchor";
      anchor.style.cssText = "position:absolute;width:1px;height:1px;pointer-events:none;opacity:0;z-index:8";
      host.appendChild(anchor);
    }

    anchor.style.left = `${x}px`;
    anchor.style.top  = `${y}px`;

    anchor.scrollIntoView({ block: "center", behavior: "smooth" });
  }
  
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
  
  
  // === QA API helpers (left pane) ===
  async function fetchEntryQa(reviewId, entryId) {
    // Fetch QA data for this entry
    const res = await fetch(
      `/review/${encodeURIComponent(reviewId)}/entries/${encodeURIComponent(entryId)}/qa/`,
      {
        method: "GET",
        headers: { "X-CSRFToken": csrftoken },
      }
    );

    if (!res.ok) {
      // Try to read text for more context, but don't fail if that throws
      let msg = `HTTP ${res.status}`;
      try {
        const txt = await res.text();
        if (txt) msg = `${msg}: ${txt}`;
      } catch (e) {}
      throw new Error(msg);
    }

    return await res.json();
  }

  function renderQa(container, payload) {
    if (!container) return;

    // Clear the loading placeholder
    container.innerHTML = "";

    // Handle error-ish payloads
    if (!payload || payload.ok === false) {
      const msg =
        (payload && payload.error) ? String(payload.error) : "Unknown error";

      const errDiv = document.createElement("div");
      errDiv.className = "qa-error";
      errDiv.textContent = `Failed to load QA data: ${msg}`;
      container.appendChild(errDiv);
      return;
    }

    const items = Array.isArray(payload.data) ? payload.data : [];

    if (!items.length) {
      const block = document.createElement("div");
      block.className = "qa-block";

      const p = document.createElement("p");
      p.className = "qa-empty-text";
      p.textContent = "No QA data for this entry.";
      block.appendChild(p);

      container.appendChild(block);
      return;
    }

    // Render each QA row
    items.forEach(item => {
      const block = document.createElement("div");
      block.className = "qa-block";

      // Title: column.name
      const titleEl = document.createElement("h3");
      titleEl.className = "qa-title";
      titleEl.textContent = item.name || "(Untitled)";
      block.appendChild(titleEl);

      // Optional description
      if (item.description) {
        const descEl = document.createElement("p");
        descEl.className = "qa-description";
        descEl.textContent = item.description;
        block.appendChild(descEl);
      }

      // "Show source text" button (jump to highlight in PDF viewer)
      const sourceBtn = document.createElement("button");
      sourceBtn.type = "button";
      sourceBtn.className = "qa-show-source";
      const colKey = item.name || "";
      sourceBtn.setAttribute("data-col-key", colKey);
      sourceBtn.textContent = "Show source text";

      const hasHighlight = getColumnHighlightList(colKey).length > 0;
      sourceBtn.disabled = !hasHighlight;
      sourceBtn.title = hasHighlight
        ? "Show source text in PDF"
        : "No source text available for this column.";

      sourceBtn.addEventListener("click", () => {
        if (sourceBtn.disabled) return;
        jumpToHighlight(colKey);
      });

      block.appendChild(sourceBtn);

      // Answer text (or placeholder)
      const answerEl = document.createElement("p");
      if (item.value) {
        answerEl.className = "qa-answer";
        answerEl.textContent = item.value;
      } else {
        answerEl.className = "qa-empty-text";
        answerEl.textContent = "No answer.";
      }
      block.appendChild(answerEl);

      container.appendChild(block);
    });

    // In case highlights arrived before QA, ensure buttons reflect latest state
    syncQaButtonsWithHighlights();
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
      if (!payload || payload.ok === false) {
        const msg = (payload && payload.error) ? payload.error : "highlight fetch failed";
        throw new Error(msg);
      }

      const byColumn = payload.by_column || {};
      columnHighlightIndex = {};
      Object.entries(byColumn).forEach(([col, list]) => {
        if (!col) return;
        const arr = Array.isArray(list) ? list : [];
        const normalized = arr.filter(it =>
          it &&
          Array.isArray(it.rect) &&
          it.rect.length >= 4 &&
          Number.isFinite(Number(it.page))
        );
        if (normalized.length) {
          columnHighlightIndex[col] = normalized;
        }
      });
      viewer.__columnHighlightIndex = columnHighlightIndex;

      console.log("[HL] will fetch & inject for entry", id, "columns:", Object.keys(columnHighlightIndex));
      await injectHighlightsIntoPdfViewer(viewer, columnHighlightIndex);

      // After highlights are ready, sync QA buttons (if they are already rendered)
      syncQaButtonsWithHighlights();


    } catch (err) {
      console.warn("[highlight] skip:", err);
    }
  })();
  // === Kick off QA loading for the left pane ===
  if (qaContainer) {
    (async () => {
      try {
        if (!questionID || !id) {
          // Missing identifiers – show a friendly message instead of failing silently
          renderQa(qaContainer, {
            ok: false,
            error: "Missing review or entry id.",
          });
          return;
        }

        const payload = await fetchEntryQa(questionID, id);
        renderQa(qaContainer, payload);
      } catch (err) {
        console.error("[QA] failed:", err);
        renderQa(qaContainer, { ok: false, error: err.message || String(err) });
      }
    })();
  }
}

function closePaperModal() {
  const modal = document.getElementById("paperModal");
  const viewer = document.getElementById("paperViewer");
  viewer.src = "about:blank";
  modal.style.display = "none";
}

//let qaRendered = false;

// Open/close the upload modal (if corresponding button exists on the page)
function toggleUploadModal(show) {
  const modal = document.getElementById("uploadModal");
  if (!modal) return;
  modal.style.display = show ? "block" : "none";
}

// Bind upload form for AJAX submission: automatically refresh EAV table upon success
/* --- main.js --- */

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

      // On success: close modal, clear file input
      toggleUploadModal(false);
      const fileInput = uploadForm.querySelector('input[type="file"]');
      if (fileInput) fileInput.value = "";
      
      console.log("[upload] success, reloading papers and generating answers...");

      // === 【修改】传入 generateAnswers 作为回调 ===
      // 注意：generateAnswers 是全局函数 (window.generateAnswers)
      reloadPapers(() => {
          if (typeof generateAnswers === "function") {
              generateAnswers();
          }
      });

    } catch (err) {
      console.error(err);
      alert("Upload failed: " + err.message);
    }
  });
}

// Display answers. Input: llmText = data.llm_text, table = your Tabulator instance
function applyLlmTextToTabulator(llmText, table, isEdited) {
  if (!Array.isArray(llmText)) return;

  // FIX: Capture the scroll position ONCE before any updates occur.
  // This prevents the "dirty read" issue where later rows read a scroll position 
  // that has already been shifted by previous row updates.
  const holder = table.element.querySelector(".tabulator-tableholder");
  const globalSavedScrollTop = holder ? holder.scrollTop : 0;

  // Map column titles to their internal field names
  const FILE_COL_TITLE = "File name";
  const titleToField = new Map();
  table.getColumns().forEach(col => {
    const def = col.getDefinition();
    if (def && def.title) {
      titleToField.set(def.title, def.field || def.title);
    }
  });

  const fileField = titleToField.get(FILE_COL_TITLE) || FILE_COL_TITLE;

  // Pre-calculate a map of Filename -> Row Component for faster lookups
  const rowByFilename = new Map();
  table.getRows().forEach(row => {
    const d = row.getData();
    // Ensure we handle potential null/undefined values safely
    const fname = (d[fileField] || "").toString().trim();
    if (fname) rowByFilename.set(fname, row);
  });

  // Helper to extract filename from a full URL
  const filenameFromUrl = (url) => {
    if (!url) return null;
    try {
      return url.split("/").pop();
    } catch {
      return null;
    }
  };

  // Iterate through the LLM results and apply updates
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

    // Map the incoming answers to the correct Tabulator fields
    Object.entries(q2ans).forEach(([questionTitle, answer]) => {
      const field = titleToField.get(questionTitle) || questionTitle;
      if (answer !== undefined && answer !== null) {
        patch[field] = (answer === "N/A") ? "" : answer;
      }
    });

    // Apply the update if there is data
    if (Object.keys(patch).length) {
      // Note: We do NOT capture scrollTop here anymore.
      
      row.update(patch).then(() => {
        // FIX: Restore the scroll position to the 'globalSavedScrollTop' captured 
        // at the very beginning of the function.
        if (holder) {
          // Only force the scroll adjustment if the position has actually drifted
          if (Math.abs(holder.scrollTop - globalSavedScrollTop) > 0) {
            holder.scrollTop = globalSavedScrollTop;
          }
        }
      });
    }
  });
}


window.applyLlmTextToTabulator ||= applyLlmTextToTabulator;


// ========== Initial rendering after document is fully loaded ==========
$(document).ready(() => {
  reloadPapers();
  bindUploadFormAjax();   // Refresh after successful upload
});
