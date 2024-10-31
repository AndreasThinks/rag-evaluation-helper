from fasthtml.common import (
    A, Button, Card, Container, Div, Form, Grid, Group, H2, H3, H4, Hidden,
    Input, Li, P, Textarea, Title, Titled, Ul, Label,
    FastHTML, fast_app, serve,
    RedirectResponse, database
)
from typing import List
from collections import OrderedDict

# Initialize database
db = database('data/rag.db')

questions,urls,answers = db.t.questions,db.t.urls,db.t.answers

# Get or create tables using the tables collection (t)
if 'questions' not in db.t:
    questions.create(dict(id=int, text=str), pk='id')
    urls.create(dict(id=int, question_id=int, url=str, source=str), pk='id')
    answers.create(dict(
        id=int,
        question_id=int,
        user_answer=str,
        llm_answer=str,
        llm_sources=str,
        final_answer=str,
        url_ranking=str,
        url_relevance=str
    ), pk='id')
else:
    # Get existing tables
    questions = db.t.questions
    urls = db.t.urls
    answers = db.t.answers

# Get dataclasses from tables
Question = questions.dataclass()
Url = urls.dataclass()
Answer = answers.dataclass()

app, rt = fast_app()

# Debug mode for LLM simulation
DEBUG_MODE = True

def simulate_llm_response(question: str, urls: List[str]) -> tuple:
    """Debug function to simulate LLM response when API is not available"""
    return (
        "This is a simulated LLM answer that would normally come from the API. "
        "It demonstrates how the system works without needing the actual LLM service.",
        ["https://example.com/doc1", "https://example.com/doc2"]
    )

@rt("/")
def get():
    # Get existing questions
    existing_questions = questions()
    
    # Create form for new question submission
    new_question_form = Form(
        Group(
            Input(id="question", name="question", placeholder="Enter your question"),
            Button("Submit Question", type="submit")
        ),
        hx_post="/questions",
        hx_target="#question-section"
    )
    
    # Create list of existing questions
    question_list = Ul(
        *[Li(
            A(q.text, hx_get=f"/questions/{q.id}", hx_target="#question-section")
        ) for q in existing_questions]
    ) if existing_questions else P("No questions yet")

    # Add link to best answers page
    best_answers_link = A("View Questions with Multiple Answers", href="/best-answers", cls="button")

    return Titled("RAG Evaluation Tool",
        Container(
            H2("Submit a New Question"),
            new_question_form,
            H2("Or Choose an Existing Question"),
            best_answers_link,
            question_list,
            Div(id="question-section")
        )
    )

@rt("/questions")
async def post(request):
    # Get question from form data
    form_data = await request.form()
    question_text = form_data.get("question", "")
    
    # Check if question already exists
    existing = questions(where="text = ?", where_args=[question_text])
    if existing:
        # If exists, redirect to existing question
        return redirect_to_question(existing[0].id)
    
    # Insert new question if it doesn't exist
    q = questions.insert(dict(text=question_text))
    return redirect_to_question(q.id)

@rt("/questions/{id}")
def get(id: int):
    q = questions[id]
    # Fixed query syntax for FastLite
    existing_urls = urls(where="question_id = ?", where_args=[id])
    
    # URL submission form
    url_form = Form(
        Group(
            Input(id="url", name="url", placeholder="Enter a relevant URL"),
            Button("Add URL", type="submit")
        ),
        hx_post=f"/questions/{id}/urls",
        hx_target="#url-list"
    )
    
    # List of submitted URLs
    url_list = Div(
        H3("Submitted URLs"),
        Ul(*[Li(u.url) for u in existing_urls]) if existing_urls else P("No URLs submitted yet"),
        id="url-list"
    )
    
    # User answer form
    answer_form = Form(
        Group(
            H3("Write Your Perfect Answer"),
            Textarea(id="user_answer", name="user_answer", rows=10, placeholder="Write your answer here, referencing the URLs where appropriate"),
            Button("Submit Answer", type="submit")
        ),
        hx_post=f"/questions/{id}/user-answer",
        hx_target="#answer-section"
    )
    
    return Card(
        H2(f"Question: {q.text}"),
        url_form,
        url_list,
        answer_form,
        Div(id="answer-section")
    )

