import fitz  # PyMuPDF
import json
import requests
import pickle


# Step 1: Extract text from PDF
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text_by_page = [page.get_text() for page in doc]
    full_text = "\n".join(text_by_page)
    return full_text, text_by_page


# Step 2: Construct prompt for the language model
def build_prompt(text, question):
    prompt = f"""
Given the following research paper, please answer the following questions in JSON format:

Text:
{text}

Answer Format: 
{{
  "responses:" [
    {{
       "question_id": "...",
       "answer": "...",
       "evidence": "...",
       "confidence": 0.5
    }},
    ... # Other questions have the same dictionary structure within the 'responses' array.
  ]
}}

- "question_id" should match one of the question_ids from the questions given below
- "answer" should be an answer to the question in a word, phrase, or sentence.
- "evidence" should be text directly from the research paper given above.
- "confidence" should be the confidence score of the answer as a float, where 0.0 is low confidence, 1.0 is high confidence.

Questions:
- How many participants are in the study? (question_id = "participant_count")
- What information was given about the age of the participants in the study? (question_id = "participant_ages")
- What devices were used to track the motion in the study? (question_id = "tracking_device")
- What frame rate was this motion tracked at? (question_id = "frame_rate")
- What variable (environmental or individual) was being inferred from this motion? (question_id = "inferred_variable")

"""
    return prompt


# Step 3: Query Mistral 7B via DeepInfra
def query_llm(prompt, model="mistralai/Mistral-7B-Instruct-v0.3", token="YOUR_DEEPINFRA_API_KEY"):
    url = f"https://api.deepinfra.com/v1/openai/chat/completions"
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


# Step 4: Match extracted evidence with original PDF text (fuzzy)
def fuzzy_match_evidence(evidence, text_by_page):
    best_score = 0
    best_page = -1
    for i, page_text in enumerate(text_by_page):
        #score = Levenshtein.ratio(evidence.lower(), page_text.lower())
        #if score > best_score:
        #    best_score = score
        #    best_page = i
        pass
    return best_page, best_score


# Step 5: Locate evidence in PDF by bounding boxes
def locate_text_in_pdf(pdf_path, target_text):
    doc = fitz.open(pdf_path)
    locations = []

    for page_number in range(len(doc)):
        page = doc[page_number]
        ptm = page.transformation_matrix
        text_instances = page.search_for(target_text, quads=True)  # returns quads, better spatial matching
        if text_instances:
            locations.append({
                "page": page_number,
                "rectangles": [quad.rect * ~ptm for quad in text_instances]
            })

    return locations


# Step 6: Orchestration function
def analyze_pdf_question(pdf_path, question, api_token):
    print("Step 1: Extracting text from PDF...")
    full_text, text_by_page = extract_text_from_pdf(pdf_path)
    print("Text extraction complete.\n")

    print("Step 2: Building prompt...")
    prompt = build_prompt(full_text, question)
    print(prompt[:500] + "\n...prompt truncated...\n")

    print("Step 3: Querying LLM...")
    llm_response = query_llm(prompt, token=api_token)
    #with open("llm_response_2.pkl", 'wb') as f:
    #    pickle.dump(llm_response, f)
    with open("llm_response.pkl", 'rb') as f:
        llm_response = pickle.load(f)
    print("LLM response:", llm_response, "\n")

    #print("Step 4: Matching evidence with page...")
    #page_index, score = fuzzy_match_evidence(llm_response["evidence"], text_by_page)
    #print(f"Best match on page {page_index + 1} with score {score:.2f}\n")

    print("Step 5: Locating evidence in PDF...")
    locations = locate_text_in_pdf(pdf_path, llm_response["evidence"])
    print("Text locations in PDF:", locations, "\n")

    with open("text_location.pkl", 'wb') as f:
        pickle.dump(locations, f)

    return {
        "question": question,
        "answer": llm_response["answer"],
        "confidence": llm_response["confidence"],
        #"page": page_index + 1,
        "locations": locations
    }

if __name__ == "__main__":
    result = analyze_pdf_question(
        pdf_path="ligninapp/static/ligninapp/aff_states.pdf",
        question="How many participants are in the study?",
        api_token=""
    )

    # actually first, see if the text selection renders.

    with open("text_location.pkl", 'rb') as f:
        text_locations = pickle.load(f)
        print(text_locations)

