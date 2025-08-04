// === globals / setup ===
const csrftoken = Cookies.get('csrftoken');
window.__editMode = false;   // edit mode off by default
let table;                   // Tabulator instance

const findResults = $("#find-results");
const paperTable = $("#paper-table");
const snowballResults = $("#snowball-results");

// --- helpers ---
function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, c => (
    { "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]
  ));
}

// === layout controls ===
function toggleFullWidth() {
  $("#paper-table-container").toggleClass("fullwidth");
}

// === add / reject from search & snowball ===
function addPaper() {
  let paperId = $(this).attr("data-lignin-paperId");
  const thisButton = this;
  $.ajax({
    url: '/question/' + questionID + '/papers/add/' + paperId + '/',
    headers: { 'X-CSRFToken': csrftoken },
    type: 'PUT',
    success: function() {
      reloadPapers();
      $(thisButton).closest('tr').remove();
    }
  });
}

function rejectPaper() {
  let paperId = $(this).attr("data-lignin-paperId");
  const thisButton = this;
  $.ajax({
    url: '/question/' + questionID + '/papers/reject/' + paperId + '/',
    headers: { 'X-CSRFToken': csrftoken },
    type: 'PUT',
    success: function() {
      $(thisButton).closest('tr').remove();
    }
  });
}

// === helpers used by search/snowball ===
function stringOrFALN(keyname, entry) {
  if (keyname === "authors") {
    return entry["authors"].map(x => x.name).join(", ");
  } else {
    return entry[keyname];
  }
}
function arrayToTable(array, additional, drop, columnIDs) {
  const dataKeys = Object.keys(array.reduce(function(acc, curr) {
    Object.keys(curr).forEach(x => acc[x] = true); return acc;
  }, {})).filter(item => !drop.includes(item));
  const additionalKeys = Array.from(Object.keys(additional));
  const table = $("<table>");
  table.append($("<tr>").append(
    dataKeys.concat(additionalKeys).map(keyname => $("<th>").text(keyname))
  ));
  table.append(array.map(entry => $("<tr>")
    .attr("data-lignin-paperId", entry["ssPaperID"] || entry["paperId"])
    .append(
      dataKeys.map(keyname => $("<td>")
        .text(stringOrFALN(keyname, entry))
        .attr("data-lignin-columnId", columnIDs[keyname]))
      .concat(additionalKeys.map(keyname => additional[keyname](entry)))
    )
  ));
  return table;
}
function titleAndLink(entry) {
  return $("<td>").append($("<a>").text(entry["title"]).attr("href", entry["url"]).attr("target", "_blank"));
}

// === legacy replace file modal (kept for now) ===
function triggerReplace(paperId) {
  const modal = document.getElementById("replaceModal");
  modal.style.display = "block";
  document.getElementById("replacePaperId").value = paperId;
}
function closeReplaceModal() {
  document.getElementById("replaceModal").style.display = "none";
}

// === new paper viewer + replace modal ===
function openPaperModal({ id, url, name }) {
    // Title
    document.getElementById("paperModalTitle").textContent = name || "Paper";
  
    // Make sure the file URL is absolute
    const absUrl = /^https?:\/\//i.test(url) ? url : `${window.location.origin}${url}`;
  
    // Point to the viewer we copied into ligninapp/static/ligninapp/pdfjs/...
    const viewerUrl = `${STATIC_BASE}ligninapp/pdfjs/web/viewer.html?file=${encodeURIComponent(absUrl)}#zoom=page-width`;
  
    const viewer = document.getElementById("paperViewer");
    viewer.src = viewerUrl;
  
    document.getElementById("paperModalPaperId").value = id || "";
    document.getElementById("paperModal").style.display = "block";
  }
  
  
function closePaperModal() {
  const modal = document.getElementById("paperModal");
  const viewer = document.getElementById("paperViewer");
  viewer.src = "about:blank";
  modal.style.display = "none";
}

// === click-pencil helper: turn on Edit mode and edit this cell ===
function enterEditModeAndEdit(cell) {
  if (!window.__editMode) {
    window.__editMode = true;
    document.body.classList.toggle("edit-mode", true);
    updateEditButtonUI();
    applyEditMode();
  }
  cell.edit(true);
}

// === formatter that renders value + pencil button ===
function editableCellFormatter(cell) {
  const wrap = document.createElement("div");
  wrap.className = "cell-edit-wrap";

  const span = document.createElement("span");
  const v = cell.getValue();
  span.className = "cell-text";
  span.textContent = (v === null || v === undefined) ? "" : String(v);

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "cell-edit-handle";
  btn.title = "Edit";
  btn.textContent = "✏️";
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    enterEditModeAndEdit(cell);
  });

  wrap.appendChild(span);
  wrap.appendChild(btn);
  return wrap;
}

