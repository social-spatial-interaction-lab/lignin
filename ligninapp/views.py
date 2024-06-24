import json

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
        paper_info["title"] = f"<a target=\"_blank\" href=\"{paper.url}\">{paper.title}</a>"
        paper_info["description"] = subpaper.description
        paper_info["id"] = subpaper.id
        for column in columns:
            descriptions = Value.objects.filter(column=column, entry=subpaper)
            paper_info[column.name] = descriptions[0].value if descriptions else ""

        result.append(paper_info)
        #

    column_mds = [{"title":"Title", "field":"title", "formatter":"html"}]

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


def get_snowball(request, question_id):
    question = get_object_or_404(Review, id=question_id)
    #included_papers = question.papers.all()


    # foo_queryset = Foo.objects.filter(attr=value)
    # referenced_bars = foo_queryset.bar_set.all()
    included_papers = question.entries.paper.all()

    print(included_papers)
    print("aef")
    print("aef")

    rejected_paper_ids = question.rejected_papers.split(" ") if question.rejected_papers else []
    ignored_paper_ids = [x.ssPaperID for x in included_papers] + rejected_paper_ids
    id_strings = [x.references.split(" ") + x.citations.split(" ") for x in included_papers]
    snowball_set_size = len(id_strings)

    d = defaultdict(int)
    for paper_links in id_strings:
        for paper_id in paper_links:
            d[paper_id] += 1

    most_refs = sorted(d.items(), key=lambda item: item[1], reverse=True)
    most_refs_filtered = [x for x in most_refs if x[0] not in ignored_paper_ids]
    #print(most_refs)
    #print(most_refs_filtered)

    r = requests.post(
        "https://api.semanticscholar.org/graph/v1/paper/batch?fields=title,year,authors,url",
        json={"ids": [x[0] for x in most_refs_filtered[:10]]}
    )

    response = r.json()
    print(response)

    for paper in response:
        paper["occurrence_number"] = d[paper['paperId']]
        paper["occurrence"] = f"{d[paper['paperId']]}/{snowball_set_size}"

    return JsonResponse({"data": sorted(response, key=lambda x: x["occurrence_number"], reverse=True)})

