from django.db import models
from django.conf import settings


class LigninUser(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.owner.username


class Paper(models.Model):
    ssPaperID = models.CharField(max_length=50)
    title = models.CharField(max_length=500)
    faln = models.CharField(max_length=100)
    references = models.TextField()
    citations = models.TextField()


class Column(models.Model):
    name = models.CharField(max_length=200)
    creator = models.ForeignKey(LigninUser, on_delete=models.CASCADE)


class Question(models.Model):
    question_text = models.CharField(max_length=200)
    columns = models.ManyToManyField(Column, blank=True)
    # TODO: figure out perms so this doesn't cascade.
    creator = models.ForeignKey(LigninUser, on_delete=models.CASCADE)
    papers = models.ManyToManyField(Paper, blank=True)


class Value(models.Model):
    column = models.ForeignKey(Column, on_delete=models.CASCADE)
    creator = models.ForeignKey(LigninUser, null=True, on_delete=models.SET_NULL)
    value = models.CharField(max_length=1000)

