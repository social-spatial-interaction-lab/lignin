import json
import logging

from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.core import serializers
from rules.contrib.views import PermissionRequiredMixin
from .models import Paper, Review, Value, Column, LigninUser, Entry
from collections import defaultdict
import requests
from rules import has_perm
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .forms import UploadedPaperForm, ReviewForm
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET
from django.urls import reverse
from django.shortcuts import redirect
from .models import UploadedPaper
from django.views.decorators.http import require_http_methods
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Prefetch
from django.contrib import messages
from django.db import transaction
import os
from urllib.parse import unquote
from django.views.decorators.csrf import csrf_exempt

from .LLM_response import LLM_entrance

from django.conf import settings  # log
from datetime import datetime     # log

# 对照组模型和代码
from .models import ControlGroupTab, ControlGroupMessage
from .LLM_control_group import process_control_group_llm

import environ
env = environ.Env()
environ.Env.read_env()

logger = logging.getLogger(__name__)

LOG_INITIALIZED = False  # reset to False on each server start
LOG_FILE_PATH = None
CG_LOG_FILE_PATH = None

def _init_log_if_needed():
    """
    Initialize the log directory and log file once per server start.
    This function is only called from get_papers() on its first execution.
    It will:
      - create log/ directory under project root (where manage.py lives),
      - create a file named LogYYYYMMDD_HHMMSS.log,
      - write the first line: [New_Experiment] Null
      - set LOG_INITIALIZED = True
    """
    global LOG_INITIALIZED, LOG_FILE_PATH
    if LOG_INITIALIZED:
        return

    # Try to use settings.BASE_DIR as the project root (the directory that contains manage.py).
    base_dir = getattr(settings, "BASE_DIR", None)
    if base_dir is None:
        # Fallback: go up a few levels from this file, if BASE_DIR is not configured as expected.
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    log_dir = os.path.join(base_dir, "log")
    os.makedirs(log_dir, exist_ok=True)

    now = datetime.now()
    filename = f"Log{now.strftime('%Y%m%d_%H%M%S')}.log"
    LOG_FILE_PATH = os.path.join(log_dir, filename)

    # First line: New_Review Null
    line = f"{now.strftime('%Y-%m-%d %H:%M:%S')} [New_Experiment] Null\n"
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        # Do not break the request flow if logging fails
        LOG_FILE_PATH = None

    LOG_INITIALIZED = LOG_FILE_PATH is not None


def _append_log(operation: str, content):
    """
    Append a single log line in the format:
        <timestamp> [<Operation>] <Content>

    If content is None or empty, write 'Null'.
    If the log system has not been initialized yet (LOG_INITIALIZED is False),
    this function will silently do nothing.
    """
    global LOG_INITIALIZED, LOG_FILE_PATH

    if not LOG_INITIALIZED or not LOG_FILE_PATH:
        # Requirement: log file is created only by get_papers() on first call.
        # If get_papers() has not yet run, we skip logging.
        return

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if content is None or str(content).strip() == "":
        content_str = "Null"
    else:
        content_str = str(content)

    line = f"{ts} [{operation}] {content_str}\n"
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        # Avoid raising errors from logging
        pass

def index(request):
    pks = [i.pk for i in Review.objects.all() if has_perm('ligninapp.view_review', request.user, i)]
    visible_questions = Review.objects.filter(id__in=pks)

    return render(request, template_name="ligninapp/index.html", context={
        "visible_questions": visible_questions
    })

def control_group_view(request):
    #this is for experiment use only.
    return render(request, 'ligninapp/control_group.html') 

def get_question(request, question_id):
    question = get_object_or_404(Review, id=question_id)
    return render(request, template_name="ligninapp/question.html", context={
        "question": question,
        "question_id": question_id
    })

def _get_value_by_ids(entry_id: int, column_pk: int, create_if_missing: bool = False):
    entry = get_object_or_404(Entry, pk=entry_id)
    column = get_object_or_404(Column, pk=column_pk)
    try:
        val = Value.objects.get(entry=entry, column=column)
    except Value.DoesNotExist:
        if not create_if_missing:
            return entry, column, None
        val = Value.objects.create(entry=entry, column=column, creator=None, value="", notes="", highlights=None)
    return entry, column, val


class ReviewCreate(PermissionRequiredMixin, CreateView):
    model = Review
    fields = ['question_text', 'default_permission']
    permission_required = 'ligninapp.add_review'

    def get_initial(self):
        initial = super().get_initial()
        if 'title' in self.request.GET:
            initial['question_text'] = self.request.GET['title']
        return initial



class NewColumnForm(forms.Form):
    name = forms.CharField(
        label="Column name (a summary for this question)",
        max_length=200
    )
    description = forms.CharField(
        label="Description (the question it self)",
        widget=forms.Textarea(attrs={"rows": 4}),
        required=True
    )
    review_to_add_to = forms.ModelChoiceField(
        queryset=Review.objects.all(),
        widget=forms.HiddenInput()
    )


# views.py

