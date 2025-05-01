import itertools
import json
import networkx as nx

from django import forms
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.core import serializers
from rules.contrib.views import PermissionRequiredMixin

from .models import Paper, Review, Value, Column, LigninUser, Entry
from collections import defaultdict
import requests
from rules import has_perm
from django.views.generic.edit import CreateView, UpdateView, DeleteView

import environ
env = environ.Env()
environ.Env.read_env()


def index(request):
    pks = [i.pk for i in Review.objects.all() if has_perm('ligninapp.view_review', request.user, i)]
    visible_questions = Review.objects.filter(id__in=pks)

    return render(request, template_name="ligninapp/index.html", context={
        "visible_questions": visible_questions
    })

def get_question(request, question_id):
    question = get_object_or_404(Review, id=question_id)
    return render(request, template_name="ligninapp/question.html", context={
        "question": question,
        "question_id": question_id
    })


class ReviewCreate(PermissionRequiredMixin, CreateView):
    model = Review
    fields = ['question_text', 'default_permission']
    permission_required = 'ligninapp.add_review'


class NewColumnForm(forms.Form):
    name = forms.CharField(max_length=200)
    review_to_add_to = forms.IntegerField(widget = forms.HiddenInput(), required = False)


def create_column(request):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = NewColumnForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required

            # Create the new column
            col = Column.objects.create(name=form.cleaned_data['name'])
            col.save()
            # add the column to the review
            review = Review.objects.get(pk=form.cleaned_data['review_to_add_to'])
            review.columns.add(col)
            review.save()

            # redirect to the review
            return HttpResponseRedirect(review.get_absolute_url())

    # if a GET (or any other method) we'll create a blank form
    else:
        form = NewColumnForm(initial={"review_to_add_to": int(request.GET['review'])})

    return render(request, "ligninapp/column_form.html", {"form": form})


def add_paper(request, question_id, paper_id):
    # check if the paper exists.
    paper_match_set = Paper.objects.filter(ssPaperID=paper_id)
    if paper_match_set:
        paper_match = paper_match_set[0]
    else:
        # make API call to Semantic Scholar.
        paper_details = requests.get(
            f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
            f"?fields=title,year,authors,citations.paperId,references.paperId",
            headers={"x-api-key": "PDPwFWmKA72Rlsuqd2xmF3YVZhB75BUd3ylD4a61"}
        ).json()

        print(paper_details)

        new_paper = Paper.objects.create(
            ssPaperID=paper_details['paperId'],
            title=paper_details['title'],
            year=int(paper_details['year']),
            faln=paper_details['authors'][0]['name'] + (" et al." if len(paper_details['authors']) > 1 else ""),
            references=" ".join([x["paperId"] for x in paper_details['references'] if x["paperId"]]),
            citations=" ".join([x["paperId"] for x in paper_details['citations'] if x["paperId"]]),
            url=f"https://www.semanticscholar.org/paper/{paper_details['paperId']}"
        )
        new_paper.save()
        paper_match = new_paper

    subpaper = paper_match.default_subpaper
    if subpaper is None:
        subpaper = Entry.objects.create(paper=paper_match, description="")
        subpaper.save()
        paper_match.default_subpaper = subpaper
        paper_match.save()

    Review.objects.get(id=question_id).entries.add(subpaper)

    return HttpResponse(status=201)


