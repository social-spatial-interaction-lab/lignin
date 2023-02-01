from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('question/<int:question_id>/', views.get_question, name='question'),
    path('question/<int:question_id>/papers/add/<paper_id>/', views.add_paper),
    path('question/<int:question_id>/papers/', views.get_papers)
]