def create_column(request):
    """
    Updated: Returns JsonResponse on POST for AJAX modal support.
    """
    if request.method == "POST":
        form = NewColumnForm(request.POST)
        if form.is_valid():
            # Create the Column
            column = Column.objects.create(
                name=form.cleaned_data["name"],
                description=form.cleaned_data.get("description", ""),
            )

            # Attach to Review
            review = form.cleaned_data["review_to_add_to"]
            if review:
                review.columns.add(column)

            # Log
            desc = column.description if column.description else "Null"
            _append_log("New_Question", f"{column.name} | {desc}")

            # === 修改点：返回 JSON 而不是重定向 ===
            return JsonResponse({"ok": True, "msg": "Column created successfully"})
        else:
            # 如果表单验证失败，返回错误信息
            return JsonResponse({"ok": False, "error": form.errors.as_json()}, status=400)
    else:
        # GET 请求保持不变（如果有人直接访问 URL，依然渲染旧模板，或者你可以选择删除这部分）
        review_id = request.GET.get("review")
        form = NewColumnForm(initial={"review_to_add_to": review_id})
        return render(request, "ligninapp/column_form.html", {"form": form})


def add_paper(request, question_id, paper_id):
    # check if the paper exists.
    paper_match_set = Paper.objects.filter(ssPaperID=paper_id)
    if paper_match_set:
        paper_match = paper_match_set[0]
    else:
        # make API call to Semantic Scholar.
        paper_details = requests.get(
            f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
            f"?fields=title,year,authors,citations.paperId,references.paperId",
            headers={"x-api-key": "PDPwFWmKA72Rlsuqd2xmF3YVZhB75BUd3ylD4a61"}
        ).json()

        print(paper_details)
        # When references are elided, the reference list can be None rather than an empty list. :(
        if paper_details['references'] is None:
            paper_details['references'] = []

        new_paper = Paper.objects.create(
            ssPaperID=paper_details['paperId'],
            title=paper_details['title'],
            year=int(paper_details['year']),
            faln=paper_details['authors'][0]['name'] + (" et al." if len(paper_details['authors']) > 1 else ""),
            references=" ".join([x["paperId"] for x in paper_details['references'] if x["paperId"]]),
            citations=" ".join([x["paperId"] for x in paper_details['citations'] if x["paperId"]]),
            url=f"https://www.semanticscholar.org/paper/{paper_details['paperId']}"
        )
        new_paper.save()
        paper_match = new_paper

    subpaper = paper_match.default_subpaper
    if subpaper is None:
        subpaper = Entry.objects.create(paper=paper_match, description="")
        subpaper.save()
        paper_match.default_subpaper = subpaper
        paper_match.save()

    Review.objects.get(id=question_id).entries.add(subpaper)

    return HttpResponse(status=201)

def get_papers(request, question_id):

    # log: initialize log system on first call
    _init_log_if_needed()

    review = get_object_or_404(Review, id=question_id)

    # Include 'description' in the query
    columns_qs = review.columns.all().only("id", "name", "description")
    # Convert to a list of dictionaries immediately for easier JSON serialization
    columns_meta = list(columns_qs.values("id", "name", "description"))
    col_id_to_name = {c['id']: c['name'] for c in columns_meta}
    col_ids = [c['id'] for c in columns_meta]
    col_names = [c['name'] for c in columns_meta]

    entries_qs = (
        review.entries
        .prefetch_related(
            Prefetch(
                "value_set",
                # Prefetch the 'edited' field as well to avoid N+1 queries later
                queryset=Value.objects.filter(column_id__in=col_ids).only("column_id", "value"),
            )
        )
        .only("id")
    )

    rows = []
    #edited_map = {}  # NEW: { "<entry_id>": { "<column_name>": true, ... }, ... }

    for entry in entries_qs:
        row = {"entry_id": entry.id}
        for name in col_names:
            row[name] = ""

        for val in entry.value_set.all():
            c_name = col_id_to_name.get(val.column_id)
            if c_name:
                row[c_name] = val.value
        rows.append(row)

    payload = {
        "columns": col_names,  # Compatible with the old frontend
        # === MODIFICATION START ===
        # Use the list of dictionaries we prepared earlier
        "columns_meta": columns_meta, 
        # === MODIFICATION END ===
        "rows": rows,

    }
    return JsonResponse(payload, safe=False)




@require_POST
def edit_annotation(request, entry_id, column_pk):
    """
    User edits a cell from the frontend.
    Updated: Removed 'lock_after_save' and 'edited' logic.
    """
    # --- DEBUG START ---
    try:
        raw_body = request.body.decode("utf-8")
    except Exception as e:
        raw_body = f"<decode error: {e}>"
    logger.info(f"[edit_annotation] raw_body={raw_body} entry_id={entry_id} column_pk={column_pk}")
    # --- DEBUG END ---
    
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON."}, status=400)

    new_value = payload.get("value", "")
    new_notes = payload.get("notes", None)

    # lock_after_save = payload.get("lock_after_save", True)

    entry, column, val = _get_value_by_ids(entry_id, column_pk, create_if_missing=True)
    
    val.value = new_value
    if new_notes is not None:
        val.notes = new_notes

    # if lock_after_save:
    #     val.edited = True

    logger.info(f"[edit_annotation] entry={entry_id} col={column_pk} value updated")

    update_fields = ["value"]
    if new_notes is not None:
        update_fields.append("notes")
    
    val.save(update_fields=update_fields)

    # log: log edit operation (Edit_Answer)
    file_name = (
        Value.objects
        .filter(entry_id=entry.id, column__name="file_name")
        .values_list("value", flat=True)
        .first()
    )
    if not file_name:
        file_name = "Null"
    col_name = column.name if column and column.name else "Null"
    _append_log("Edit_Answer", f"{file_name} | {col_name}")

    return JsonResponse({
        "ok": True,
        "entry_id": entry.id,
        "column_pk": column.pk,
        "value": val.value,
        "notes": val.notes,
    })

