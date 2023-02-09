from django.db import models
from django.conf import settings


class LigninUser(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.owner.username


class Paper(models.Model):
    ssPaperID = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=500)
    faln = models.CharField(max_length=100)
    references = models.TextField()
    citations = models.TextField()
    year = models.IntegerField()
    url = models.URLField(blank=True)

    def __str__(self):
        return f"{self.faln} ({self.year}) {self.title[:20]}..."


class Column(models.Model):
    name = models.CharField(max_length=200)
    creator = models.ForeignKey(LigninUser, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Question(models.Model):
    question_text = models.CharField(max_length=200)
    columns = models.ManyToManyField(Column, blank=True)
    # TODO: figure out perms so this doesn't cascade.
    creator = models.ForeignKey(LigninUser, on_delete=models.CASCADE)
    papers = models.ManyToManyField(Paper, blank=True)
    rejected_papers = models.TextField(blank=True)

    def __str__(self):
        return f'"{self.question_text}" by {self.creator}'


class Value(models.Model):
    column = models.ForeignKey(Column, on_delete=models.CASCADE)
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE)
    creator = models.ForeignKey(LigninUser, null=True, on_delete=models.SET_NULL)
    value = models.CharField(max_length=1000)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.column} for {self.paper}: {self.value}"
