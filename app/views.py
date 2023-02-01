from django.shortcuts import render
from django.http import HttpResponse


def index(request):
    return HttpResponse("Hello, world. You're at the index.")


def question(request, question_id):
    return HttpResponse("Question id" + str(question_id))
