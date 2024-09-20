import rules
from django.contrib import admin
from .models import Column, LigninUser, Paper, Review, Entry, Value

from rules.contrib.admin import ObjectPermissionsModelAdmin
from rules import has_perm


class ReviewAdmin(ObjectPermissionsModelAdmin):
    def get_queryset(self, request):
        queryset = super(ReviewAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return queryset
        else:
            pks = [i.pk for i in queryset.all() if has_perm('ligninapp.view_review', request.user, i)]
            return Review.objects.filter(id__in=pks)


admin.site.register(Column)
admin.site.register(LigninUser)
admin.site.register(Paper)
admin.site.register(Entry)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Value)
