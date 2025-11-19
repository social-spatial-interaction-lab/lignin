# LLM_response.py
from __future__ import annotations

import requests
import json
import os
import re
from typing import Any, Dict, List, Iterable, Tuple, Optional, Union
from urllib.parse import urlparse
from django.conf import settings

try:
    from django.conf import settings
    BASE_DIR = getattr(settings, "BASE_DIR", os.getcwd())
except Exception:
    BASE_DIR = os.getcwd()

try:
    from fuzzysearch import find_near_matches
except Exception:
    find_near_matches = None

try:
    import fitz  # PyMuPDF
except ImportError as e:
    fitz = None


_ANSWER_OPEN = re.compile(r"\s*#{3}\s*ANSWER\s*#{3}\s*", re.IGNORECASE)
_ANSWER_CLOSE = re.compile(r"\s*#{3}\s*ENDANSWER\s*#{3}\s*", re.IGNORECASE)


EXCLUDE_COLUMNS = {
    "File name", "Entry ID", "Title", "Author", "Year", "Notes", "Paper(s)", "Delete",
}

def LLM_entrance(
    columns: Dict[str, Any] | List[str],
    urls: Dict[str, Any] | List[str],
    include_highlights: bool = True,     # NEW: Whether to include highlight or not
) -> List[Dict[str, Any]]:
    """
    New entry point: return results per URL
    - For each URL:
        1) Extract PDF text
        2) Construct prompt and call LLM
        3) Parse with parse_llm_output_sections to obtain (answers_by_question, evidence_by_question)
        4) [optional] Build highlight locating payload (anchors + rectangles)
    - Return a list, where each element is:
        {
          "qa": {
            "url": str,
            "answers_by_question": {question -> answer},
            "evidence_by_question": {question -> [evidence]}
          },
          "highlights": {
            "doc": {...},
            "anchors_by_question": {...},
            "locations_by_question": {...}
          } | None
        }
    """

    # 1) Normalize
    col_list = normalize_columns(columns)
    url_list = normalize_urls(urls)

    # filter column names (obtained from the frontend)
    filtered_cols = filter_columns(col_list, EXCLUDE_COLUMNS)

    results: List[Dict[str, Any]] = []

    # 2) Main loop
    for idx, url in enumerate(url_list, start=1):
        # 2.a Extract text from the PDF file
        print("Extracting text...")
        pdf_text = extract_text_from_pdf(url)

        print("Sending to LLM...")
        # 2.b Build the prompt and send it to LLM
        prompt = build_llm_prompt(pdf_text, filtered_cols)
        llm_raw = send_llm_request(prompt)

        print("Handling output...")
        # 2.c Handle the reply of LLM
        answers_by_q, evidence_by_q = parse_llm_output_sections(llm_raw)

        print("Building QA payload...")
        # 2.d Build QA payload
        qa_payload = {
            "url": url,
            "answers_by_question": answers_by_q,
            "evidence_by_question": evidence_by_q,
        }

        print("Working on highlights...")
        # 2.e [Optional] Build the highlight-location payload (decoupled from QA; failure does not affect QA).
        highlights_payload = None
        if include_highlights:
            try:
                # build_highlights_payload / url_to_fs_path / fuzzy_match_evidence / locate_text_in_pdf
                highlights_payload = build_highlights_payload(
                    url=url,
                    evidence_by_question=evidence_by_q,
                    full_text=pdf_text,            # The full text is already available, passing it in can skip one extraction.
                    url_to_fs_path_fn=url_to_fs_path,
                )
            except Exception:
                highlights_payload = None  # Fallback: does not block the main process.

        # 2.f Append per-URL result(Dual payload, convenient for the frontend to consume separately.)
        results.append({
            "qa": qa_payload,
            "highlights": highlights_payload,   # May be None (when include_highlights=False or an exception occurs).
        })

    # 3) return
    return results



# -------------------------
# Tool Functions
# -------------------------