def reject_paper(request, question_id, paper_id):
    question = get_object_or_404(Review, id=question_id)

    # if it's already there, ignore the request.
    if paper_id in question.rejected_papers:
        return HttpResponse(204)

    # Otherwise, add the paper (with perhaps a space)
    if question.rejected_papers:
        question.rejected_papers += " " + paper_id
    else:
        question.rejected_papers = paper_id
    question.save()
    return HttpResponse(201)


def get_snowball(request, question_id):
    question = get_object_or_404(Review, id=question_id)
    #included_papers = question.papers.all()


    # foo_queryset = Foo.objects.filter(attr=value)
    # referenced_bars = foo_queryset.bar_set.all()
    included_papers = Paper.objects.filter(ssPaperID__in=question.entries.values('paper__ssPaperID'))

    rejected_paper_ids = question.rejected_papers.split(" ") if question.rejected_papers else []
    ignored_paper_ids = [x.ssPaperID for x in included_papers] + rejected_paper_ids
    id_strings = [x.references.split(" ") + x.citations.split(" ") for x in included_papers]
    snowball_set_size = len(id_strings)

    d = defaultdict(int)
    for paper_links in id_strings:
        for paper_id in paper_links:
            d[paper_id] += 1

    most_refs = sorted(d.items(), key=lambda item: item[1], reverse=True)
    most_refs_filtered = [x for x in most_refs if x[0] not in ignored_paper_ids]
    #print(most_refs)
    #print(most_refs_filtered)

    r = requests.post(
        "https://api.semanticscholar.org/graph/v1/paper/batch?fields=title,year,authors,url",
        json={"ids": [x[0] for x in most_refs_filtered[:10]]}
    )

    response = r.json()
    print(response)

    for paper in response:
        if paper:
            paper["occurrence_number"] = d[paper['paperId']]
            paper["occurrence"] = f"{d[paper['paperId']]}/{snowball_set_size}"

    return JsonResponse({"data": sorted([i for i in response if i], key=lambda x: x["occurrence_number"], reverse=True)})

def create_review(request):
    title = request.GET.get("title", "").strip()
    if title:
        review = Review.objects.create(question_text=title, default_permission='MOD')
    return redirect("question", question_id=review.id)
    return redirect("index")  # fallback if title is empty

@require_POST

def save_review_title(request):
    title = request.POST.get("title", "").strip()
    if not title:
        return JsonResponse({"error": "Missing title"}, status=400)

    review = Review.objects.create(
        question_text=title,
        default_permission="VIEW",
    )

    return JsonResponse({"redirect_url": reverse("add-columns-papers", args=[review.id])})

def add_columns_papers(request, review_id):
    review = get_object_or_404(Review, pk=review_id)
    return render(request, "ligninapp/add_columns_papers.html", {"review": review})
#10.20 Create Entry and Uploadedpaper.So it can upload the pdf file.
@transaction.atomic
def upload_paper(request, question_id):
    review = get_object_or_404(Review, id=question_id)

    if request.method != "POST":
        return redirect("question", question_id)

    # 1. 修改点：使用 getlist 获取所有文件
    files = request.FILES.getlist("file")
    
    # 如果列表为空，尝试回退到 get (兼容旧版单文件上传，虽非必须但更稳健)
    if not files:
        f = request.FILES.get("file")
        if f:
            files = [f]

    if not files:
        messages.error(request, "No file received.")
        return redirect("question", question_id)

    # 2. 修改点：遍历文件列表，为每个文件执行创建逻辑
    count = 0
    for f in files:
        # A) 保存文件实体
        paper = UploadedPaper.objects.create(
            review=review,
            title=os.path.splitext(os.path.basename(f.name))[0],
            file=f,
        )

        # B) 创建 Entry 并关联
        entry = Entry.objects.create(description="", uploaded_paper=paper)
        review.entries.add(entry)

        # C) 写入 file_name 列
        file_name_col, _ = Column.objects.get_or_create(name="file_name")
        review.columns.add(file_name_col)
        Value.objects.create(entry=entry, column=file_name_col, value=os.path.basename(paper.file.name))

        # D) 记录日志
        _append_log("New_Paper", os.path.basename(paper.file.name))
        count += 1

    messages.success(request, f"Uploaded {count} file(s).")
    return redirect("question", question_id)

@require_http_methods(["DELETE"])
def delete_uploaded_paper(request, paper_id):
    try:
        paper = UploadedPaper.objects.get(pk=paper_id)
        paper.delete()
        return JsonResponse({'success': True})
    except UploadedPaper.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Paper not found'}, status=404)