@rt("/questions/{id}/urls")
async def post(request, id: int):
    # Get URL from form data
    form_data = await request.form()
    url = form_data.get("url", "")
    # Insert new URL
    urls.insert(dict(question_id=id, url=url, source="user"))
    # Return updated URL list
    url_list = urls(where="question_id = ?", where_args=[id])
    return Ul(*[Li(u.url) for u in url_list])

@rt("/questions/{id}/user-answer")
async def post(request, id: int):
    # Get user answer from form data
    form_data = await request.form()
    user_answer = form_data.get("user_answer", "")
    
    # Get URLs for this question
    url_list = urls(where="question_id = ?", where_args=[id])
    url_texts = [u.url for u in url_list]
    
    # Get LLM answer (or simulate in debug mode)
    if DEBUG_MODE:
        llm_answer, llm_sources = simulate_llm_response(questions[id].text, url_texts)
    else:
        # TODO: Implement actual LLM API call
        llm_answer, llm_sources = simulate_llm_response(questions[id].text, url_texts)
    
    # Store LLM sources as URLs
    for source in llm_sources:
        if not urls(where="url = ? AND question_id = ?", where_args=[source, id]):
            urls.insert(dict(question_id=id, url=source, source="llm"))
    
    # Store answers
    answer = answers.insert(dict(
        question_id=id,
        user_answer=user_answer,
        llm_answer=llm_answer,
        llm_sources=",".join(llm_sources),
        final_answer="",
        url_ranking="",
        url_relevance=""
    ))
    
    # Get combined unique sources
    all_urls = urls(where="question_id = ?", where_args=[id])
    
    # Show comparison view
    return Card(
        H3("Compare Answers"),
        Grid(
            Card(
                H4("Your Answer"),
                P(user_answer),
                header="User Generated"
            ),
            Card(
                H4("LLM Answer"),
                P(llm_answer),
                P("Sources:", ", ".join(llm_sources)),
                header="AI Generated"
            )
        ),
        Form(
            H3("Submit Final Perfect Answer"),
            P("Review and rate all sources:"),
            Ul(*[Li(
                Grid(
                    # Rank input for sorting
                    Input(type="number", 
                          name=f"rank_{u.id}", 
                          value="0", 
                          min="0", 
                          max=str(len(all_urls)),
                          style="width: 60px;"),
                    # URL display
                    P(u.url),
                    # Relevance toggle switch
                    Group(
                        Input(
                            type="checkbox",
                            role="switch",
                            name=f"relevant_{u.id}",
                            id=f"relevant_{u.id}"
                        ),
                        Label("Relevant", for_=f"relevant_{u.id}")
                    ),
                    # Source indicator
                    P(f"Source: {u.source}", 
                      style="color: var(--pico-muted-color);")
                )
            ) for u in all_urls], 
            cls="url-ranking"),
            H3("Write Final Answer"),
            Textarea(
                id="final_answer",
                name="final_answer",
                rows=10,
                placeholder="Write the perfect answer combining the best of both responses"
            ),
            Button("Submit Final Answer", type="submit"),
            hx_post=f"/questions/{id}/final-answer/{answer.id}",
            hx_target="#final-section"
        ),
        Div(id="final-section")
    )

