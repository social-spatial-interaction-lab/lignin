import fitz  # PyMuPDF
import json
import requests
import pickle
from fuzzysearch import find_near_matches

# Shared Utilities
# =========================

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text_by_page = [page.get_text() for page in doc]
    full_text = "\n".join(text_by_page)
    return full_text, text_by_page

def query_llm(prompt, model="mistralai/Mistral-7B-Instruct-v0.3", token="API TOKEN HERE"):
    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    headers = {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)

def fuzzy_match_evidence(evidence, full_text):
    for dist in [0, 7, 50]:
        near_matches = find_near_matches(evidence, full_text, max_l_dist=dist)
        if near_matches:
            break
    print(f"{len(near_matches)} NEAR MATCH(ES)")
    if not near_matches:
        return None
    return near_matches[0].matched

def locate_text_in_pdf(pdf_path, target_text):
    doc = fitz.open(pdf_path)
    locations = []

    for page_number in range(len(doc)):
        page = doc[page_number]
        ptm = page.transformation_matrix
        text_instances = page.search_for(
            target_text,
            quads=True,
            flags=fitz.TEXT_PRESERVE_WHITESPACE
                  | fitz.TEXT_PRESERVE_LIGATURES
                  | fitz.TEXT_MEDIABOX_CLIP
        )
        if text_instances:
            locations.append({
                "page": page_number,
                "rectangles": [quad.rect * ~ptm for quad in text_instances]
            })

    return locations

# Original Proof of Concept
# =========================

def build_prompt(text, question):
    prompt = f"""
Given the following research paper, please answer the following questions in JSON format:

Text:
{text}

Answer Format: 
{{
  "responses": [
    {{
       "question_id": "...",
       "answer": "...",
       "evidence": ["...", "..."],
       "confidence": 0.5
    }},
    ... # Other questions have the same dictionary structure within the 'responses' array.
  ]
}}

- "question_id" should match one of the question_ids from the questions given below
- "answer" should be an answer to the question in a word, phrase, or sentence.
- "evidence" should provide relevant parts of text that formed this answer. The evidence text should match the text of the paper exactly. There should be one entry in the "evidence" array for every continuous passage of the text used - if a sentence or phrase is cut out in between, then there needs to be two separate entries in the list.
- "confidence" should be the confidence score of the answer as a float, where 0.0 is low confidence, 1.0 is high confidence.

Questions:
- How many participants are in the study? (question_id = "participant_count")
- What information was given about the age of the participants in the study? (question_id = "participant_ages")
- What devices were used to track the motion in the study? (question_id = "tracking_device")
- What frame rate was this motion tracked at? (question_id = "frame_rate")
- What feature(s) of the individual or environment was being inferred from this motion? (question_id = "inferred_variable")

"""
    return prompt

def analyze_pdf_question(pdf_path, question, api_token):
    print("Step 1: Extracting text from PDF...")
    full_text, text_by_page = extract_text_from_pdf(pdf_path)
    print("Text extraction complete.\n")

    print("Step 2: Building prompt...")
    prompt = build_prompt(full_text, question)
    print(prompt[:500] + "\n...prompt truncated...\n")

    print("Step 3: Querying LLM...")
    # Uncomment to query live
    llm_response = query_llm(prompt, token=api_token)
    with open("llm_response_3.pkl", 'wb') as f:
         pickle.dump(llm_response, f)
    with open("llm_response_3.pkl", 'rb') as f:
        llm_response = pickle.load(f)
    print("LLM response:", llm_response, "\n")

    print("Step 4: Matching evidence with page...")
    match_texts = [
        [fuzzy_match_evidence(q_part, full_text) for q_part in q_resp["evidence"]]
        for q_resp in llm_response["responses"]
    ]
    print("Matchings: ")
    for response, match in zip(llm_response["responses"], match_texts):
        print(response["evidence"])
        print(match)
    print()

    print("Step 5: Locating evidence in PDF...")
    locations_list = [
        locate_text_in_pdf(pdf_path, match)
        for match_group in match_texts
        for match in match_group if match
    ]
    print("Text locations in PDF:", locations_list, "\n")

    with open("text_location_list_2.pkl", 'wb') as f:
        pickle.dump(locations_list, f)

# New: Basic Info Extraction
# =========================

def build_basic_info_prompt(text):
    prompt = f"""
You are given the text of an academic research paper.

Extract the following information and return it in valid JSON only, matching this schema exactly:
{{
  "title": "...",
  "authors": ["Author 1", "Author 2", "..."],
  "year": "...",
  "conference_or_journal": "..."
}}

Rules:
- Use the paper's actual title as printed.
- Authors should be a list of names exactly as written in the paper.
- Year should be an integer.
- Conference or journal should be the name of the venue; if unknown, return null.

Text:
{text}
    """
    return prompt

def extract_basic_info_from_pdf(pdf_path, api_token):
    full_text, _ = extract_text_from_pdf(pdf_path)
    prompt = build_basic_info_prompt(full_text)
    return query_llm(prompt, token=api_token)

# New: Multi‑Question Analysis
# =========================

def build_multi_question_prompt(text, questions):
    question_list_str = "\n".join(
        [f'- {q["question"]} (question_id = "{q["question_id"]}")' for q in questions]
    )
    
    prompt = f"""
Given the following research paper text, answer the listed questions in valid JSON format.

Text:
{text}

Questions:
{question_list_str}

Answer Format:
{{
  "responses": [
    {{
      "question_id": "...",
      "answer": "###ANSWER### ... ###ENDANSWER###",
      "evidence": ["Exact quote from paper", "..."],
      "confidence": 0.0
    }}
  ]
}}

Rules:
- "answer" should be short and factual.
- "evidence" must match the paper text exactly.
- "confidence" is a float between 0.0 and 1.0.
- Always include ###ANSWER### and ###ENDANSWER### around the answer.
    """
    return prompt

def analyze_pdf_questions(pdf_path, questions, api_token):
    full_text, _ = extract_text_from_pdf(pdf_path)
    prompt = build_multi_question_prompt(full_text, questions)
    return query_llm(prompt, token=api_token)

# Script Entry Point
# =========================

if __name__ == "__main__":
    pdf_path = "/Users/krystianszczepankiewicz/Downloads/aff_states.pdf"
    api_token = "FAKE"

    # --- 1. Basic Info Extraction ---
    print("\n=== BASIC INFO EXTRACTION ===")
    basic_info = extract_basic_info_from_pdf(pdf_path, api_token)
    print(json.dumps(basic_info, indent=2))

    # --- 2. Single‑Question Proof of Concept ---
    print("\n=== SINGLE QUESTION ANALYSIS ===")
    analyze_pdf_question(
        pdf_path=pdf_path,
        question="How many participants are in the study?",
        api_token=api_token
    )

    # --- 3. Multi‑Question Analysis ---
    print("\n=== MULTI‑QUESTION ANALYSIS ===")
    questions = [
        {"question_id": "participant_count", "question": "How many participants are in the study?"},
        {"question_id": "participant_ages", "question": "What was the average age of the participants?"},
        {"question_id": "tracking_device", "question": "What tracking device was used in the study?"}
    ]
    multi_results = analyze_pdf_questions(pdf_path, questions, api_token)
    print(json.dumps(multi_results, indent=2))