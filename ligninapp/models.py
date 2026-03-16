import rules
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as gtl
from rules.contrib.models import RulesModel


@rules.predicate
def view_review(user, review):
    if review is None:
        return True
    if not user.is_authenticated:
        return review.default_permission in ['VIEW', 'PROP', 'MOD', 'ADMIN']
    try:
        q_perm = ReviewPermission.objects.get(user=user.lignin_user, review=review)
        return q_perm.permission in ['VIEW', 'PROP', 'MOD', 'ADMIN']
        # otherwise, go to the default.
    except ReviewPermission.DoesNotExist:
        return review.default_permission in ['VIEW', 'PROP', 'MOD', 'ADMIN']


class LigninUser(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lignin_user')

    def __str__(self):
        return self.owner.username


class PermissionEnum(models.TextChoices):
    NONE = 'NONE', gtl('None') # do nothing (for defaults)
    VIEW = 'VIEW', gtl('View') # see stuff
    PROPOSE = 'PROP', gtl('Propose') # suggest stuff
    MODERATE = 'MOD', gtl('Moderate') # approve, edit directly
    ADMIN = 'ADMIN', gtl('Administrate') # edit permissions, etc. (don't think too hard yet)


class ReviewPermission(models.Model):
    user = models.ForeignKey(LigninUser, on_delete=models.CASCADE)
    review = models.ForeignKey("Review", on_delete=models.CASCADE)
    permission = models.CharField(choices=PermissionEnum.choices, max_length=5)

class Paper(RulesModel):
    ssPaperID = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=500)
    faln = models.CharField(max_length=100)
    references = models.TextField()
    citations = models.TextField()
    year = models.IntegerField()
    url = models.URLField()
    default_subpaper = models.ForeignKey("Entry", null=True, on_delete=models.SET_NULL, related_name="default_of")

    def __str__(self):
        return f"{self.faln} ({self.year}) {self.title[:20]}..."


class Entry(RulesModel):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, null=True, blank=True)
    uploaded_paper = models.ForeignKey("UploadedPaper", on_delete=models.SET_NULL, null=True, blank=True, related_name="entries")
    description = models.TextField(blank=True)
    def __str__(self):
        if self.description:
            return f"{self.paper}, {self.description}"
        else:
            return f"{self.paper}"


class Column(RulesModel):
    name = models.CharField(max_length=200)
    default_permission = models.CharField(
        choices=PermissionEnum.choices, max_length=5, default="MOD"
    )
    column_info = models.TextField(blank=True, null=False)

    # NEW: human-readable description of the question/column
    description = models.TextField(blank=True, null=True)  # allow-null for smooth migration

    def __str__(self):
        return self.name

    def get_absolute_url(self):  # new
        return reverse('', args=[str(self.id)])



rules.add_perm('ligninapp.add_column', rules.is_authenticated)
rules.add_perm('ligninapp.view_column', rules.is_authenticated)
#rules.add_perm('ligninapp.change_column', view_review


class Review(RulesModel):
    question_text = models.CharField(max_length=200, help_text="The title of the review")
    columns = models.ManyToManyField(Column, blank=True)
    entries = models.ManyToManyField(Entry, blank=True)
    rejected_papers = models.TextField(blank=True)
    default_permission = models.CharField(choices=PermissionEnum.choices, max_length=5, help_text="This currently does not matter")

    def __str__(self):
        return f'{self.question_text}'

    def get_absolute_url(self):  # new
        return reverse('question', args=[str(self.id)])


rules.add_perm('ligninapp', rules.always_allow)
rules.add_perm('ligninapp.add_review', rules.is_authenticated)
rules.add_perm('ligninapp.view_review', view_review)
rules.add_perm('ligninapp.change_review', view_review)


class Value(RulesModel):
    column = models.ForeignKey(Column, on_delete=models.CASCADE)
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE)
    creator = models.ForeignKey(LigninUser, null=True, on_delete=models.SET_NULL)
    value = models.CharField(max_length=1000)
    notes = models.TextField(blank=True)
    highlights = models.JSONField(blank=True, null=True)
    edited = models.BooleanField(default=False, help_text="If True, block LLM updates for this cell; user edits still allowed.")
    
    def __str__(self):
        return f"{self.column} for {self.entry}: {self.value}"
    
class UploadedPaper(RulesModel):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="uploaded_papers")
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True)
    year = models.IntegerField(null=True, blank=True)
    file = models.FileField(upload_to='uploaded_papers/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    # Optional metadata
    doi = models.CharField(max_length=100, blank=True, null=True)
    citation_text = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "year": self.year,
            "file_url": self.file.url if self.file else "",
            "uploaded_at": self.uploaded_at.strftime("%Y-%m-%d %H:%M"),
            "notes": self.notes or ""
        }

# --- 以下为 Control Group Experiment 新增模型 ---

class ControlGroupTab(models.Model):
    """
    代表一个独立的对话选项卡 (Chat Session)。
    移除了 user 字段，所有访问页面的用户共享这些选项卡。
    """
    # 选项卡名称 (例如 tab1, tab2)，允许同名
    name = models.CharField(max_length=100)
    
    # 需求：每个选项卡只允许上传一个文件。
    attached_file = models.FileField(upload_to='control_group_files/', null=True, blank=True)
    original_file_name = models.CharField(max_length=255, null=True, blank=True) # 用于前端显示原始文件名
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ControlGroupMessage(models.Model):
    """
    代表选项卡内的单条对话消息。
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('llm', 'LLM'),
    ]
    
    # 关联到对应的选项卡 (Django 会自动使用 tab.id 作为外键)
    tab = models.ForeignKey(ControlGroupTab, on_delete=models.CASCADE, related_name='messages')
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    text = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at'] # 确保对话总是按时间先后顺序排列

    def __str__(self):
        return f"[{self.role}] {self.text[:30]}..."