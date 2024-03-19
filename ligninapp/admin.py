import rules
from django.contrib import admin
from .models import Column, LigninUser, Paper, Question, Subpaper, Value

from rules.contrib.admin import ObjectPermissionsModelAdmin
from rules import has_perm


class QuestionAdmin(ObjectPermissionsModelAdmin):
    def get_queryset(self, request):
        queryset = super(QuestionAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return queryset
        else:
            pks = [i.pk for i in queryset.all() if has_perm('ligninapp.view_question', request.user, i)]
            return Question.objects.filter(id__in=pks)


admin.site.register(Column)
admin.site.register(LigninUser)
admin.site.register(Paper)
admin.site.register(Subpaper)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Value)
