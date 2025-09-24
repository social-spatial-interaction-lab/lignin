jjstrus
jjstrus
Invisible

l1fe1sg00d
[OAI]
 — 4/26/25, 2:33 PM
#include<stdio.h>
#include <string.h>
#include <stdlib.h>

int main(void) {

   /* Type your code here. /
   char title[100];
   char column1[100];
   char column2[100];
   char dataString[100][100];
   int dataInt[100];
   int numPoints = 0;
   char input[100];
   charcommaPosition;


   printf("Enter a title for the data:\n");
   fgets(title, sizeof(title), stdin);
   title[strcspn(title, "\n")] = '\0';
   printf("You entered: %s\n\n", title);

   printf("Enter the column 1 header:\n");
   fgets(column1, sizeof(column1), stdin);
   column1[strcspn(column1, "\n")] = '\0';
   printf("You entered: %s\n\n", column1);

   printf("Enter the column 2 header:\n");
   fgets(column2, sizeof(column2), stdin);
   column2[strcspn(column2, "\n")] = '\0';
   printf("You entered: %s\n", column2);
   printf("\n");

    printf("Enter a data point (-1 to stop input):\n");

   while(1){
    fgets(input, sizeof(input), stdin);
    input[strcspn(input, "\n")] = '\0';

    if(strcmp(input, "-1") == 0){
        break;
    }
    int commaCount = 0;
    for(int i = 0; input[i] != '\0'; i++){
        if(input[i] == ','){
            commaCount++;
        }
    }
    if(commaCount == 0){
        printf("Error: No comma in string.\n\n");
        printf("Enter a data point (-1 to stop input):\n");
        continue;
    }
    else if(commaCount > 1){
        printf("Error: Too many commas in input.\n\n");
        printf("Enter a data point (-1 to stop input):\n");
        continue;
    }
commaPosition = strchr(input, ',');
    commaPosition = '\0';
    strcpy(dataString[numPoints], input);

    int len = strlen(dataString[numPoints]);
    while(len > 0 && dataString[numPoints][len - 1] == ' '){
        dataString[numPoints][len - 1] = '\0';
        len--;
    }

    charintPart = commaPosition + 1;
    while(intPart == ' '){
        intPart++;
    }
    int isValidInteger = 1;
    if(intPart == '\0'){
        isValidInteger = 0;
    } else {
        for(int i = 0; intPart[i] != '\0'; i++){
            if(intPart[i] < '0' || intPart[i] > '9'){
                isValidInteger = 0;
                break;
            }
        }
    }
    if(!isValidInteger){
        printf("Error: Comma not followed by an integer.\n\n");
        printf("Enter a data point (-1 to stop input):\n");
        continue;
    }
    dataInt[numPoints] = atoi(intPart);
    printf("Data string: %s\n", dataString[numPoints]);
    printf("Data integer: %d\n", dataInt[numPoints]);
    printf("\n");
    numPoints++;
    printf("Enter a data point (-1 to stop input):\n");
   }
   printf("\n%33s\n", title);
   printf("%-20s|%23s\n", column1, column2);
   printf("--------------------------------------------\n");

   for(int i = 0; i < numPoints; i++){
    printf("%-20s|%23d\n", dataString[i], dataInt[i]);
   }
   printf("\n");
   for(int i = 0; i < numPoints; i++){
    printf("%20s ", dataString[i]);
    for(int j = 0; j < dataInt[i]; j++){
        printf("*");
    }
    printf("\n");
   }

   return 0;
}
l1fe1sg00d
[OAI]
 — 4/28/25, 1:48 PM
#include<stdio.h>
#include <string.h>

int main(void) {

   /* Type your code here. /
   char input[100];
   char firstWord[100];
   char secondWord[100];
   charcommaPosition;
while(1){
   printf("Enter input string:\n");
   fgets(input, sizeof(input), stdin);
    input[strcspn(input, "\n")] = '\0';
    if(strcmp(input, "q") == 0){
        return 0;
    }
   //check if there's a comma in the string
   if(strchr(input,  ',') == NULL){
    printf("Error: No comma in string.\n\n");
   } else {
    commaPosition = strchr(input, ',');
    *commaPosition = '\0';
    strcpy(firstWord, input);
    strcpy(secondWord, commaPosition + 1);

    int len = strlen(firstWord);
    while(len > 0 && firstWord[len-1] == ' '){
        firstWord[len-1] = '\0';
        len--;
    }

    while(secondWord[0] == ' '){
        memmove(secondWord, secondWord + 1, strlen(secondWord));
    }

    printf("First word: %s\n", firstWord);
    printf("Second word: %s\n\n", secondWord);
   }
}

   return 0;
}
jjstrus — 4/29/25, 2:32 PM
so we not going for swe at all?
lowkey we could like
lock the fuck in for leetcode this summer if we really want
we got nothing better to do lmfao
last resort
i dont know
l1fe1sg00d
[OAI]
 — 4/29/25, 2:33 PM
idk swe doesn't really interest me anymore
jjstrus — 4/29/25, 2:34 PM
idk if it fully interests me either but idk what else to do lol
l1fe1sg00d
[OAI]
 — 4/29/25, 2:34 PM
we can go to china and become warriors
jjstrus — 4/29/25, 2:34 PM
i think we should go to the uk tbh
claim we are migrants from pakistan
they get full benefits and housing
and a stipend
l1fe1sg00d
[OAI]
 — 4/30/25, 11:57 AM
https://www.cs.sfu.ca/~ashriram/Courses/CS295/assets/books/CSAPP_2016.pdf
l1fe1sg00d
[OAI]
 — 4/30/25, 1:34 PM
https://github.com/jon-whit/malloc-lab/blob/master/mm.c
GitHub
malloc-lab/mm.c at master · jon-whit/malloc-lab
Contribute to jon-whit/malloc-lab development by creating an account on GitHub.
Contribute to jon-whit/malloc-lab development by creating an account on GitHub.
l1fe1sg00d
[OAI]
 — 5/1/25, 8:02 PM
Forwarded
That exam will be in future CIA torture manuals

cs@iit  •  5/1/25
Ggs for me
jjstrus — 5/1/25, 8:29 PM
Jaceks exam?
l1fe1sg00d
[OAI]
 — 5/1/25, 8:44 PM
yup
jjstrus — 5/1/25, 9:31 PM
GG
You’re cooked
l1fe1sg00d
[OAI]
 — 5/2/25, 9:12 PM
this is my task:

The only file you will be modifying and handing in is mm.c. The mdriver.c program is a driver program
that allows you to evaluate the performance of your solution. Use the command make to generate the driver
code and run it with the command ./mdriver -V. (The -V flag displays helpful summary information.)
*Acknowledgment: This lab is based on earlier material by Bryant and O’Hallaron.
Expand
message.txt
23 KB
jjstrus — 5/2/25, 9:15 PM
// Add a global variable to track the last position
static char last_bp = NULL;

// Modify mm_malloc to use next-fit
voidmm_malloc(size_t size)
{
    if(size == 0) return NULL;
    size_t asize = ALIGN(size + DSIZE);

    // Start search from last position if available
    char bp = last_bp ? last_bp : heap_listp;
    charstart_bp = bp;
    int wrapped = 0;

    // Search from last position to end
    while(GET_SIZE(HDRP(bp)) != 0) {
        if(!GET_ALLOC(HDRP(bp)) && (GET_SIZE(HDRP(bp)) >= asize)) {
            place(bp, asize);
            last_bp = NEXT_BLKP(bp); // Update last position
            return bp;
        }
        bp = NEXT_BLKP(bp);

        // If we reach the end, wrap around to beginning
        if(GET_SIZE(HDRP(bp)) == 0 && !wrapped) {
            bp = heap_listp;
            wrapped = 1;
        }

        // If we've searched the entire heap, break
        if(bp == start_bp)
            break;
    }

    // If no fit found, extend heap
    size_t extendsize = MAX(asize, CHUNKSIZE);
    bp = extend_heap(extendsize / WSIZE);
    if(bp == NULL) return NULL;

    place(bp, asize);
    last_bp = NEXT_BLKP(bp); // Update last position
    return bp;
}

// Update mm_init to initialize last_bp
int mm_init(void)
{
    // Your existing code...
    heap_listp += (2*WSIZE);
    last_bp = heap_listp; // Initialize last_bp
    return 0;
}
^^^^^^^^^next fit
int mm_check(void)
{
    char *bp = heap_listp;

    // Check prologue blocks
    if(GET_SIZE(HDRP(heap_listp)) != DSIZE  !GET_ALLOC(HDRP(heap_listp)))
        printf("Error: Bad prologue header\n");

    // Check each block
    while(GET_SIZE(HDRP(bp)) > 0) {
        // Check block alignment
        if((unsigned long)bp % ALIGNMENT)
            printf("Error: %p is not aligned\n", bp);

        // Check header/footer match
        if(GET(HDRP(bp)) != GET(FTRP(bp)))
            printf("Error: Header does not match footer at %p\n", bp);

        // Check for contiguous free blocks
        if(!GET_ALLOC(HDRP(bp)) && !GET_ALLOC(HDRP(NEXT_BLKP(bp))))
            printf("Error: Contiguous free blocks not coalesced at %p\n", bp);

        bp = NEXT_BLKP(bp);
    }

    // Check epilogue block
    if(GET_SIZE(HDRP(bp)) != 0  !GET_ALLOC(HDRP(bp)))
        printf("Error: Bad epilogue header\n");

    return 1; // Return 1 if heap is consistent
}
heap consistency^^^
l1fe1sg00d
[OAI]
 — 5/2/25, 9:20 PM
errrors😂
mm.c:66:23: error: initialization of ‘char’ from ‘void *’ makes integer from pointer without a cast [-Werror=int-conversion]
   66 | static char last_bp = NULL;
      |                       ^~~~
mm.c: In function ‘mm_init’:
mm.c:82:10: error: assignment to ‘char’ from ‘char *’ makes integer from pointer without a cast [-Werror=int-conversion]
   82 |  last_bp = heap_listp;
Expand
message.txt
10 KB
this is my task:

The only file you will be modifying and handing in is mm.c. The mdriver.c program is a driver program
that allows you to evaluate the performance of your solution. Use the command make to generate the driver
code and run it with the command ./mdriver -V. (The -V flag displays helpful summary information.)
*Acknowledgment: This lab is based on earlier material by Bryant and O’Hallaron.
Expand
message.txt
13 KB
your code
put your results
l1fe1sg00d
[OAI]
 — 5/2/25, 9:27 PM
as you can see my throughput is very low. I asked my TA how to improve it and he gave me the following:

Your implementation looks good so far and just needs some optimization. These are some suggestions that I have that might or might not be able to improve your current implementation you will have to use your best judgement to decide what to do. 
Instead of using  first-fit you could implement next-fit
Optimize realloc to avoid copying when possible instead of always allocating a new block
Introduce a different fitting algorithm based on block size
Adjust block splitting thresholds based on request size
Add immediate coalescing when searching for free blocks
Again, it will depend on your implementation whether or not these suggestions provide improvements, but they could be a good place to start.
l1fe1sg00d
[OAI]
 — 5/3/25, 8:38 PM
Image
l1fe1sg00d
[OAI]
 — 5/4/25, 4:29 PM
this is my current code:

/*
 * mm-naive.c - The fastest, least memory-efficient malloc package.
 * 
 * In this naive approach, a block is allocated by simply incrementing
Expand
message.txt
11 KB
l1fe1sg00d
[OAI]
 — 5/5/25, 12:44 PM
Image
Image
Image
Image
Image
Image
Forwarded
Image
Image
Image
Image
Forwarded
Image
Image
Image
Image
3 people sent me their math final
They said you can skip 2 questions
jjstrus — 5/5/25, 1:21 PM
Sheeesh
Thank you man
Is it just the two versions?
If so imma write down both on my cheat sheets
l1fe1sg00d
[OAI]
 — 5/5/25, 1:24 PM
Not sure
l1fe1sg00d
[OAI]
 — 8/10/25, 1:57 PM
import fitz  # PyMuPDF
import json
import requests
import pickle
from fuzzysearch import find_near_matches
Expand
message.txt
9 KB
Couple things to note:

-make sure you import everything necessary.
if name == "main":
  pdf_path = "/Users/krystianszczepankiewicz/Downloads/aff_states.pdf"
  api_token = "GVnbyYlCjVJIvDzQClhhBZxJ20XjEOLM"

here change the pdf_path to wherever you have it downloaded. (I'll attach the pdf I used)
replace "FAKE" with the API key (Ill send it in a sec)

-def query_llm(prompt, model="mistralai/Mistral-7B-Instruct-v0.3", token="API TOKEN HERE"):
replace "API TOKEN HERE" with actual
Attachment file type: acrobat
aff_states.pdf
979.18 KB
Key: GVnbyYlCjVJIvDzQClhhBZxJ20XjEOLM
﻿
l1fe1sg00d
l1fe1sg00d
[OAI]
 
 
 
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