@rt("/questions/{qid}/final-answer/{aid}")
async def post(request, qid: int, aid: int):
    # Get form data
    form_data = await request.form()
    final_answer = form_data.get("final_answer", "")
    
    # Extract URL rankings and relevance from form
    url_list = urls(where="question_id = ?", where_args=[qid])
    url_data = []
    for u in url_list:
        rank = form_data.get(f"rank_{u.id}", "0")
        relevant = "1" if form_data.get(f"relevant_{u.id}") else "0"
        url_data.append(f"{u.url}:{rank}:{relevant}")
    
    # Update answer with final version and URL data
    answers.update(dict(
        final_answer=final_answer,
        url_ranking=",".join(url_data)
    ), aid)
    
    return Card(
        H3("Evaluation Complete"),
        P("Your final answer and URL evaluations have been saved."),
        A("Start New Evaluation", href="/", cls="button")
    )

@rt("/best-answers")
def get():
    # Get questions with multiple answers
    questions_with_answers = []
    for q in questions():
        # Count total number of answers (both user and LLM)
        answer_records = answers(where="question_id = ?", where_args=[q.id])
        total_answers = sum(2 for a in answer_records)  # Each record has both user and LLM answer
        if total_answers >= 2:
            questions_with_answers.append((q, total_answers))
    
    # Create list of questions with multiple answers
    question_list = Ul(
        *[Li(
            A(f"{q.text} ({count} answers)", 
              href=f"/best-answers/{q.id}")
        ) for q, count in questions_with_answers]
    ) if questions_with_answers else P("No questions with multiple answers yet")

    return Titled("Questions with Multiple Answers",
        Container(
            H2("Select Best Answer"),
            P("The following questions have multiple answers. Click to select the best one."),
            question_list,
            A("Back to Home", href="/", cls="button")
        )
    )

@rt("/best-answers/{id}")
def get(id: int):
    q = questions[id]
    answer_records = answers(where="question_id = ?", where_args=[id])
    
    # Create a list of all answers (both user and LLM)
    all_answers = []
    for record in answer_records:
        # Add user answer
        all_answers.append({
            'text': record.user_answer,
            'type': 'User Answer',
            'id': f"{record.id}_user",
            'record_id': record.id,
            'sources': None
        })
        # Add LLM answer
        all_answers.append({
            'text': record.llm_answer,
            'type': 'LLM Answer',
            'id': f"{record.id}_llm",
            'record_id': record.id,
            'sources': record.llm_sources
        })
    
    return Titled(f"Select Best Answer for: {q.text}",
        Container(
            H2(q.text),
            *[Card(
                H3(f"Answer Option {i+1}"),
                P(answer['text']),
                P(f"Type: {answer['type']}"),
                *([] if not answer['sources'] else [P("Sources:", answer['sources'])]),
                Form(
                    Hidden(name="answer_id", value=answer['record_id']),
                    Hidden(name="answer_type", value="user" if answer['type'] == 'User Answer' else "llm"),
                    Hidden(name="question_id", value=id),
                    Button("Select as Best Answer", type="submit"),
                    hx_post=f"/best-answers/{id}/select"
                )
            ) for i, answer in enumerate(all_answers)],
            A("Back to Questions", href="/best-answers", cls="button")
        )
    )

@rt("/best-answers/{id}/select")
async def post(request, id: int):
    form_data = await request.form()
    answer_id = int(form_data.get("answer_id"))
    answer_type = form_data.get("answer_type")
    
    # Get the selected answer record
    selected_record = answers[answer_id]
    
    # Get the selected answer text based on type
    selected_answer = selected_record.user_answer if answer_type == "user" else selected_record.llm_answer
    
    # Update all answers for this question to mark this as best
    other_answers = answers(where="question_id = ?", where_args=[id])
    for a in other_answers:
        answers.update(dict(
            final_answer=selected_answer
        ), a.id)
    
    return Card(
        H3("Best Answer Selected"),
        P("The selected answer has been marked as the best answer for this question."),
        A("Back to Questions", href="/best-answers", cls="button")
    )

def redirect_to_question(id: int):
    return RedirectResponse(f"/questions/{id}", status_code=303)

serve()
