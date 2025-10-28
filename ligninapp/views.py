import json
import logging

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
from django.views.decorators.http import require_GET
from django.urls import reverse
from django.shortcuts import redirect
from .models import UploadedPaper
from django.views.decorators.http import require_http_methods
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Prefetch
from django.contrib import messages
from django.db import transaction
import os
from urllib.parse import unquote

from .LLM_response import LLM_entrance

import environ
env = environ.Env()
environ.Env.read_env()

logger = logging.getLogger(__name__)

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

#10.20 column-delete  
def get_papers(request, question_id):
    review = get_object_or_404(Review, id=question_id)

    columns_qs = review.columns.all().only("id", "name")
    columns = list(columns_qs.values_list("id", "name"))  # [(id, name), ...]
    col_id_to_name = {cid: name for cid, name in columns}
    col_ids = [cid for cid, _ in columns]
    col_names = [name for _, name in columns]

    entries_qs = (
        review.entries
        .prefetch_related(
            Prefetch(
                "value_set",
                queryset=Value.objects.filter(column_id__in=col_ids).only("column_id", "value"),
            )
        )
        .only("id")
    )

    rows = []
    for entry in entries_qs:
        row = {"entry_id": entry.id}
        for name in col_names:
            row[name] = ""
        for v in entry.value_set.all():
            name = col_id_to_name.get(v.column_id)
            if name:
                row[name] = v.value or ""
        rows.append(row)

    payload = {
        "columns": col_names,  # Compatible with the old frontend
        "columns_meta": [{"id": cid, "name": name} for cid, name in columns],
        "rows": rows,
    }
    return JsonResponse(payload, safe=False)



@require_POST
def edit_annotation(request, entry_id, column_pk):
    value_text = request.POST.get("value_text", "")
    # note_text = request.POST.get("note_text", "")

    entry  = get_object_or_404(Entry, id=entry_id)
    column = get_object_or_404(Column, pk=column_pk)

    # First try to locate an existing value while ignoring the creator; if none exists, create one
    value = Value.objects.filter(entry=entry, column=column).order_by("-id").first()
    if value is None:
        value = Value(entry=entry, column=column)  # No longer dependent on LigninUser/creator

    value.value = value_text
    # value.notes = note_text
    value.save()
    return HttpResponse(status=204)



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
#10.20 Create Entry and Uploadedpaper.So it can upload the pdf file.
@transaction.atomic
def upload_paper(request, question_id):
    review = get_object_or_404(Review, id=question_id)

    if request.method != "POST":
        return redirect("question", question_id)

    f = request.FILES.get("file")
    if not f:
        messages.error(request, "No file received.")
        return redirect("question", question_id)

    # 1) Physically save the PDF
    paper = UploadedPaper.objects.create(
        review=review,
        title=os.path.splitext(os.path.basename(f.name))[0],
        file=f,
    )

    # 2) Create an Entry, attach it to the Review, and link it to the UploadedPaper in the backend
    entry = Entry.objects.create(description="", uploaded_paper=paper)
    review.entries.add(entry)

    # 3) Only write the file_name column (no longer write file_url)
    file_name_col, _ = Column.objects.get_or_create(name="file_name")
    review.columns.add(file_name_col)
    Value.objects.create(entry=entry, column=file_name_col, value=os.path.basename(paper.file.name))

    messages.success(request, f"Uploaded: {os.path.basename(paper.file.name)}")
    return redirect("question", question_id)

@require_http_methods(["DELETE"])
def delete_uploaded_paper(request, paper_id):
    try:
        paper = UploadedPaper.objects.get(pk=paper_id)
        paper.delete()
        return JsonResponse({'success': True})
    except UploadedPaper.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Paper not found'}, status=404)