def normalize_columns(columns: Dict[str, Any] | List[str]) -> List[str]:
    """
    Accepts:
      - {"columns": [...]} or directly [...]
    Returns:
      - Flattened list of column names (str), with whitespace and duplicates removed (original order preserved)
    """

    if isinstance(columns, dict):
        candidate = columns.get("columns", [])
    else:
        candidate = columns
    out, seen = [], set()
    for c in (candidate or []):
        s = str(c).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def normalize_urls(urls: Dict[str, Any] | List[str]) -> List[str]:
    """
    Accepts:
      - {"urls": [...]} or directly [...]
    Returns:
      - Flattened list of URLs (str), with whitespace and empty values removed
    """

    if isinstance(urls, dict):
        candidate = urls.get("urls", [])
    else:
        candidate = urls
    out = []
    for u in (candidate or []):
        s = str(u).strip()
        if s:
            out.append(s)
    return out


def filter_columns(all_columns: List[str], exclude: Iterable[str]) -> List[str]:
    """
    Filter out column names that should not be sent to the LLM.
    - If USE_DEFAULT_TEST_QUESTIONS = True, ignore input and directly return the default question list.
    - Otherwise, follow the original logic: remove columns in 'exclude' and return the remaining column names.

    Note: This is a test function, the switch can only be modified manually in the code.
    """


    # === Use default questions and ignore input（TEST ONLY） ===
    USE_DEFAULT_TEST_QUESTIONS = False

    # === Default questions） ===
    DEFAULT_QUESTIONS = [
        "What is the main contribution of the paper?",
        "What methods are used?",
        "What are the key findings?",
        "What limitations are discussed?",
    ]

    if USE_DEFAULT_TEST_QUESTIONS:
        return DEFAULT_QUESTIONS

    # === Original logic ===
    exclude_set = set(exclude or [])
    return [c for c in all_columns if c not in exclude_set]


def url_to_fs_path(url_or_path: str) -> str:
    """
    Map frontend URL/path to local file system path.
    Rules:
    - If http/https -> raise explicit error (network download not supported for now)
    - If starting with MEDIA_URL -> replace with MEDIA_ROOT
    - If starting with /uploaded_papers/ -> map to MEDIA_ROOT/uploaded_papers/...
      (or the actual directory where PDFs are stored in your project)
    - If absolute path and exists -> return directly
    - If relative path -> treat as relative to BASE_DIR or MEDIA_ROOT (depending on your project convention)
    """

    s = (url_or_path or "").strip()
    if not s:
        raise ValueError("Empty URL/path")

    # Reject network URLs (you could also implement download logic here)
    parsed = urlparse(s)
    if parsed.scheme in ("http", "https"):
        raise ValueError(f"HTTP/HTTPS URL not supported by local extractor: {s}")

    # Prioritize handling MEDIA_URL prefix
    media_url = getattr(settings, "MEDIA_URL", "/media/")
    media_root = getattr(settings, "MEDIA_ROOT", None)
    if media_url and s.startswith(media_url):
        if not media_root:
            raise RuntimeError("MEDIA_ROOT is not configured.")
        rel = s[len(media_url):]  # remove '/media/' prefix
        return os.path.normpath(os.path.join(media_root, rel))

    # Backward compatibility: /uploaded_papers/ -> MEDIA_ROOT/uploaded_papers/...
    if s.startswith("/uploaded_papers/"):
        if not media_root:
            raise RuntimeError("MEDIA_ROOT is not configured.")
        rel = s.lstrip("/")  # remove the leading slash
        return os.path.normpath(os.path.join(media_root, rel))

    # Absolute path: return directly (let exists check later)
    if os.path.isabs(s):
        return os.path.normpath(s)

    # Relative path: try MEDIA_ROOT first, then BASE_DIR
    base_dir = getattr(settings, "BASE_DIR", os.getcwd())
    candidates = []
    if media_root:
        candidates.append(os.path.join(media_root, s))
    candidates.append(os.path.join(base_dir, s))

    for c in candidates:
        c = os.path.normpath(c)
        if os.path.exists(c):
            return c

    # If none found, still return the first candidate so upper-level error can display it
    return os.path.normpath(candidates[0])

