from django.contrib import admin

# Register your models here.
from .models import Column, LigninUser, Paper, Question, Value

admin.site.register(Column)
admin.site.register(LigninUser)
admin.site.register(Paper)
admin.site.register(Question)
admin.site.register(Value)