#10.20 delete-column
@require_http_methods(["POST"])
@transaction.atomic
def remove_column_from_review(request, review_id, column_id):
    review = get_object_or_404(Review, pk=review_id)
    column = get_object_or_404(Column, pk=column_id)

    # Only allow the operation if the column belongs to the current review
    if not review.columns.filter(pk=column.pk).exists():
        return JsonResponse({"ok": False, "error": "Column not in this review"}, status=400)

    # 1) Delete all Values in this column under the current review’s entries
    entry_ids = list(review.entries.values_list("id", flat=True))
    Value.objects.filter(column=column, entry_id__in=entry_ids).delete()

    # 2) Remove this column from the review's column set
    review.columns.remove(column)

    # 3) Optional cleanup: if this column is no longer used by any review and has no remaining Value, physically delete it
    if not column.review_set.exists() and not Value.objects.filter(column=column).exists():
        column.delete()

    return JsonResponse({"ok": True})

#10.20 delete-row
@require_http_methods(["POST"])
@transaction.atomic
def remove_entry_from_review(request, review_id, entry_id):
    review = get_object_or_404(Review, pk=review_id)
    entry = get_object_or_404(Entry, pk=entry_id)

    # Check whether the entry belongs to the current review
    if not review.entries.filter(pk=entry.pk).exists():
        return JsonResponse({"ok": False, "error": "This entry does not belong to this review."}, status=400)

    # 1. Unlink it from the current review
    review.entries.remove(entry)

    # 2. If the entry no longer belongs to any review, safely delete it
    if not entry.review_set.exists():
        Value.objects.filter(entry=entry).delete()
        entry.delete()

    return JsonResponse({"ok": True})

@require_http_methods(["POST"])
def update_uploaded_paper(request, paper_id):
    try:
        paper = UploadedPaper.objects.get(pk=paper_id)
        data = json.loads(request.body)

        paper.title = data.get("title", paper.title)
        paper.author = data.get("author", paper.author)
        paper.year = data.get("year", paper.year)
        paper.save()

        return JsonResponse({'success': True})
    except UploadedPaper.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Paper not found'}, status=404)

@require_http_methods(["POST"])
def replace_uploaded_paper(request, paper_id):
    try:
        paper = UploadedPaper.objects.get(pk=paper_id)
        new_file = request.FILES.get("file")
        if not new_file:
            return JsonResponse({"success": False, "error": "No file uploaded"})

        paper.file = new_file
        paper.save()

        return JsonResponse({"success": True})
    except UploadedPaper.DoesNotExist:
        return JsonResponse({"success": False, "error": "Paper not found"}, status=404)
    
