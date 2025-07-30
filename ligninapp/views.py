import json
from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.core import serializers
from rules.contrib.views import PermissionRequiredMixin
from .models import Paper, Review, Value, Column, LigninUser, Entry
from collections import defaultdict
import requests
from rules import has_perm
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .forms import UploadedPaperForm, ReviewForm
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.shortcuts import redirect


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

    def get_initial(self):
        initial = super().get_initial()
        if 'title' in self.request.GET:
            initial['question_text'] = self.request.GET['title']
        return initial



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
        # When references are elided, the reference list can be None rather than an empty list. :(
        if paper_details['references'] is None:
            paper_details['references'] = []

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


from django.http import JsonResponse
from .models import Paper, UploadedPaper, Value

def get_papers(request, question_id):
    question = get_object_or_404(Question, id=question_id)

    # Normal papers
    papers = Paper.objects.filter(question=question)
    values = Value.objects.filter(paper__in=papers)

    # Uploaded papers
    uploaded = UploadedPaper.objects.filter(question=question)

    # Combine into a unified list
    data = []

    for paper in papers:
        row = {
            "id": paper.id,
            "title": paper.title,
            "type": "semantic",  # can be used to distinguish
        }
        # Populate grid values
        for val in values.filter(paper=paper):
            row[val.column.name] = val.value_text
        data.append(row)

    for up in uploaded:
        row = {
            "id": f"upload-{up.id}",
            "title": up.title,
            "link": up.file.url,
            "uploaded_at": up.uploaded_at.strftime('%Y-%m-%d %H:%M'),
            "type": "upload"
        }
        data.append(row)

    # Add column headers dynamically if needed
    metadata = [
        {"title": "Title", "field": "title"},
        {"title": "Link", "field": "link", "formatter": "link"},
        {"title": "Uploaded", "field": "uploaded_at"},
    ]

    return JsonResponse({
        "data": data,
        "metadata": metadata
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
    included_papers = Paper.objects.filter(ssPaperID__in=question.entries.values('paper__ssPaperID'))

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
        if paper:
            paper["occurrence_number"] = d[paper['paperId']]
            paper["occurrence"] = f"{d[paper['paperId']]}/{snowball_set_size}"

    return JsonResponse({"data": sorted([i for i in response if i], key=lambda x: x["occurrence_number"], reverse=True)})

def upload_paper(request):
    if request.method == 'POST':
        form = UploadedPaperForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/')  # adjust redirect as needed
    else:
        form = UploadedPaperForm()
    return render(request, 'ligninapp/upload_paper.html', {'form': form})


def create_review(request):
    title = request.GET.get("title", "").strip()
    if title:
        review = Review.objects.create(question_text=title, default_permission='MOD')
    return redirect("question", question_id=review.id)
    return redirect("index")  # fallback if title is empty

@require_POST

def save_review_title(request):
    title = request.POST.get("title", "").strip()
    if not title:
        return JsonResponse({"error": "Missing title"}, status=400)

    review = Review.objects.create(
        question_text=title,
        default_permission="VIEW",
    )

    return JsonResponse({"redirect_url": reverse("add-columns-papers", args=[review.id])})

def add_columns_papers(request, review_id):
    review = get_object_or_404(Review, pk=review_id)
    return render(request, "ligninapp/add_columns_papers.html", {"review": review})

def upload_paper_modal(request, question_id):
    review = get_object_or_404(Review, id=question_id)
    if request.method == 'POST':
        form = UploadedPaperForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_paper = form.save(commit=False)
            uploaded_paper.review = review
            uploaded_paper.save()
            return redirect('question', question_id=question_id)
    return redirect('question', question_id=question_id)