def extract_text_from_pdf(url: str, *, return_pages: bool = False) -> Union[str, Tuple[str, List[str]]]:
    """
    Args:
        url: PDF path/URL passed from frontend (will be mapped to local file system path first)
        return_pages: If True, return (full_text, text_by_page); otherwise return only full_text string
    Returns:
        - full_text: concatenated text of all pages separated by newlines
        - or (full_text, text_by_page)
    Raises:
        - FileNotFoundError: file does not exist
        - ImportError: PyMuPDF not installed
        - ValueError: PDF is protected, etc.
        - Other underlying exceptions
    """
    if fitz is None:
        raise ImportError("PyMuPDF is not installed. Please `pip install pymupdf`")

    path = url_to_fs_path(url)  # reuse our previous path mapping function
    if not os.path.exists(path):
        raise FileNotFoundError(f"PDF not found: {path}")

    doc = None
    text_by_page: List[str] = []
    try:
        doc = fitz.open(path)
        # If the document is password-protected
        if getattr(doc, "needs_pass", False):
            raise ValueError(f"Encrypted PDF requires password: {path}")

        for page in doc:  # extract page by page
            try:
                # get_text() defaults to 'text' mode, sufficient for most cases;
                # if layout is needed, consider 'blocks' or 'html'
                txt = page.get_text()
            except Exception:
                txt = ""
            text_by_page.append(txt or "")

    finally:
        if doc is not None:
            doc.close()

    # Merge into full text
    full_text = "\n".join(text_by_page)

    return (full_text, text_by_page) if return_pages else full_text

def build_llm_prompt(pdf_text: str, columns: list[str]) -> str:
    """
    Construct a prompt based on the extracted PDF text and filtered column names (= question list).
    - columns: each element is a "question" string
    - Returns: the complete prompt text for LLM usage
    """
    # 1) Normalize the question list
    questions = [str(q).strip() for q in (columns or []) if str(q).strip()]
    # A human-readable list for clarity
    question_list_str = "\n".join(f"- {q}" for q in questions) if questions else "- (no questions)"
    # Also provide a JSON version to reduce model misinterpretation
    questions_json_str = json.dumps(questions, ensure_ascii=False, indent=2)

    # 2) Control the length of paper text to avoid overly long prompts (adjust as needed)
    TEXT_MAX_CHARS = 100000000
    text = pdf_text or ""
    truncated = False
    if len(text) > TEXT_MAX_CHARS:
        text = text[:TEXT_MAX_CHARS]
        truncated = True

    # 3) Generate the prompt
    prompt = f"""
You are an assistant that reads academic PDFs and answers table-structured questions.

Given the following research paper text, answer the listed questions in **valid JSON** format. 
Return **ONLY** the JSON object, with no extra commentary, markdown, or backticks.

Paper Text{" (TRUNCATED)" if truncated else ""}:
{text}

Questions (list):
{question_list_str}

Questions (JSON array):
{questions_json_str}

Answer Format (return exactly this structure):
{{
  "responses": [
    {{
      "question": "<the question text exactly as given>",
      "answer": "###ANSWER### ... ###ENDANSWER###",
      "evidence": ["Exact quote from paper", "..."],
      "confidence": 0.0
    }}
  ]
}}

Rules:
- Include one and only one response object for each input question, preserving the original question text in the "question" field.
- "answer" must be concise and factual. Always wrap it with ###ANSWER### and ###ENDANSWER###.
- "evidence" must be exact verbatim quotes from the Paper Text (exact substring matches), up to 3 items.
- "confidence" is a float between 0.0 and 1.0.
- If the Paper Text does not contain sufficient information to answer a question, use:
  - "answer": "NOTFOUND"
  - "evidence": NOTFOUND
  - "confidence": 0.0
- Output must be strictly valid JSON; do not include any explanations or formatting outside the JSON object.
""".strip()

    return prompt


