from django.shortcuts import render
from django.http import HttpResponse
from .models import Paper

def index(request):
    return HttpResponse("Hello, world. You're at the index.")


def question(request, question_id):
    print(question_id)
    return render(request, template_name="ligninapp/question.html", context={
        "question_id": question_id
    })