#10.20 delete-column
@require_http_methods(["POST"])
@transaction.atomic
def remove_column_from_review(request, review_id, column_id):
    review = get_object_or_404(Review, pk=review_id)
    column = get_object_or_404(Column, pk=column_id)

    # Only allow the operation if the column belongs to the current review
    if not review.columns.filter(pk=column.pk).exists():
        return JsonResponse({"ok": False, "error": "Column not in this review"}, status=400)

    # log: prepare log content before modifying the DB
    col_name = column.name if column.name else "Null"
    col_desc = column.description if column.description else "Null"

    # 1) Delete all Values in this column under the current review’s entries
    entry_ids = list(review.entries.values_list("id", flat=True))
    Value.objects.filter(column=column, entry_id__in=entry_ids).delete()

    # 2) Remove this column from the review's column set
    review.columns.remove(column)

    # 3) Optional cleanup: if this column is no longer used by any review and has no remaining Value, physically delete it
    if not column.review_set.exists() and not Value.objects.filter(column=column).exists():
        column.delete()

    # log: log column deletion (Delete_Question)
    _append_log("Delete_Question", f"{col_name} | {col_desc}")

    return JsonResponse({"ok": True})

#2.3 edit-column
@require_http_methods(["POST"])
@transaction.atomic
def edit_column_in_review(request, review_id, column_id):
    review = get_object_or_404(Review, pk=review_id)
    column = get_object_or_404(Column, pk=column_id)

    # 1. Verify column belongs to this review
    if not review.columns.filter(pk=column.pk).exists():
        return JsonResponse({"ok": False, "error": "Column not in this review"}, status=400)

    # 2. Get data from form (Multipart/form-data from frontend)
    new_name = request.POST.get("name", "").strip()
    new_desc = request.POST.get("description", "").strip()

    if not new_name:
        return JsonResponse({"ok": False, "error": "Column name cannot be empty"}, status=400)

    old_desc = (column.description or "").strip()
    old_name = column.name
    
    # 3. Update the column
    column.name = new_name
    column.description = new_desc
    column.save()

    # 4. Check if description changed
    if old_desc != new_desc:
        entry_ids = review.entries.values_list("id", flat=True)
        deleted_count, _ = Value.objects.filter(
            column=column, 
            entry_id__in=entry_ids
        ).delete()
        
        _append_log("Edit_Column_Reset", f"{new_name} | {new_desc} | Description changed. Cleared {deleted_count} cells.")
    else:
        _append_log("Edit_Column", f"{old_name} | {new_name} | Name updated only.")

    return JsonResponse({"ok": True})

#10.20 delete-row
@require_http_methods(["POST"])
@transaction.atomic
def remove_entry_from_review(request, review_id, entry_id):
    review = get_object_or_404(Review, pk=review_id)
    entry = get_object_or_404(Entry, pk=entry_id)

    # Check whether the entry belongs to the current review
    if not review.entries.filter(pk=entry.pk).exists():
        return JsonResponse({"ok": False, "error": "This entry does not belong to this review."}, status=400)

    # log: get file name for logging before removing
    file_name = (
        Value.objects
        .filter(entry=entry, column__name="file_name")
        .values_list("value", flat=True)
        .first()
    )
    if not file_name:
        file_name = "Null"

    # 1. Unlink it from the current review
    review.entries.remove(entry)

    # 2. If the entry no longer belongs to any review, safely delete it
    if not entry.review_set.exists():
        Value.objects.filter(entry=entry).delete()
        entry.delete()

    # log: log deletion (Delete_Paper)
    _append_log("Delete_Paper", file_name)

    return JsonResponse({"ok": True})

@require_http_methods(["POST"])
def update_uploaded_paper(request, paper_id):
    try:
        paper = UploadedPaper.objects.get(pk=paper_id)
        data = json.loads(request.body)

        paper.title = data.get("title", paper.title)
        paper.author = data.get("author", paper.author)
        paper.year = data.get("year", paper.year)
        paper.save()

        return JsonResponse({'success': True})
    except UploadedPaper.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Paper not found'}, status=404)

@require_http_methods(["POST"])
def replace_uploaded_paper(request, paper_id):
    try:
        paper = UploadedPaper.objects.get(pk=paper_id)
        new_file = request.FILES.get("file")
        if not new_file:
            return JsonResponse({"success": False, "error": "No file uploaded"})

        paper.file = new_file
        paper.save()

        return JsonResponse({"success": True})
    except UploadedPaper.DoesNotExist:
        return JsonResponse({"success": False, "error": "Paper not found"}, status=404)
    