def send_llm_request(
    prompt: str,
    *,
    model: str = "mistralai/Mistral-7B-Instruct-v0.3",
    token: Optional[str] = None,
    temperature: float = 0.2,
    timeout: int = 300,
) -> str:
    """
    Send the prompt to the DeepInfra OpenAI-compatible Chat Completions API 
    and return the raw text content from the LLM.
    - Do not perform json.loads here; keep the "raw string" for later parsing.
    - The token is read from the environment variable DEEPINFRA_API_TOKEN by default, 
      or can be specified via the parameter.
    """
    api_token = token or os.getenv("DEEPINFRA_API_TOKEN")
    if not api_token:
        raise RuntimeError(
            "Missing API token. Set env DEEPINFRA_API_TOKEN or pass `token=` explicitly."
        )

    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    headers = {
        "Authorization": f"bearer {api_token}",
        "Content-Type": "application/json",
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        # Add max_tokens if needed, e.g.:
        # "max_tokens": 1200,
        # JSON strictness: DeepInfra's support for response_format may vary by model, use with caution
        # "response_format": {"type": "json_object"},
    }
    print("Composed data, sending request...")

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        # Include the first few hundred characters of the server response for debugging
        body_preview = getattr(e.response, "text", "")[:600] if hasattr(e, "response") and e.response is not None else ""
        raise RuntimeError(f"LLM API request failed: {e}\n{body_preview}") from e
    print("Received requirest, handling structure")
    payload = resp.json()
    # Handle empty/abnormal structures
    choices = payload.get("choices") or []
    if not choices or "message" not in choices[0] or "content" not in choices[0]["message"]:
        raise RuntimeError(f"Unexpected LLM response structure: {json.dumps(payload)[:600]}")

    content = choices[0]["message"]["content"] or ""
    if not content.strip():
        raise RuntimeError("Empty content from LLM.")

    # Return only the text, parsing/cleaning is handled later by parse_llm_output_sections
    print("Returning content")
    return content


def _strip_answer_markers(text: str) -> str:
    """
    Remove ###ANSWER### and ###ENDANSWER### (case/whitespace-insensitive match), and apply strip().
    If only one marker appears, remove only the one that exists.
    """
    if not isinstance(text, str):
        return ""
    s = _ANSWER_OPEN.sub("", text)
    s = _ANSWER_CLOSE.sub("", s)
    return s.strip()

def _extract_json_object_str(s: str) -> str:
    """
    Attempt to extract the outermost JSON object substring from a string.
    First, try json.loads directly; if it fails, attempt to slice from the first '{' 
    to the last '}' and parse again. If it still fails, raise an error.
    """
    # Try directly
    try:
        json.loads(s)
        return s
    except Exception:
        pass

    #  Try slicing a window
    first = s.find("{")
    last = s.rfind("}")
    if first != -1 and last != -1 and last > first:
        candidate = s[first : last + 1]
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            # Try shrinking again: move the right boundary backwards
            for pos in range(last, first, -1):
                try:
                    cand2 = s[first : pos]
                    json.loads(cand2)
                    return cand2
                except Exception:
                    continue

    raise ValueError("Failed to locate a valid top-level JSON object in LLM text.")