// === table loader ===
function reloadPapers() {
  $.get('/question/' + questionID + '/papers/', {}, function(data) {
    if (table && typeof table.destroy === "function") {
      try { table.destroy(); } catch (e) {}
      $("#paper-table").empty();
    }

    table = new Tabulator("#paper-table", {
      maxHeight: "80vh",
      height: "80vh",
      data: data.data,
      layout: "fitData",
      renderHorizontal: "virtual",
      editTriggerEvent: "dblclick",
      persistence: { columns: ["width"] },
      columns: [
        { title: "Title",  field: "title",  editor: false, formatter: editableCellFormatter },
        { title: "Author", field: "author", editor: false, formatter: editableCellFormatter },
        { title: "Year",   field: "year",   editor: false, editorParams:{ min:1800, max:2100, step:1 }, formatter: editableCellFormatter },
        { title: "Notes",  field: "notes",  editor: false, formatter: editableCellFormatter },
        {
          title: "Paper(s)",
          field: "url",
          formatter: function(cell) {
            const d = cell.getRow().getData();
            const url = cell.getValue();
            const name =
              d.paper_title || d.file_name || d.filename || d.original_filename ||
              (function(u){
                if (!u) return "";
                try { return decodeURIComponent(u.split("/").pop().split("?")[0]); }
                catch { return u; }
              })(url);

            const paperId = d.id.replace("upload-", "");
            return `<a href="#" class="paper-link"
                      data-id="${paperId}"
                      data-url="${url}"
                      data-name="${escapeHtml(name)}">${escapeHtml(name || "—")}</a>`;
          },
          widthGrow: 2,
          hozAlign: "left",
        },
        {
          title: "Delete",
          formatter: "buttonCross",
          width: 100,
          align: "center",
          cellClick: function(e, cell) {
            const paperId = cell.getRow().getData().id.replace("upload-", "");
            fetch(`/papers/delete/${paperId}/`, {
              method: "DELETE",
              headers: { "X-CSRFToken": csrftoken },
            })
            .then(res => res.json())
            .then(data => {
              if (data.success) cell.getRow().delete();
              else alert("Delete failed: " + data.error);
            });
          }
        }
      ]
    });

    // Block editing unless in Edit mode
    table.on("cellEditing", function(){
      if (!window.__editMode) return false;
    });

    // Persist edits only while in Edit mode
    table.on("cellEdited", function(cell) {
      if (!window.__editMode) return;

      const rowData = cell.getRow().getData();
      const paperId = rowData.id.replace("upload-", "");

      fetch(`/papers/update/${paperId}/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrftoken,
        },
        body: JSON.stringify({
          title: rowData.title,
          author: rowData.author,
          year: rowData.year,
          notes: rowData.notes,
        }),
      })
      .then(res => res.json())
      .then(data => { if (!data.success) alert("Update failed: " + data.error); });
    });

    applyEditMode();
  }, 'json');
}

// === toggle editors on/off at the column level ===
function applyEditMode() {
  if (!table) return;
  if (window.__editMode) {
    table.updateColumnDefinition("title",  { editor: "input" });
    table.updateColumnDefinition("author", { editor: "input" });
    table.updateColumnDefinition("year",   { editor: "number", editorParams: { min: 1800, max: 2100, step: 1 } });
    table.updateColumnDefinition("notes",  { editor: "textarea" });
  } else {
    table.updateColumnDefinition("title",  { editor: false });
    table.updateColumnDefinition("author", { editor: false });
    table.updateColumnDefinition("year",   { editor: false });
    table.updateColumnDefinition("notes",  { editor: false });
  }
  table.redraw(true);
}

// === edit button UI ===
function updateEditButtonUI() {
  const btn = document.getElementById("toggle-edit");
  if (!btn) return;
  btn.textContent = window.__editMode ? "Done Editing" : "Edit";
  btn.classList.toggle("btn-success", window.__editMode);
  btn.classList.toggle("btn-outline-warning", !window.__editMode);
}

// === single DOMContentLoaded block ===
document.addEventListener("DOMContentLoaded", () => {
  // Legacy replace modal submit (kept for now)
  const replaceForm = document.getElementById("replaceForm");
  if (replaceForm) {
    replaceForm.addEventListener("submit", function(e) {
      e.preventDefault();

      const paperId = document.getElementById("replacePaperId").value;
      const fileInput = document.getElementById("newFile");
      const formData = new FormData();
      formData.append("file", fileInput.files[0]);

      fetch(`/papers/replace/${paperId}/`, {
        method: "POST",
        headers: { "X-CSRFToken": csrftoken },
        body: formData
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          alert("File replaced successfully!");
          closeReplaceModal();
          reloadPapers();
        } else {
          alert("Replace failed: " + data.error);
        }
      });
    });
  }

  // New paper viewer modal: delegated click from table
  const tableEl = document.getElementById("paper-table");
  if (tableEl) {
    tableEl.addEventListener("click", (e) => {
      const a = e.target.closest("a.paper-link");
      if (!a) return;
      e.preventDefault();
      openPaperModal({
        id: a.dataset.id,
        url: a.dataset.url,
        name: a.dataset.name,
      });
    });
  }

  // Paper viewer modal: replace submit
  const paperReplaceForm = document.getElementById("paperReplaceForm");
  if (paperReplaceForm) {
    paperReplaceForm.addEventListener("submit", function(e){
      e.preventDefault();
      const paperId = document.getElementById("paperModalPaperId").value;
      const fileInput = document.getElementById("paperModalNewFile");
      if (!paperId || !fileInput.files.length) return;

      const formData = new FormData();
      formData.append("file", fileInput.files[0]);

      fetch(`/papers/replace/${paperId}/`, {
        method: "POST",
        headers: { "X-CSRFToken": csrftoken },
        body: formData
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          alert("File replaced successfully!");
          closePaperModal();
          reloadPapers();
        } else {
          alert("Replace failed: " + data.error);
        }
      });
    });
  }

  // Close paper modal on ESC or backdrop click
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closePaperModal();
  });
  const paperModal = document.getElementById("paperModal");
  if (paperModal) {
    paperModal.addEventListener("click", (e) => {
      if (e.target === paperModal) closePaperModal();
    });
  }

  // Edit toggle
  const btn = document.getElementById("toggle-edit");
  if (btn) {
    btn.addEventListener("click", () => {
      window.__editMode = !window.__editMode;
      document.body.classList.toggle("edit-mode", window.__editMode);
      updateEditButtonUI();
      applyEditMode();
    });
    document.body.classList.toggle("edit-mode", window.__editMode);
    updateEditButtonUI();
  }

  // Load table
  reloadPapers();
});