def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # from django.contrib.auth.urls
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@require_POST
def generate_request_accept_view(request, question_id):
    try:
        # log: log when LLM answer generation starts
        _append_log("Generate_Answer", None)
        
        # 1. 解析请求体
        payload = json.loads(request.body.decode("utf-8"))
        columns_obj = payload.get("columns", {}) or {}
        urls_obj    = payload.get("urls", {})    or {} # 格式通常是 {"urls": ["http://..."]}

        review = get_object_or_404(Review, id=question_id)
        
        # --- 步骤 A: 提取并解析列名 (保持原有逻辑) ---
        incoming_names = []
        raw_list = columns_obj.get("columns", []) or []
        for n in raw_list:
            s = (n or "").strip()
            if not s: continue
            if s in {"file_name", "File name", "Entry ID"}: continue
            incoming_names.append(s)

        # 批量查找 Column 对象
        found_cols = {c.name: c for c in Column.objects.filter(name__in=incoming_names).only("name", "description", "column_info")}

        # --- 步骤 B: [新功能] 针对单行请求进行过滤 ---
        # 只有当请求中正好包含 1 个 URL 时，我们才启用这个“智能跳过”功能。
        # 如果将来恢复批量请求，此逻辑会自动失效（或者需要改为取并集，这里暂不处理）。
        url_list = urls_obj.get("urls", [])
        
        filtered_names = [] # 最终要发给 LLM 的列名列表
        
        if len(url_list) == 1:
            target_url = url_list[0]
            
            # 1. 从 URL 解析文件名 (逻辑同 persist_answers)
            base = os.path.basename(target_url)
            filename = unquote(base).strip()
            
            # 2. 找到对应的 Entry
            # 需要先获取或创建 file_name 列对象来辅助查找
            file_name_col = Column.objects.filter(name="file_name").first()
            
            entry = None
            if file_name_col and filename:
                # 查找当前 Review 下，匹配 file_name 的 Entry
                # 注意：这里我们只读，不创建。如果 Entry 不存在，说明都没上传过，自然全是空的，不用过滤。
                entry_id = Value.objects.filter(
                    column=file_name_col, 
                    value=filename, 
                    entry__review=review
                ).values_list("entry_id", flat=True).first()
                
                if entry_id:
                    entry = Entry.objects.get(pk=entry_id)

            # 3. 检查每一列是否为空
            if entry:
                # 预先获取该 Entry 下所有相关列的 Value，避免 N+1 查询
                # 获取我们关心的列的 ID 列表
                relevant_col_ids = [c.id for c in found_cols.values()]
                existing_values = {
                    v.column_id: v.value 
                    for v in Value.objects.filter(entry=entry, column_id__in=relevant_col_ids)
                }

                for name in incoming_names:
                    col = found_cols.get(name)
                    should_generate = True
                    
                    if col:
                        val_str = existing_values.get(col.id)
                        # 核心判断：如果值存在且剔除空格后不为空，则跳过
                        if val_str is not None and val_str.strip() != "":
                            should_generate = False
                    
                    if should_generate:
                        filtered_names.append(name)
            else:
                # 如果找不到 Entry（理论上不应该发生），则无法判断，默认全生成
                filtered_names = incoming_names
        else:
            # 如果 URL 列表为空或大于 1，为了安全起见，不执行过滤，保留原有行为
            filtered_names = incoming_names


        # --- 步骤 C: 如果过滤后没有剩余列，直接返回成功 ---
        if not filtered_names:
            _append_log("Answer_Obtained", "Skipped (All Filled)")
            return JsonResponse({
                "ok": True,
                "llm_text": [], # 前端会认为没有数据更新，这很安全
                "msg": "All requested columns are already filled."
            })

        # --- 步骤 D: 构建发给 LLM 的 Column Description 列表 ---
        # 注意：这里我们只为 filtered_names 构建描述
        desc_list = []
        for name in filtered_names:
            col = found_cols.get(name)
            if col is not None:
                desc = (col.description or col.column_info or name) or ""
            else:
                desc = name
            desc_list.append(desc.strip())

        columns_for_llm = {"columns": desc_list}
        
        # --- 步骤 E: 调用 LLM (传入过滤后的列) ---
        # 注意：LLM 此时只会收到“真正为空”的那些问题的描述
        results_per_url = LLM_entrance(columns_for_llm, urls_obj, include_highlights=True)

        # --- 步骤 F: 后续处理 (数据整形) ---
        qa_only, highlights_only = [], []
        
        # 辅助函数：将描述映射回列名 (需要在循环外准备好)
        # 因为我们过滤了列，所以这里的 desc_to_name 只需要包含我们发出去的那些列
        temp_desc_map = {} # desc -> col_name
        for name in filtered_names:
            col = found_cols.get(name)
            if col:
                d = (col.description or col.column_info or name).strip()
                if d: temp_desc_map[d] = name
            else:
                temp_desc_map[name] = name

        def _desc_to_name(desc: str) -> str | None:
            key = (desc or "").strip()
            if not key: return None
            # 优先查本次请求的映射
            if key in temp_desc_map: return temp_desc_map[key]
            # 兜底查数据库 (应对 LLM 幻觉或极端情况)
            c = Column.objects.filter(description=key).only("name").first()
            return c.name if c else None

        for item in (results_per_url or []):
            qa_payload = (item or {}).get("qa", {}) or {}
            hl_payload = (item or {}).get("highlights", None)

            abq = qa_payload.get("answers_by_question") or {}
            mapped = {}
            for k_desc, v in abq.items():
                k_name = _desc_to_name(k_desc)
                if k_name:
                    mapped[k_name] = v

            qa_only.append({
                **qa_payload,
                "answers_by_question": mapped,
            })
            highlights_only.append(hl_payload)

        llm_text = qa_only

        # --- 步骤 G: 保存结果 (persist_answers) ---
        # 这部分逻辑保持原样即可，因为它会根据 LLM 返回的结果 update 数据库。
        # 由于我们只请求了空列，LLM 也只返回了空列的答案，所以这里只会 update 那些空列。
        # 已有值的列不会被触碰。
        
        # ... (以下为原有的 persist_answers 相关准备工作) ...
        file_name_col, _ = Column.objects.get_or_create(name="file_name")
        if not review.columns.filter(pk=file_name_col.pk).exists():
            review.columns.add(file_name_col)
        review_entry_ids = set(review.entries.values_list("id", flat=True))
        try:
            creator = getattr(request.user, "lignin_user", None)
        except Exception:
            creator = None

        @transaction.atomic
        def persist_answers():
            # 这里的逻辑不需要大改，直接复用原有逻辑即可
            # 只需要确保 desc_to_col 能正确工作
            desc_to_col = {}
            for c in review.columns.only("id", "name", "description", "column_info"):
                key = (c.description or c.column_info or c.name or "").strip()
                if key: desc_to_col[key] = c

            def resolve_column_by_desc(desc_key: str) -> Column:
                key = (desc_key or "").strip()
                if not key: return None
                col = desc_to_col.get(key)
                if col: return col
                col = Column.objects.filter(description=key).first()
                if not col:
                    col = Column.objects.create(name=key, description=key)
                if not review.columns.filter(pk=col.pk).exists():
                    review.columns.add(col)
                desc_to_col[key] = col
                return col

            for item in (results_per_url or []):
                qa = (item or {}).get("qa", {}) or {}
                hl = (item or {}).get("highlights", {}) or {}
                url = (qa.get("url") or "").strip()
                if not url: continue

                base = os.path.basename(url)
                filename = unquote(base).strip()
                if not filename: continue

                entry_qs = (
                    Value.objects
                    .filter(column=file_name_col, value=filename, entry_id__in=review_entry_ids)
                    .values_list("entry_id", flat=True)
                )
                entry_id = next(iter(entry_qs), None)
                if not entry_id: continue

                answers_by_q = qa.get("answers_by_question") or {}
                
                anchors_by_q   = hl.get("anchors_by_question")   or {}
                locations_by_q = hl.get("locations_by_question") or {}
                
                for desc_key, answer in answers_by_q.items():
                    desc_key = (desc_key or "").strip()
                    if not desc_key: continue
                    if desc_key in {"File name", "file_name", "Entry ID"}: continue

                    column = resolve_column_by_desc(desc_key)
                    if column is None: continue

                    val_obj = (
                        Value.objects
                        .filter(entry_id=entry_id, column=column)
                        .order_by("-id")
                        .first()
                    )

                    if val_obj is None:
                        val_obj = Value(entry_id=entry_id, column=column, creator=creator)

                    safe_answer = (answer or "").strip()
                    if len(safe_answer) > 1000:
                        safe_answer = safe_answer[:1000]

                    val_obj.value = safe_answer

                    # Highlights logic
                    locs = locations_by_q.get(desc_key) or []
                    rects_all = []
                    for loc in locs:
                        occs = loc.get("occurrences") or []
                        for occ in occs:
                            page = occ.get("page")
                            if isinstance(page, int) and page >= 0:
                                page = page + 1
                            rects = occ.get("rects") or []
                            for r in rects:
                                rects_all.append({"page": page, "rect": r})

                    val_obj.highlights = rects_all
                    val_obj.save()
                    # logger.warning(...) 

        persist_answers()
        llm_response_str = json.dumps(llm_text, ensure_ascii=False)
        _append_log("Answer_Obtained", llm_response_str)
        
        return JsonResponse({
            "ok": True,
            "columns": columns_obj, # 返回前端原始请求的列结构，保持兼容
            "urls": urls_obj,
            "llm_text": llm_text,   # 只包含本次生成的答案
            "results": results_per_url,
            "qa": qa_only,
            "highlights": highlights_only,
        }, status=200)

    except Exception as e:
        logger.exception("generate_request_accept_view failed")
        return JsonResponse({"ok": False, "error": str(e)}, status=400)