def parse_llm_output_sections(llm_text: str) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """
    Args:
        llm_text: raw string returned by the LLM (expected to be a JSON object containing 'responses': [...])
    Returns:
        (answers_by_question, evidence_by_question)
        - answers_by_question: {question(str) -> answer(str, with ###ANSWER### and ###ENDANSWER### removed)}
        - evidence_by_question: {question(str) -> List[str]}

    Raises:
        - ValueError: if valid JSON cannot be parsed / required structure is missing
    """
    if not isinstance(llm_text, str) or not llm_text.strip():
        raise ValueError("Empty LLM text.")

    # 1) Attempt to extract a clean JSON substring and load it
    json_str = _extract_json_object_str(llm_text)
    try:
        payload = json.loads(json_str)
    except Exception as e:
        raise ValueError(f"Invalid JSON from LLM: {e}")

    # 2) Validate basic structure
    if not isinstance(payload, dict) or "responses" not in payload:
        raise ValueError("JSON must be an object containing a 'responses' array.")
    responses = payload.get("responses")
    if not isinstance(responses, list):
        raise ValueError("'responses' must be a list.")

    answers_by_question: Dict[str, str] = {}
    evidence_by_question: Dict[str, List[str]] = {}

    # 3) Extract each response
    for i, item in enumerate(responses):
        if not isinstance(item, dict):
            # Skip non-dict items but continue
            continue

        q = item.get("question")
        ans = item.get("answer")
        ev = item.get("evidence")

        # question must be a non-empty string
        if not isinstance(q, str) or not q.strip():
            # Skip invalid items
            continue
        q_norm = q.strip()

        # answer -> remove markers
        if isinstance(ans, str):
            clean_ans = _strip_answer_markers(ans)
        else:
            # Fallback: if not string, cast to string then clean
            clean_ans = _strip_answer_markers("" if ans is None else str(ans))

        # evidence -> normalize to list of strings
        ev_list: List[str] = []
        if isinstance(ev, list):
            for e in ev:
                if isinstance(e, str) and e.strip():
                    ev_list.append(e.strip())
                elif e is not None:
                    # Fallback: convert non-string to string
                    ev_list.append(str(e).strip())
        elif isinstance(ev, str) and ev.strip():
            # Fallback: some models may return a single string
            ev_list = [ev.strip()]
        else:
            ev_list = []

        # Overwrite policy: if question repeats, the latter overwrites the former (can be changed to merge if needed)
        answers_by_question[q_norm] = clean_ans
        evidence_by_question[q_norm] = ev_list

    return answers_by_question, evidence_by_question


def handle_sections(sections: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> None:
    # This part doesn't have an actual function right now.
    print("[handle_sections] context:", context or {})
    print("[handle_sections] sections:", json.dumps(sections, ensure_ascii=False)[:300])


# =========================================================
# Highlight Locating Helpers (self-contained & JSON-safe)
# =========================================================

def _safe_rect_to_list(rect: "fitz.Rect") -> List[float]:
    """Convert PyMuPDF Rect to plain list[float] for JSON serialization."""
    return [float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)]

def fuzzy_match_evidence(evidence: str, full_text: str,
                         max_edit_distances: Tuple[int, ...] = (0, 7, 50)) -> Optional[str]:
    """
    Try to find a near-exact substring of `evidence` inside `full_text`.
    Returns the *matched substring* (best-effort) or None.
    - Step up tolerance: 0 -> 7 -> 50 (configurable).
    - If fuzzysearch is unavailable, fall back to exact substring search.
    """
    if not evidence or not full_text or evidence == "NOTFOUND":
        return None

    # Exact match first (fast path)
    if evidence in full_text:
        return evidence

    # Fuzzy match if library is available
    if find_near_matches is not None:
        for d in max_edit_distances:
            print(f"Trying find_near_matches for evidence={evidence[:30]}, d={d}, full_text={full_text[:30]}")
            try:
                matches = find_near_matches(evidence, full_text, max_l_dist=d, max_deletions=d,
                                            max_insertions=d, max_substitutions=d)
            except Exception:
                matches = []
            if matches:
                # take the first match (keep behavior deterministic)
                return matches[0].matched

    # Last resort: None (no match)
    return None