def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # from django.contrib.auth.urls
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@require_http_methods(["POST"])
def generate_request_accept_view(request, question_id):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        columns_obj = payload.get("columns", {})
        urls_obj = payload.get("urls", {})

        # 1) Call the LLM
        results_per_url = LLM_entrance(columns_obj, urls_obj, include_highlights=True)

        # 2) Split (for frontend compatibility)
        qa_only, highlights_only = [], []
        for item in results_per_url:
            qa_payload = (item or {}).get("qa", {}) or {}
            hl_payload = (item or {}).get("highlights", None)
            qa_only.append(qa_payload)
            highlights_only.append(hl_payload)

        llm_text = qa_only

        # 3) Write answers into EAV (only answers, do not handle highlights)
        review = get_object_or_404(Review, id=question_id)

        # Column "file_name" used for locating the row (note: column name is "file_name")
        file_name_col, _ = Column.objects.get_or_create(name="file_name")
        # If this column is not yet in the review’s column set, add it
        if not review.columns.filter(pk=file_name_col.pk).exists():
            review.columns.add(file_name_col)

        # For convenience: fetch all entries of the current review first for set filtering
        review_entry_ids = set(review.entries.values_list("id", flat=True))

        # Try to get LigninUser as the creator (optional)
        try:
            creator = getattr(request.user, "lignin_user", None)
        except Exception:
            creator = None

        @transaction.atomic
        def persist_answers():
            for item in (results_per_url or []):
                qa = (item or {}).get("qa", {}) or {}
                hl = (item or {}).get("highlights", {}) or {}
                url = (qa.get("url") or "").strip()
                if not url:
                    continue

                # URL -> filename (decode %20, etc.
                base = os.path.basename(url)
                filename = unquote(base).strip()
                if not filename:
                    continue

                # Use file_name to locate the entry (limited to the current review)
                entry_qs = (
                    Value.objects
                    .filter(column=file_name_col, value=filename, entry_id__in=review_entry_ids)
                    .values_list("entry_id", flat=True)
                )
                entry_id = next(iter(entry_qs), None)
                if not entry_id:
                    # The row may be empty or lack a file_name; you can choose to skip or create it here
                    continue

                answers_by_q = qa.get("answers_by_question") or {}
                if not isinstance(answers_by_q, dict) or not answers_by_q:
                    continue

                # Preload the two tables "question -> highlights" for this URL (for writing highlights per question)
                anchors_by_q   = hl.get("anchors_by_question")   or {}
                locations_by_q = hl.get("locations_by_question") or {}
                doc_info       = hl.get("doc")                   or {}

                # Write answers for each "question column name"
                for question_title, answer in answers_by_q.items():
                    col_name = (question_title or "").strip()
                    if not col_name:
                        continue
                    # Skip reserved column names
                    if col_name in {"File name", "file_name", "Entry ID"}:
                        continue

                    column, _ = Column.objects.get_or_create(name=col_name)
                    # Ensure the column belongs to the current review
                    if not review.columns.filter(pk=column.pk).exists():
                        review.columns.add(column)

                    # Save or update the Value (simple strategy: overwrite if it already exists)
                    val_obj = (
                        Value.objects
                        .filter(entry_id=entry_id, column=column)
                        .order_by("-id")
                        .first()
                    )
                    if val_obj is None:
                        val_obj = Value(entry_id=entry_id, column=column, creator=creator)

                    safe_answer = (answer or "").strip()
                    if len(safe_answer) > 1000:
                        safe_answer = safe_answer[:1000]  # Model field limit

                    val_obj.value = safe_answer

                    locs = locations_by_q.get(col_name) or []
                    rects_all = []

                    for loc in locs:
                        occs = loc.get("occurrences") or []
                        for occ in occs:
                            page = occ.get("page")
                            if isinstance(page, int) and page >= 0:
                                page = page + 1
                            rects = occ.get("rects") or []
                            # Each rect is [x0, y0, x1, y1]
                            for r in rects:
                                rects_all.append({
                                    "page": page,
                                    "rect": r,
                                })

                    # Keep only pure coordinate arrays
                    val_obj.highlights = rects_all
                    val_obj.save()
                    logger.warning("[HIGHLIGHT SAVED] review=%s entry=%s col=%r highlights=%r", review.id, entry_id, col_name, val_obj.highlights)
        persist_answers()

        # 4) Normal return (compatible with old frontend + new structure)
        return JsonResponse({
            "ok": True,
            "columns": columns_obj,
            "urls": urls_obj,
            "llm_text": llm_text,
            "results": results_per_url,
            "qa": qa_only,
            "highlights": highlights_only,
        }, status=200)

    except Exception as e:
        logger.exception("generate_request_accept_view failed")
        return JsonResponse({"ok": False, "error": str(e)}, status=400)


@require_GET
def get_entry_highlights(request, review_id, entry_id):
    """Return all highlights of a specific entry under the given review, grouped by column name.
    Response example:
    {
      "ok": true,
      "entry_id": 123,
      "file_name": "foo.pdf",
      "by_column": {
        "Q1: Method?": [{"page":1,"rect":[x0,y0,x1,y1]}, ...],
        "Q2: Result?": [...]
      }
    }
    """
    review = get_object_or_404(Review, pk=review_id)
    entry  = get_object_or_404(Entry,  pk=entry_id)

    # Confirm that the entry belongs to the current review
    if not review.entries.filter(pk=entry.pk).exists():
        return JsonResponse({"ok": False, "error": "Entry not in this review"}, status=400)

    # Retrieve the column set of the current review
    col_ids = list(review.columns.values_list("id", flat=True))
    values  = Value.objects.filter(entry=entry, column_id__in=col_ids).select_related("column")

    # The corresponding file name in the row (if exists)
    file_name = Value.objects.filter(entry=entry, column__name="file_name").values_list("value", flat=True).first() or ""

    by_column = {}
    for v in values:
        col_name = v.column.name
        if v.highlights:
            # Return only if the column has highlights
            by_column[col_name] = v.highlights

    return JsonResponse({
        "ok": True,
        "entry_id": entry.id,
        "file_name": file_name,
        "by_column": by_column,
    })