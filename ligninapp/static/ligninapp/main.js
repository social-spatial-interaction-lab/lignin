const csrftoken = Cookies.get('csrftoken');

const findResults = $("#find-results");
const paperTable = $("#paper-table");
const snowballResults = $("#snowball-results");

function toggleFullWidth() {
    $("#paper-table-container").toggleClass("fullwidth");
}

function addPaper() {
    let paperId = $(this).attr("data-lignin-paperId");
    const thisButton = this;
    $.ajax({
        url: '/question/' + questionID + '/papers/add/' + paperId + '/',
        headers: {
            'X-CSRFToken': csrftoken
        },
        type: 'PUT',
        success: function(result) {
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
        headers: {
            'X-CSRFToken': csrftoken
        },
        type: 'PUT',
        success: function(result) {
            $(thisButton).closest('tr').remove();
        }
    });
}

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
        dataKeys.concat(additionalKeys)
            .map(keyname => $("<th>").text(keyname))
    ));
    table.append(array.map(entry => $("<tr>").attr("data-lignin-paperId", entry["ssPaperID"] || entry["paperId"]).append(
        dataKeys.map(keyname => $("<td>").text(stringOrFALN(keyname, entry)).attr("data-lignin-columnId", columnIDs[keyname]))
            .concat(additionalKeys.map(keyname => additional[keyname](entry)))
    )));
    return table;
}

function titleAndLink(entry) {
    return $("<td>").append($("<a>").text(entry["title"]).attr("href", entry["url"]).attr("target", "_blank"));
}

$("#find").submit(function() {
    const queryVal = $("#find-query").val();

    $.get({
        url: "https://api.semanticscholar.org/graph/v1/paper/search?query=" + encodeURI(queryVal) + "&fields=title,year,authors,url",
        success: function(data) {
            const table = arrayToTable(data.data, {
                "Title": titleAndLink,
                "add?": entry => $("<td>").append($("<button>").text("add").attr("data-lignin-paperId", entry["paperId"]).click(addPaper))
            }, ["paperId", "url"], {});
            findResults.empty();
            findResults.append(table);
        },
        dataType: 'json',
        headers: {
            "accept": "application/json",
            "x-api-key": "PDPwFWmKA72Rlsuqd2xmF3YVZhB75BUd3ylD4a61"
        }
    });

    return false;
});

$("#snowball").submit(function() {
    $.get('/question/' + questionID + '/snowball/', {}, function(data) {
        const table = arrayToTable(data.data, {
            "Title": titleAndLink,
            "add?": entry => $("<td>").append($("<button>").text("add").attr("data-lignin-paperId", entry["paperId"]).click(addPaper)),
            "reject?": entry => $("<td>").append($("<button>").text("reject").attr("data-lignin-paperId", entry["paperId"]).click(rejectPaper))
        }, ['paperId', 'url', 'title', 'occurrence_number'], {});
        snowballResults.empty();
        snowballResults.append(table);
    });
    return false;
});

function triggerReplace(paperId) {
    alert("Replace triggered for paper ID: " + paperId);
    // TODO: Implement modal or file upload for replacing PDF
}

function triggerReplace(paperId) {
    const modal = document.getElementById("replaceModal");
    modal.style.display = "block";
    document.getElementById("replacePaperId").value = paperId;
}

function closeReplaceModal() {
    document.getElementById("replaceModal").style.display = "none";
}


function reloadPapers() {
    $.get('/question/' + questionID + '/papers/', {}, function(data) {
        var table = new Tabulator("#paper-table", {
            maxHeight: "80vh",
            height: "80vh",
            data: data.data,
            layout: "fitData",
            renderHorizontal: "virtual",
            editTriggerEvent: "dblclick",
            persistence: {
                columns: ["width"]
            },
            columns: [
                { title: "Title", field: "title", editor: "input" },
                { title: "Author", field: "author", editor: "input" },
                { title: "Year", field: "year", editor: "input" },
                { title: "Notes", field: "notes" },
                {
                    title: "Actions",
                    field: "url",
                    formatter: function(cell, formatterParams, onRendered) {
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
                            headers: {
                                "X-CSRFToken": csrftoken,
                            },
                        })
                        .then(res => res.json())
                        .then(data => {
                            if (data.success) {
                                cell.getRow().delete();
                            } else {
                                alert("Delete failed: " + data.error);
                            }
                        });
                    }
                }
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
                }),
            })
            .then((res) => res.json())
            .then((data) => {
                if (!data.success) {
                    alert("Update failed: " + data.error);
                }
            });
        });

        $("#loading-indicator").hide();
    }, 'json');
}

reloadPapers();


document.getElementById("replaceForm").addEventListener("submit", function(e) {
    e.preventDefault();

    const paperId = document.getElementById("replacePaperId").value;
    const fileInput = document.getElementById("newFile");
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    fetch(`/papers/replace/${paperId}/`, {
        method: "POST",
        headers: {
            "X-CSRFToken": csrftoken
        },
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
