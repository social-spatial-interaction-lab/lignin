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
    path('review/<int:review_id>/columns/<int:column_id>/remove/', views.remove_column_from_review, name='remove-column-from-review'),
    path('review/<int:review_id>/entries/<int:entry_id>/remove/', views.remove_entry_from_review, name='remove-entry-from-review'),
    path('review/<int:review_id>/entries/<int:entry_id>/highlights/', views.get_entry_highlights, name='get-entry-highlights'),

    path("review/<int:review_id>/entries/<int:entry_id>/qa/",views.entry_qa_view, name="entry_qa",),
    path('review/<int:review_id>/columns/<int:column_id>/edit/', views.edit_column_in_review, name='column-edit'),
    #control group experiment
    path('control-group/', views.control_group_view, name='control_group'),
    path('api/control-group/tabs/', views.get_cg_tabs, name='cg_get_tabs'),
    path('api/control-group/tabs/create/', views.create_cg_tab, name='cg_create_tab'),
    path('api/control-group/tabs/<int:tab_id>/rename/', views.rename_cg_tab, name='cg_rename_tab'),
    path('api/control-group/tabs/<int:tab_id>/delete/', views.delete_cg_tab, name='cg_delete_tab'),
    path('api/control-group/tabs/message/', views.send_cg_message, name='cg_send_message'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