@require_GET
def get_entry_highlights(request, review_id, entry_id):
    """Return all highlights of a specific entry under the given review, grouped by column name.
    Response example:
    {
      "ok": true,
      "entry_id": 123,
      "file_name": "foo.pdf",
      "by_column": {
        "Q1: Method?": [{"page":1,"rect":[x0,y0,x1,y1]}, ...],
        "Q2: Result?": [...]
      }
    }
    """
    review = get_object_or_404(Review, pk=review_id)
    entry  = get_object_or_404(Entry,  pk=entry_id)

    # Confirm that the entry belongs to the current review
    if not review.entries.filter(pk=entry.pk).exists():
        return JsonResponse({"ok": False, "error": "Entry not in this review"}, status=400)

    # Retrieve the column set of the current review
    col_ids = list(review.columns.values_list("id", flat=True))
    values  = Value.objects.filter(entry=entry, column_id__in=col_ids).select_related("column")

    # The corresponding file name in the row (if exists)
    file_name = Value.objects.filter(entry=entry, column__name="file_name").values_list("value", flat=True).first() or ""

    by_column = {}
    for v in values:
        col_name = v.column.name
        if v.highlights:
            # Return only if the column has highlights
            by_column[col_name] = v.highlights

    return JsonResponse({
        "ok": True,
        "entry_id": entry.id,
        "file_name": file_name,
        "by_column": by_column,
    })