def get_papers(request, question_id):
    question = get_object_or_404(Review, id=question_id)

    # get columns for that question.
    columns = question.columns.all()
    paper_fields = ['year', 'faln'] # 'ssPaperID',

    # loop through the serialized files and pull relevant info
    result = []
    for subpaper in question.entries.all(): # these are objects, one by one.
        paper = subpaper.paper
        # extract the basics (year, faln, etc)
        paper_json = json.loads(serializers.serialize(
            'json',
            Paper.objects.filter(pk=paper.pk),
            fields=paper_fields))

        paper_info = paper_json[0]["fields"]  # there's guaranteed to be one and only one.
        paper_info["title"] = paper.title
        paper_info["link"] = paper.url
        paper_info["description"] = subpaper.description
        paper_info["id"] = subpaper.id
        for column in columns:
            descriptions = Value.objects.filter(column=column, entry=subpaper)
            paper_info[column.name] = descriptions[0].value if descriptions else ""

        result.append(paper_info)
        #

    column_mds = [
        {"title": "Title", "field": "title", "formatter": "textarea"},
        {"title": "Link", "field": "link", "formatter": "link", "formatterParams": {
            "label": "@",
            "target": "_blank"
        }}
    ]

    for title in paper_fields: #["description", "id"]:
        column_md = {}
        column_md["title"] = title
        column_md["field"] = title
        column_mds.append(column_md)

    for column in columns:
        column_md = {}
        column_md["title"] = column.name
        column_md["field"] = column.name
        column_md["editor"] = True
        column_md["column_id"] = column.id
        column_md["formatter"] = "textarea"
        column_md["headerPopupIcon"] = "&#128712;"
        if column.column_info:
            column_md["headerPopup"] = column.column_info.replace("\n", "<br />\n")
        column_mds.append(column_md)

    # add IDs

    # rectangle:
    # {id: f..
    #  	{id:4, name:"Brendon Philips", age:"125", col:"orange", dob:"01/08/1980"},
    #  	{id:5, name:"Margret Marmaduke", age:"16", col:"yellow", dob:"31/01/1999"},
    # "column_metadata: [
    # 	 	{title:"Favourite Color", field:"col"},
    # 	 	{title:"Date Of Birth", field:"dob", sorter:"date", hozAlign:"center"},
    # 	 	]
    return JsonResponse({
        "data": result,
        "metadata": column_mds
    })


def edit_annotation(request, entry_id, column_pk):
    # if it already exists, edit it.
    value_text = request.POST["value_text"]
    note_text = request.POST["note_text"]
    entry = get_object_or_404(Entry, id=entry_id)
    column = get_object_or_404(Column, pk=column_pk)
    lignin_user = get_object_or_404(LigninUser, owner=request.user)

    value, was_created = Value.objects.get_or_create(entry=entry, column=column, creator=lignin_user)
    value.value = value_text
    # value.notes = note_text
    value.save()
    return HttpResponse(200)


def reject_paper(request, question_id, paper_id):
    question = get_object_or_404(Review, id=question_id)

    # if it's already there, ignore the request.
    if paper_id in question.rejected_papers:
        return HttpResponse(204)

    # Otherwise, add the paper (with perhaps a space)
    if question.rejected_papers:
        question.rejected_papers += " " + paper_id
    else:
        question.rejected_papers = paper_id
    question.save()
    return HttpResponse(201)

def average_path_distance(G):
    full_graph_order = G.order()
    nodes_accounted_for = 0
    node_pairs = 0
    path_sum = 0
    for C in (G.subgraph(c).copy() for c in nx.connected_components(G)):
        cluster_nodes = C.order()
        cluster_pairs = C.order() * (C.order() - 1) / 2

        path_sum += cluster_nodes * nodes_accounted_for * full_graph_order # penalize every non-link between notes with full graph order path.
        node_pairs += cluster_nodes * nodes_accounted_for

        path_sum += nx.average_shortest_path_length(C) * cluster_pairs
        node_pairs += cluster_pairs

        nodes_accounted_for += cluster_nodes

    return path_sum / node_pairs

def average_path_distance_shorten(G, nodeignore):
    path_sum = average_path_distance(G) * G.order() * (G.order() - 1) / 2
    remove_total = 0

    for C in (G.subgraph(c).copy() for c in nx.connected_components(G)):
        if nodeignore in C:
            remove_total += sum([v for k, v in nx.shortest_path_length(G, source = nodeignore).items()])
        else:
            remove_total += G.order() * C.order()

    return float(path_sum - remove_total) / ((G.order() - 2) * (G.order() - 1) / 2)

