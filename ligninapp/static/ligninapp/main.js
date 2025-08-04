// === globals / setup ===
const csrftoken = Cookies.get('csrftoken');
window.__editMode = false;   // edit mode off by default
let table;                   // Tabulator instance

const findResults = $("#find-results");
const paperTable = $("#paper-table");
const snowballResults = $("#snowball-results");

// === layout controls ===
function toggleFullWidth() {
  $("#paper-table-container").toggleClass("fullwidth");
}

// === add / reject from search & snowball (kept as-is if you use them elsewhere) ===
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

// === helpers used by search/snowball (safe to keep) ===
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

// === replace file modal ===
function triggerReplace(paperId) {
  const modal = document.getElementById("replaceModal");
  modal.style.display = "block";
  document.getElementById("replacePaperId").value = paperId;
}
function closeReplaceModal() {
  document.getElementById("replaceModal").style.display = "none";
}

// === click-pencil helper: turn on Edit mode and edit this cell ===
function enterEditModeAndEdit(cell) {
  if (!window.__editMode) {
    window.__editMode = true;
    document.body.classList.toggle("edit-mode", true);
    updateEditButtonUI();
    applyEditMode();                // inject editors
  }
  cell.edit(true);                  // open editor for this specific cell
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
    enterEditModeAndEdit(cell);     // <- flip Edit ON + open editor
  });

  wrap.appendChild(span);
  wrap.appendChild(btn);
  return wrap;
}

// === table loader ===
function reloadPapers() {
  $.get('/question/' + questionID + '/papers/', {}, function(data) {
    // Destroy any prior table instance (prevents lingering settings)
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
      editTriggerEvent: "dblclick",   // dblclick still works while in Edit mode
      persistence: { columns: ["width"] },
      columns: [
        { title: "Title",  field: "title",  editor: false, formatter: editableCellFormatter },
        { title: "Author", field: "author", editor: false, formatter: editableCellFormatter },
        { title: "Year",   field: "year",   editor: false, editorParams:{ min:1800, max:2100, step:1 }, formatter: editableCellFormatter },
        { title: "Notes",  field: "notes",  editor: false, formatter: editableCellFormatter },
        {
          title: "Actions",
          field: "url",
          formatter: function(cell) {
            const fileUrl = cell.getValue();
            const paperId = cell.getRow().getData().id.replace("upload-", "");
            return `
              <a href="${fileUrl}" target="_blank" style="margin-right: 10px;">🔍 View</a>
              <button onclick="triggerReplace('${paperId}')">📝 Replace</button>
            `;
          },
          widthGrow: 2
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

    // Gate editing attempts entirely when not in Edit mode (safety)
    table.on("cellEditing", function(cell){
      if (!window.__editMode) return false; // returning false cancels editing
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

    // Apply current mode (starts with no editors)
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
  // optional styling toggles
  btn.classList.toggle("btn-success", window.__editMode);
  btn.classList.toggle("btn-outline-warning", !window.__editMode);
}

// === single DOMContentLoaded block ===
document.addEventListener("DOMContentLoaded", () => {
  // Replace form submit (guarded)
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

  // Edit toggle
  const btn = document.getElementById("toggle-edit");
  if (btn) {
    btn.addEventListener("click", () => {
      window.__editMode = !window.__editMode;
      document.body.classList.toggle("edit-mode", window.__editMode); // optional if you style differently in edit mode
      updateEditButtonUI();
      applyEditMode();
    });
    // initial UI state
    document.body.classList.toggle("edit-mode", window.__editMode);
    updateEditButtonUI();
  }

  // Load table
  reloadPapers();
});