@require_GET
def entry_qa_view(request, review_id, entry_id):
    """Return QA data (Column + Value) for a specific entry under the given review.

    Response example:
    {
      "ok": true,
      "review_id": 1,
      "entry_id": 42,
      "data": [
        {
          "column_id": 10,
          "name": "Q1: Method?",
          "description": "Please summarize the methods used in this paper.",
          "value": "Randomized controlled trial..."
        },
        ...
      ]
    }
    """
    # Basic object lookups
    review = get_object_or_404(Review, pk=review_id)
    entry = get_object_or_404(Entry, pk=entry_id)

    # Confirm that the entry belongs to the given review
    if not review.entries.filter(pk=entry.pk).exists():
        return JsonResponse({"ok": False, "error": "Entry not in this review"}, status=400)

    # Optional: permission check, consistent with index() which uses has_perm
    if not has_perm("ligninapp.view_review", request.user, review):
        return JsonResponse({"ok": False, "error": "Permission denied"}, status=403)

    # Retrieve all Columns of this review (including those without a Value yet)
    columns_qs = review.columns.all().only("id", "name", "description")
    columns = list(columns_qs)

    # If the review has no columns yet, just return an empty list
    if not columns:
        return JsonResponse(
            {
                "ok": True,
                "review_id": review.id,
                "entry_id": entry.id,
                "data": [],
            }
        )

    col_ids = [c.id for c in columns]

    # Retrieve all Value objects for this entry under the review's columns
    values_qs = Value.objects.filter(entry=entry, column_id__in=col_ids).only("column_id", "value")

    # Build a mapping: column_id -> value string (last one wins if duplicates exist)
    value_by_col_id = {}
    for v in values_qs:
        value_by_col_id[v.column_id] = v.value

    # Some internal/reserved columns should not be shown in the QA panel
    reserved_names = {"file_name", "File name", "Entry ID"}

    data = []
    for col in columns:
        if col.name in reserved_names:
            # Skip internal columns that are not real QA questions
            continue

        data.append(
            {
                "column_id": col.id,
                "name": col.name,
                "description": col.description or "",
                "value": value_by_col_id.get(col.id, ""),
            }
        )

    return JsonResponse(
        {
            "ok": True,
            "review_id": review.id,
            "entry_id": entry.id,
            "data": data,
        }
    )


# ==========================================
# Control Group Experiment APIs
# ==========================================

def control_group_view(request):
    # 【新增】：进入页面时，强制初始化新的日志文件
    _init_cg_log()
    return render(request, 'ligninapp/control_group.html') 


@require_GET
def get_cg_tabs(request):
    """初始化加载：获取所有的 Tabs"""
    tabs = ControlGroupTab.objects.all().order_by('created_at')
    data = []
    
    for tab in tabs:
        messages = tab.messages.all().order_by('created_at')
        msg_list = [{'role': m.role, 'text': m.text} for m in messages]
        
        file_info = None
        if tab.attached_file:
            file_info = {
                'name': tab.original_file_name or tab.attached_file.name.split('/')[-1],
                'url': tab.attached_file.url
            }
            
        data.append({
            'id': tab.id,
            'name': tab.name,
            'messages': msg_list,
            'file': file_info
        })
        
    return JsonResponse({'ok': True, 'tabs': data})


@csrf_exempt
@require_POST
def create_cg_tab(request):
    """新建一个 Tab"""
    try:
        payload = json.loads(request.body)
        name = payload.get('name', 'New Tab')
    except json.JSONDecodeError:
        name = 'New Tab'
        
    tab = ControlGroupTab.objects.create(name=name)
    
    # 【新增】：记录创建 Tab 日志
    _append_cg_log("Create_Tab", f"Tab ID: {tab.id} | Name: {tab.name}")
    
    return JsonResponse({'ok': True, 'id': tab.id, 'name': tab.name})


