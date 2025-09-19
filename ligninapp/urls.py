from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
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
    path('question/<int:question_id>/upload-paper/', views.upload_paper, name='upload-paper'),
    path('review/save-title/', views.save_review_title, name='save-review-title'),
    path('papers/delete/<int:paper_id>/', views.delete_uploaded_paper, name='delete_uploaded_paper'),
    path("papers/update/<int:paper_id>/", views.update_uploaded_paper, name="update_uploaded_paper"),
    path("papers/replace/<int:paper_id>/", views.replace_uploaded_paper, name="replace_uploaded_paper"),
    path('question/add/step2/<int:review_id>/', views.add_columns_papers, name='add-columns-papers'),
    path('accounts/register/', views.register, name='register'),

    path("question/<int:question_id>/generate-request-accept/", views.generate_request_accept_view, name="generate-request-accept"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
