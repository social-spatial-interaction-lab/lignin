// === globals / setup ===
const csrftoken = Cookies.get('csrftoken');
let table;

const findResults = $("#find-results");
const paperTable = $("#paper-table");
const snowballResults = $("#snowball-results");

// === helpers ===
function escapeHtml(s){
  return String(s).replace(/[&<>"]/g, c => (
    { "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[c]
  ));
}
function slugify(s){ return s.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,''); }
function toggleModal(modalId, show) {
  const modal = document.getElementById(modalId);
  if (modal) modal.style.display = show ? 'block' : 'none';
}

// === NEW: Confirm & Generate handler ===
document.getElementById('confirm-generate-btn')?.addEventListener('click', async function () {
  const questions = [];
  document.querySelectorAll('.question-text').forEach(el => {
    questions.push(el.textContent.trim());
  });

  const pathParts = window.location.pathname.split('/');
  const questionId = pathParts[pathParts.indexOf('question') + 1];

  try {
    const response = await fetch(`/question/${questionId}/generate_answers/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrftoken
      },
      body: JSON.stringify({ questions })
    });

    const data = await response.json();
    console.log("Received answers:", data);
    renderQATable(data.answers);
  } catch (error) {
    console.error("Error generating answers:", error);
  }
});

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

      // Moving + persistence
      movableColumns: true,
      persistenceID: `paper-table-review-${questionID}`,
      persistenceMode: "local",
      persistence: { columns: ["order", "width", "visible", "frozen", "sort"] },

      // Header menu (delete dynamic columns only)
      columnHeaderMenu: function(){
        return [
          {
            label: "Delete column",
            action: function(e, column){
              const def = column.getDefinition();
              if (!def._column_id) {
                alert("This built-in column can't be deleted.");
                return;
              }
              if (!confirm(`Delete column "${def.title}"?`)) return;

              fetch("/column/delete/", {
                method: "POST",
                headers: { "X-CSRFToken": csrftoken, "Content-Type": "application/json" },
                body: JSON.stringify({ review: questionID, column_id: def._column_id }),
              })
              .then(r => r.ok ? r.json() : r.text().then(t => Promise.reject(t)))
              .then(res => {
                if (!res.ok) throw (res.error || "Delete failed");
                column.delete();
              })
              .catch(err => alert(err));
            }
          }
        ];
      },

      columns: [
        { title: "Title",  field: "title",  editor: "input" },
        { title: "Author", field: "author", editor: "input" },
        { title: "Year",   field: "year",   editor: "number", editorParams:{min:1800,max:2100,step:1} },
        { title: "Notes",  field: "notes",  editor: "textarea" },
        // Paper(s) + Delete columns are defined elsewhere in your earlier version
      ]
    });

    table.on("cellEdited", function(cell) {
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
      .then(d => { if (!d.success) alert("Update failed: " + d.error); });
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

// --- Create New Column handler (fixed) ---
document.addEventListener("DOMContentLoaded", () => {
  const link = document.getElementById("createColumnLink");
  if (!link) return;

  link.addEventListener("click", async (e) => {
    e.preventDefault();

    if (!table) { alert("Table is still loading—try again in a second."); return; }

    const review = link.getAttribute("data-review"); // {{ question_id }}
    const name = prompt("New column name?");
    if (!name) return;

    const fd = new FormData();
    fd.append("review", review);
    fd.append("name", name);
    fd.append("column_info", ""); // Column.column_info is non-null

    const resp = await fetch("/column/add/", {
      method: "POST",
      headers: { "X-CSRFToken": csrftoken },
      body: fd,
    });

    const respText = await resp.text();
    let respData;
    try { respData = JSON.parse(respText); }
    catch { respData = { ok: false, error: respText }; }

    if (!resp.ok || respData.ok === false) {
      alert(respData.error || `HTTP ${resp.status}`);
      return;
    }

    const colId = respData.column.id;
    const fieldKey = slugify(name);

    table.addColumn({
      title: name,
      field: fieldKey,
      hozAlign: "left",
      editor: "input",
      widthGrow: 1,
      _column_id: colId,   // returned from /column/add/
    }, true);    
  });
});

// Delegate click event for dynamically inserted #edit-btn
document.addEventListener("click", function (e) {
  if (e.target && e.target.id === "edit-btn") {
    openNestedModal();
  }
});
