import json

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.core import serializers
from .models import Paper, Question
from collections import defaultdict
import requests


def index(request):
    return HttpResponse("Hello, world. You're at the index.")


def get_question(request, question_id):
    print(question_id)
    return render(request, template_name="ligninapp/question.html", context={
        "question_id": question_id
    })


def add_paper(request, question_id, paper_id):
    # check if the paper exists.
    paper_match_set = Paper.objects.filter(ssPaperID=paper_id)
    if paper_match_set:
        paper_match = paper_match_set[0]
    else:
        # make API call to Semantic Scholar.
        paper_details = requests.get(
            f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
            f"?fields=title,year,authors,citations.paperId,references.paperId"
        ).json()

        new_paper = Paper.objects.create(
            ssPaperID=paper_details['paperId'],
            title=paper_details['title'],
            year=int(paper_details['year']),
            faln=paper_details['authors'][0]['name'] + (" et al." if len(paper_details['authors']) > 1 else ""),
            references=" ".join([x["paperId"] for x in paper_details['references'] if x["paperId"]]),
            citations=" ".join([x["paperId"] for x in paper_details['citations'] if x["paperId"]])
        )
        new_paper.save()
        paper_match = new_paper

    Question.objects.get(id=question_id).papers.add(paper_match)

    return HttpResponse(status=201)


def get_papers(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    serialized = serializers.serialize('json', question.papers.all(), fields=('ssPaperID', 'title', 'year', 'faln'))
    return JsonResponse({"data": [x["fields"] for x in json.loads(serialized)]})


def get_snowball(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    included_papers = question.papers.all()
    included_paper_ids = [x.ssPaperID for x in included_papers]
    id_strings = [x.references.split(" ") + x.citations.split(" ") for x in included_papers]
    snowball_set_size = len(id_strings)

    d = defaultdict(int)
    for paper_links in id_strings:
        for paper_id in paper_links:
            d[paper_id] += 1

    most_refs = sorted(d.items(), key=lambda item: item[1], reverse=True)
    most_refs_filtered = [x for x in most_refs if x[0] not in included_paper_ids]
    print(most_refs)
    print(most_refs_filtered)

    r = requests.post(
        "https://api.semanticscholar.org/graph/v1/paper/batch?fields=title,year,authors,url",
        json={"ids": [x[0] for x in most_refs_filtered[:10]]}
    )

    response = r.json()
    for paper in response:
        paper["occurrence_number"] = d[paper['paperId']]
        paper["occurrence"] = f"{d[paper['paperId']]}/{snowball_set_size}"

    return JsonResponse({"data": sorted(response, key=lambda x: x["occurrence_number"], reverse=True)})