@csrf_exempt
@require_POST
def rename_cg_tab(request, tab_id):
    """重命名指定的 Tab"""
    tab = get_object_or_404(ControlGroupTab, id=tab_id)
    try:
        payload = json.loads(request.body)
        new_name = payload.get('name', '').strip()
        if new_name:
            old_name = tab.name
            tab.name = new_name
            tab.save()
            
            # 【新增】：记录重命名 Tab 日志
            _append_cg_log("Rename_Tab", f"Tab ID: {tab_id} | Old: {old_name} -> New: {new_name}")
            
            return JsonResponse({'ok': True})
        return JsonResponse({'ok': False, 'error': 'Name cannot be empty'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["DELETE", "POST"])
def delete_cg_tab(request, tab_id):
    """删除指定的 Tab"""
    tab = get_object_or_404(ControlGroupTab, id=tab_id)
    tab_name = tab.name
    tab.delete()
    
    # 【新增】：记录删除 Tab 日志
    _append_cg_log("Delete_Tab", f"Tab ID: {tab_id} | Name: {tab_name}")
    
    return JsonResponse({'ok': True})


@csrf_exempt
@require_POST
def send_cg_message(request):
    """接收用户消息和文件，并调用 LLM 生成回复"""
    tab_id = request.POST.get('tab_id')
    user_text = request.POST.get('message', '').strip()
    uploaded_file = request.FILES.get('file')

    if not tab_id:
        return JsonResponse({'ok': False, 'error': 'tab_id is required'}, status=400)

    tab = get_object_or_404(ControlGroupTab, id=tab_id)

    # 1. 如果有新文件上传，覆盖旧文件
    if uploaded_file:
        tab.attached_file = uploaded_file
        tab.original_file_name = uploaded_file.name
        tab.save()

    # 2. 保存用户的消息
    if user_text:
        ControlGroupMessage.objects.create(tab=tab, role='user', text=user_text)
    elif uploaded_file:
        ControlGroupMessage.objects.create(tab=tab, role='user', text=f"[Uploaded file: {uploaded_file.name}]")

    if not user_text and not uploaded_file:
        return JsonResponse({'ok': False, 'error': 'Empty message'}, status=400)

    # 【新增】：合并记录用户的操作（含文本和上传的文件）
    file_name_log = uploaded_file.name if uploaded_file else "No File"
    text_log = user_text if user_text else "No Text"
    _append_cg_log("User_Input", f"Tab ID: {tab_id} | Text: [{text_log}] | File: [{file_name_log}]")

    # 3. 抽象调用 LLM
    try:
        llm_response_text = process_control_group_llm(tab.id)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Control group LLM error for tab {tab.id}")
        llm_response_text = f"Sorry, an error occurred while processing your request: {str(e)}"

    # 4. 保存 LLM 的回复
    llm_message = ControlGroupMessage.objects.create(tab=tab, role='llm', text=llm_response_text)

    # 【新增】：记录 LLM 的回复
    _append_cg_log("LLM_Reply", f"Tab ID: {tab_id} | Response: [{llm_response_text}]")

    return JsonResponse({'ok': True, 'reply': llm_message.text})
    """
    接收用户消息和文件，并调用 LLM 生成回复
    注意：这里前端使用的是 FormData，所以数据在 request.POST 和 request.FILES 中
    """
    tab_id = request.POST.get('tab_id')
    user_text = request.POST.get('message', '').strip()
    uploaded_file = request.FILES.get('file')

    if not tab_id:
        return JsonResponse({'ok': False, 'error': 'tab_id is required'}, status=400)

    tab = get_object_or_404(ControlGroupTab, id=tab_id)

    # 1. 如果有新文件上传，覆盖旧文件
    if uploaded_file:
        tab.attached_file = uploaded_file
        tab.original_file_name = uploaded_file.name
        tab.save()

    # 2. 如果用户发送了文本，保存用户的消息
    if user_text:
        ControlGroupMessage.objects.create(
            tab=tab,
            role='user',
            text=user_text
        )
    elif uploaded_file:
        # 如果只传了文件没发文字，我们自动补上一条提示，方便 LLM 知道发生了什么
        ControlGroupMessage.objects.create(
            tab=tab,
            role='user',
            text=f"[Uploaded file: {uploaded_file.name}]"
        )

    # 如果既没文字也没文件，直接驳回
    if not user_text and not uploaded_file:
        return JsonResponse({'ok': False, 'error': 'Empty message'}, status=400)

    # 3. 核心抽象调用：将构建上下文和请求 LLM 的脏活累活丢给 LLM_control_group.py
    try:
        llm_response_text = process_control_group_llm(tab.id)
    except Exception as e:
        # 记录异常并给前端返回友好的错误提示
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Control group LLM error for tab {tab.id}")
        llm_response_text = f"Sorry, an error occurred while processing your request: {str(e)}"

    # 4. 保存 LLM 的回复
    llm_message = ControlGroupMessage.objects.create(
        tab=tab,
        role='llm',
        text=llm_response_text
    )

    return JsonResponse({
        'ok': True,
        'reply': llm_message.text
    })

def _init_cg_log():
    """
    每次进入 control_group_view 页面时调用，创建新的日志文件。
    命名规则：Con_LogYYYYMMDD_HHMMSS.log
    """
    global CG_LOG_FILE_PATH
    base_dir = getattr(settings, "BASE_DIR", None)
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    log_dir = os.path.join(base_dir, "log")
    os.makedirs(log_dir, exist_ok=True)

    now = datetime.now()
    filename = f"Con_Log{now.strftime('%Y%m%d_%H%M%S')}.log"
    CG_LOG_FILE_PATH = os.path.join(log_dir, filename)

    # 写入第一条进入页面的日志
    _append_cg_log("Enter_Page", "User entered Control Group Experiment page")

def _append_cg_log(operation: str, content):
    """
    追加日志记录到当前的 CG 日志文件中。带时间戳。
    """
    global CG_LOG_FILE_PATH
    if not CG_LOG_FILE_PATH:
        # 如果由于某种原因没有初始化（比如服务器重启后直接调了API），直接返回，避免报错
        return

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if content is None or str(content).strip() == "":
        content_str = "Null"
    else:
        # 去掉换行符，保证单条日志在一行内，方便后续数据分析
        content_str = str(content).replace('\n', ' \\n ')

    line = f"{ts} [{operation}] {content_str}\n"
    try:
        with open(CG_LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        logger.error(f"Failed to write CG log: {e}")