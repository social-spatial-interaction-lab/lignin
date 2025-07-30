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
    path('question/add/', views.create_review, name='review-create'),
    path('column/add/', views.create_column, name='column-create'),
    path('question/add/save_title/', views.save_review_title, name='save-title'),
    path('question/<int:question_id>/upload-paper/', views.upload_paper_modal, name='upload-paper'),
    path('review/save-title/', views.save_review_title, name='save-review-title'),
    path('question/<int:question_id>/upload-paper/', views.upload_paper_modal, name='upload-paper'),
    path('question/add/step2/<int:review_id>/', views.add_columns_papers, name='add-columns-papers')
]
