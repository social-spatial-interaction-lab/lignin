const csrftoken = Cookies.get('csrftoken');

const findResults = $("#find-results");
const paperTable = $("#paper-table");
const snowballResults = $("#snowball-results");

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
            const target = $(thisButton).closest('tr');
            console.log(thisButton);
            console.log(target)
            target.remove();
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
function arrayToTable(array, additional, drop) {
    // additional is key-value pars,
    const dataKeys = Object.keys(array.reduce(function(acc, curr) {Object.keys(curr).forEach(x => acc[x] = true); return acc;}, {})).filter(item => !drop.includes(item));
    const additionalKeys = Array.from(Object.keys(additional));
    const table = $("<table>");
    // Create the header row by merging the keys from the data with additional, javascript-defined keys
    table.append($("<tr>").append(
        dataKeys.concat(additionalKeys)
            .map(keyname => $("<th>").text(keyname))
        ));
    // Create each paper row by creating the td cells then merging with the other td cells
    table.append(array.map(entry => $("<tr>").append(
        dataKeys.map(keyname => $("<td>").text(stringOrFALN(keyname, entry)))
            .concat(additionalKeys.map(keyname => additional[keyname](entry)))
    )));
    return table;
}

$("#find").submit(function() {
    const queryVal = $("#find-query").val();

    $.getJSON(
        "https://api.semanticscholar.org/graph/v1/paper/search?query=" + encodeURI(queryVal) + "&fields=title,year,authors",
        {},
        function(data) {
            const table = arrayToTable(data.data, {
                "add?" : entry => $("<td>").append($("<button>").text("add").attr("data-lignin-paperId", entry["paperId"]).click(addPaper))
            }, []);
            findResults.empty();
            findResults.append(table);
        });

    return false;
});

$("#snowball").submit(function() {
    $.get(
        '/question/' + questionID + '/snowball/', {},
        function( data ) {
            const table = arrayToTable(data.data, {
                "add?" : entry => $("<td>").append($("<button>").text("add").attr("data-lignin-paperId", entry["paperId"]).click(addPaper))
            }, ['paperId', 'url']);
            snowballResults.empty();
            snowballResults.append(table);
        }
    )
    return false;
})

function reloadPapers() {
    $.get(
        '/question/' + questionID + '/papers/', {},
        function( data ) {
            const table = arrayToTable(data.data, {}, ["ssPaperID"]);
            paperTable.empty();
            paperTable.append(table);
        },
        'json'
    );
}

reloadPapers();
