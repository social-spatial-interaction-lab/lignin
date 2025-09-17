from django import forms
from .models import UploadedPaper, Review

class UploadedPaperForm(forms.ModelForm):
    class Meta:
        model = UploadedPaper
        fields = ['title', 'file']

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['question_text', 'default_permission']