def get_snowball(request, question_id):
    question = get_object_or_404(Review, id=question_id)
    #included_papers = question.papers.all()


    # foo_queryset = Foo.objects.filter(attr=value)
    # referenced_bars = foo_queryset.bar_set.all()
    included_papers = Paper.objects.filter(ssPaperID__in=question.entries.values('paper__ssPaperID'))

    rejected_paper_ids = question.rejected_papers.split(" ") if question.rejected_papers else []
    ignored_paper_ids = [x.ssPaperID for x in included_papers] + rejected_paper_ids
    id_strings = [x.references.split(" ") + x.citations.split(" ") for x in included_papers]
    snowball_set_size = len(id_strings)

    id_to_links = dict([(x.ssPaperID, x.references.split(" ") + x.citations.split(" ")) for x in included_papers])


    counter_dict = defaultdict(int)
    for paper_links in id_strings:
        for paper_id in paper_links:
            counter_dict[paper_id] += 1

    refs_dict = defaultdict(list)
    for paper_id, paper_links in id_to_links.items():
        for linked_paper_id in paper_links:
            refs_dict[linked_paper_id].append(paper_id)

    most_refs = sorted(counter_dict.items(), key=lambda item: item[1], reverse=True)
    most_refs_filtered = [x for x in most_refs if x[0] not in ignored_paper_ids]
    pct_dict = dict()
    #print(most_refs)
    #print(most_refs_filtered)
    #print(refs_dict)

    G = nx.Graph()
    G.add_nodes_from([paper_id for paper_id, _ in id_to_links.items()])
    G.add_edges_from([
        (paper_id_a, paper_id_b)
        for paper_id_a, paper_links_a in id_to_links.items()
        for paper_id_b, _ in id_to_links.items()
        if paper_id_b in paper_links_a
    ])

    apl = average_path_distance(G)
    apl_drop = dict()
    for i in counter_dict.items():
        if i[0] not in ignored_paper_ids and i[1] > 1:
            G2 = G.copy()
            G2.add_edges_from([(i[0], j) for j in refs_dict[i[0]]])
            apl_drop[i[0]] = apl - average_path_distance_shorten(G2, i[0])

    #print(apl_drop)

    most_drop = sorted(apl_drop.items(), key=lambda item: item[1], reverse=True)\


    # question: is X related to Y?
    for i in most_drop[:50]:
        pair_is_linked = []
        for paper_a_id, paper_b_id in itertools.combinations(refs_dict[i[0]], 2):
            paper_a = Paper.objects.get(ssPaperID=paper_a_id)
            pair_is_linked.append(paper_b_id in paper_a.references.split(" ") or paper_b_id in paper_a.citations.split(" "))
        #print(pair_is_linked)
        #print(sum(pair_is_linked) / float(len(pair_is_linked)))
        if len(pair_is_linked) == 0:
            pct_dict[i[0]] = 0.0
        else:
            pct_dict[i[0]] = sum(pair_is_linked) / float(len(pair_is_linked))
        #print()

    # another metric - what bridges the most pairs?
    # (if I add this paper, what is the new total reach-to-reach drop?
    # get all n2n distance?
    # "bridges you wouldn't expect"
    # so like,


    r = requests.post(
        "https://api.semanticscholar.org/graph/v1/paper/batch?fields=title,year,authors,url",
        json={"ids": [x[0] for x in most_drop[:50]]}
    )

    response = r.json()
    print(response)

    for paper in response:
        if paper:
            paper["occurrence_number"] = apl_drop[paper['paperId']] # counter_dict[paper['paperId']]
            paper["occurrence"] = f"{counter_dict[paper['paperId']]}/{snowball_set_size} ({pct_dict[paper['paperId']]:.3f}) ({apl_drop[paper['paperId']]:.3f})"

    return JsonResponse({"data": sorted([i for i in response if i], key=lambda x: x["occurrence_number"], reverse=True)})