def locate_text_in_pdf(fs_path: str, target_text: str) -> List[Dict[str, Any]]:
    """
    Locate `target_text` in the PDF at fs_path, returning a list of occurrences:
    [
      { "page": int, "rects": [[x0,y0,x1,y1], ...], "page_size": [w, h] },
      ...
    ]
    - Coordinates are in PDF page user space (points, origin at bottom-left).
    - `rects` are the minimal bounding boxes for text quads on that page.
    """
    if not fs_path or not target_text or fitz is None:
        return []

    occurrences: List[Dict[str, Any]] = []
    try:
        doc = fitz.open(fs_path)
    except Exception:
        return []

    try:
        text_flags = 0
        # Prefer preserving whitespace/ligatures when available
        if hasattr(fitz, "TEXT_PRESERVE_WHITESPACE"):
            text_flags |= fitz.TEXT_PRESERVE_WHITESPACE
        if hasattr(fitz, "TEXT_PRESERVE_LIGATURES"):
            text_flags |= fitz.TEXT_PRESERVE_LIGATURES
        if hasattr(fitz, "TEXT_MEDIABOX_CLIP"):
            text_flags |= fitz.TEXT_MEDIABOX_CLIP

        for page_number in range(len(doc)):
            page = doc[page_number]

            try:
                # Ask for quads to better follow text shape across wraps
                quads = page.search_for(target_text, quads=True, flags=text_flags)
            except Exception:
                quads = []

            if not quads:
                continue

            # Get page width/height in user space
            w, h = float(page.rect.width), float(page.rect.height)

            # If page has a transformation matrix, normalize rects back to page user space
            ptm = getattr(page, "transformation_matrix", None)

            rects: List[List[float]] = []
            for q in quads:
                rect = q.rect
                # Some PyMuPDF versions expose Matrix; invert (~) to map back if present
                if ptm is not None:
                    try:
                        rect = rect * (~ptm)
                    except Exception:
                        pass
                rects.append(_safe_rect_to_list(rect))

            occurrences.append({
                "page": int(page_number),
                "rects": rects,
                "page_size": [w, h],
            })

    finally:
        try:
            doc.close()
        except Exception:
            pass

    return occurrences


def build_highlights_payload(url: str,
                             evidence_by_question: Dict[str, List[str]],
                             full_text: Optional[str],
                             url_to_fs_path_fn) -> Dict[str, Any]:
    """
    Build the 'highlights' half of the dual payload.
    Inputs:
      - url: the PDF url (as you already return to front-end)
      - evidence_by_question: {question: [evidence, ...]}
      - full_text: whole-text of the PDF (if already computed in the QA path; else pass None)
      - url_to_fs_path_fn: function that maps url -> local fs path (reuse your existing helper)
    Output (JSON-serializable):
    {
      "doc": { "url": str, "doc_id": str (optional), "page_count": int (optional) },
      "anchors_by_question": { q: [ { "evidence_index": i, "matched_text": str|null }, ... ] },
      "locations_by_question": {
         q: [ { "evidence_index": i, "occurrences": [ {page, rects, page_size}, ... ] }, ... ]
      }
    }
    """
    highlights = {
        "doc": {
            "url": url,
            # add doc_id / page_count as needed; for now, only minimal fields are kept.
        },
        "anchors_by_question": {},
        "locations_by_question": {},
    }

    if not evidence_by_question:
        return highlights

    # Get the full PDF text (if not provided).
    if full_text is None:
        # You already have an implementation of extract_text_from_pdf(url); if it cannot be retrieved here, set it to empty.
        try:
            full_text = extract_text_from_pdf(url)  # noqa: F821  (refer to your existing function)
        except Exception:
            full_text = ""

    # File system path (for PyMuPDF to open).
    fs_path = None
    try:
        fs_path = url_to_fs_path_fn(url)
    except Exception:
        pass

    for q, ev_list in (evidence_by_question or {}).items():
        anchors_row: List[Dict[str, Any]] = []
        locs_row: List[Dict[str, Any]] = []

        # Keep the order of evidences aligned.
        for idx, ev in enumerate(ev_list or []):
            matched = fuzzy_match_evidence(ev, full_text or "")
            anchors_row.append({
                "evidence_index": idx,
                "matched_text": matched,
            })

            occurrences = []
            if matched and fs_path:
                occurrences = locate_text_in_pdf(fs_path, matched)  # May be an empty array.

            locs_row.append({
                "evidence_index": idx,
                "occurrences": occurrences,
            })

        highlights["anchors_by_question"][q] = anchors_row
        highlights["locations_by_question"][q] = locs_row

    return highlights


# -------------------------
# TEST ONLY
# -------------------------
if __name__ == "__main__":
    demo_columns = {"columns": ["File name", "Q1: Contribution", "Q2: Methods", "Notes"]}
    demo_urls = {"urls": ["/uploaded_papers/a.pdf", "/uploaded_papers/b.pdf"]}
    print(LLM_entrance(demo_columns, demo_urls))
