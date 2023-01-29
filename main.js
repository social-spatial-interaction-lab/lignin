
const outputDivTable = $("#output-div-table");

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
    var table = $("<table>");
    table.append($("<tr>").append(allKeys.map(keyname => $("<th>").text(keyname))));
    table.append(array.map(entry => $("<tr>").append(allKeys.map(keyname => $("<td>").text(stringOrFALN(keyname, entry))))));
    return table;
}

function displayData(data) {
    console.log(data);
    var table = arrayToTable(data.data, {thead: true});

    outputDivTable.empty();
    outputDivTable.append(table);
}

function displayCites(data) {
    console.log(data);
    var table = arrayToTable(data.data.map(x => x.citingPaper), {thead: true});

    outputDivTable.empty();
    outputDivTable.append(table);
}

function displayRefs(data) {
    console.log(data);
    var table = arrayToTable(data.data.map(x => x.citedPaper), {thead: true});

    outputDivTable.empty();
    outputDivTable.append(table);
}

function displayBatch(data) {
    console.log(data);
    var table = arrayToTable(data, {thead: true});

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

$("#refs").submit(function() {
    const idVal = $("#r-id").val();

    $.getJSON(
        "https://api.semanticscholar.org/graph/v1/paper/" + idVal + "/references?fields=paperId&limit=1000",
        {},
        displayRefs
    );

    return false;
});

$("#cites").submit(function() {
    const idVal = $("#c-id").val();

    $.getJSON(
        "https://api.semanticscholar.org/graph/v1/paper/" + idVal + "/citations?fields=paperId&limit=1000",
        {},
        displayCites
    );

    return false;
});

function arrayToCounts(arr) {
    return arr.reduce(function(acc, cv) {
        if (cv in acc) {
            acc[cv] += 1;
        } else {
            acc[cv] = 1;
        }
        return acc;
    }, {});
}

$("#tops").submit(function() {
    const topIDs = $("#tops-ids").val().match(/[0-9a-f]{40}/g);
    const rejectedIDs = $("#rejected-ids").val().match(/[0-9a-f]{40}/g);

    console.log(rejectedIDs);
    console.log(topIDs);
    console.log(topIDs.filter(x => !rejectedIDs.includes(x)));

    const counts = arrayToCounts(topIDs.filter(x => !rejectedIDs.includes(x)));
    const commons = Object.keys(counts).sort(function(a,b){return counts[b]-counts[a]});

    $.post(
        "https://api.semanticscholar.org/graph/v1/paper/batch?fields=title,year,citationCount",
        JSON.stringify({ids: commons.slice(0, 10)}),
        displayBatch,
        "json"
    ).fail(function(ff) {
        console.log(ff);
    })

    return false;
});

$("#view").submit(function() {
    const viewID = $("#view-id").val();

    $.getJSON(
        "https://api.semanticscholar.org/graph/v1/paper/" + viewID + "?fields=title,abstract,url",
        {},
        function(data) {
            console.log(data);
            $("#title").text(data.title);
            $("#abstract").text(data.abstract);
            $("#paper-frame").attr('src', data.url);
            // $("paper-object").attr('data', data.url);
            //$("#paper-view").attr('data', "https://www.youtube.com/embed/O5hShUO6wxs");
        }
    );

    return false;
})