from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('question/<int:question_id>/', views.get_question, name='question'),
    path('question/<int:question_id>/papers/', views.get_papers),
    path('question/<int:question_id>/papers/add/<paper_id>/', views.add_paper),
    path('question/<int:question_id>/papers/reject/<paper_id>/', views.reject_paper),
    path('question/<int:question_id>/snowball/', views.get_snowball),
    path('values/<entry_id>/<int:column_pk>/', views.edit_annotation),
    path('question/add/', views.ReviewCreate.as_view(), name='review-create'),
    path('column/add/', views.create_column, name='column-create')
]
