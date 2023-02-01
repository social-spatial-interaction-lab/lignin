const csrftoken = Cookies.get('csrftoken');

const outputDivTable = $("#output-div-table");

function addPaper() {
    let paperId = $(this).attr("data-lignin-paperId");
    $.ajax({
        url: '/question/' + questionID + '/add/paper/' + paperId + '/',
        headers: {
            'X-CSRFToken': csrftoken
        },
        type: 'PUT',
        success: function(result) {
            console.log("success");
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
function arrayToTable(array, options) {
    const allKeys = Object.keys(array.reduce(function(acc, curr) {Object.keys(curr).forEach(x => acc[x] = true); return acc;}, {}));
    console.log(allKeys);
    const table = $("<table>");
    const headerRow = $("<tr>").append(allKeys.map(keyname => $("<th>").text(keyname)).concat([$("<th>").text("add?")]))// .append($("<td>").append($("<button>")))
    table.append(headerRow);
    table.append(array.map(entry => $("<tr>").append(
        allKeys.map(keyname => $("<td>").text(stringOrFALN(keyname, entry))).concat([
            $("<td>").append($("<button>").text("add").attr("data-lignin-paperId", entry["paperId"]).click(addPaper))
        ])
    )));
    return table;
}

function displayData(data) {
    console.log(data);
    const table = arrayToTable(data.data, {thead: true});

    outputDivTable.empty();
    outputDivTable.append(table);
}

$("#find").submit(function() {
    const queryVal = $("#find-query").val();

    $.getJSON(
        "https://api.semanticscholar.org/graph/v1/paper/search?query=" + encodeURI(queryVal) + "&fields=title,year,authors",
        {},
        displayData
        );

    return false;
});