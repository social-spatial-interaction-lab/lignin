from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('question/<int:question_id>/', views.question, name='question'),
    path('question/<int:question_id>/add/paper/<paper_id>/', views.add_paper)
]
