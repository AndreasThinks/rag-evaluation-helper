from fasthtml.common import (
    A, Button, Card, Container, Div, Form, Grid, Group, H2, H3, H4, Hidden,
    Input, Li, P, Textarea, Title, Titled, Ul, Label, Style,
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


app, rt = fast_app(htmlkw={'data-theme': 'light'}, hdrs=[Style("""
    /* Global styles */
    :root {
        --primary-color: #4361ee;
        --secondary-color: #3f37c9;
        --accent-color: #4895ef;
        --success-color: #4cc9f0;
        --background-color: #f8f9fa;
        --text-color: #212529;
        --border-radius: 8px;
        --spacing-sm: 0.5rem;
        --spacing-md: 1rem;
        --spacing-lg: 2rem;
    }

    body {
        background-color: var(--background-color);
        color: var(--text-color);
        line-height: 1.6;
    }

    /* Typography */
    h1, h2, h3, h4 {
        margin-bottom: var(--spacing-md);
        color: var(--text-color);
    }

    h1 { font-size: 2.5rem; }
    h2 { font-size: 2rem; }
    h3 { font-size: 1.75rem; }
    h4 { font-size: 1.5rem; }

    /* Layout */
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: var(--spacing-lg);
    }

    .grid {
        gap: var(--spacing-md);
    }

    /* Cards */
    .card {
        background: white;
        border-radius: var(--border-radius);
        padding: var(--spacing-lg);
        margin-bottom: var(--spacing-lg);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .stats-card {
        background: linear-gradient(to right, #ffffff, #f8f9fa);
    }

    /* Forms */
    input, textarea {
        border: 1px solid #dee2e6;
        border-radius: var(--border-radius);
        padding: var(--spacing-sm);
        width: 100%;
        margin-bottom: var(--spacing-md);
    }

    textarea {
        min-height: 150px;
    }

    /* Buttons */
    .button-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: var(--spacing-md);
        margin: var(--spacing-lg) 0;
    }

    button, .button {
        background-color: var(--primary-color);
        color: white;
        border: none;
        border-radius: var(--border-radius);
        padding: var(--spacing-sm) var(--spacing-md);
        cursor: pointer;
        transition: background-color 0.3s ease;
    }

    button:hover, .button:hover {
        background-color: var(--secondary-color);
    }

    button.outline, .button.outline {
        background-color: transparent;
        border: 2px solid var(--primary-color);
        color: var(--primary-color);
    }

    button.outline:hover, .button.outline:hover {
        background-color: var(--primary-color);
        color: white;
    }

    /* Lists */
    .question-list {
        list-style: none;
        padding: 0;
    }

    .question-list li {
        padding: var(--spacing-md);
        margin-bottom: var(--spacing-sm);
        background: white;
        border-radius: var(--border-radius);
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
    }

    .question-list li:hover {
        transform: translateX(5px);
    }

    .url-list {
        list-style: none;
        padding: 0;
    }

    .url-list li {
        padding: var(--spacing-sm);
        margin-bottom: var(--spacing-sm);
        background: #f8f9fa;
        border-radius: var(--border-radius);
    }

    /* Answer sections */
    .answer-text {
        background: #f8f9fa;
        padding: var(--spacing-md);
        border-radius: var(--border-radius);
        margin-bottom: var(--spacing-md);
    }

    .answer-section {
        margin: var(--spacing-lg) 0;
    }

    /* URL ranking section */
    .url-ranking {
        list-style: none;
        padding: 0;
    }

    .url-ranking li {
        padding: var(--spacing-md);
        margin-bottom: var(--spacing-sm);
        background: #f8f9fa;
        border-radius: var(--border-radius);
    }

    /* Stats list */
    .stats-list {
        list-style: none;
        padding: 0;
    }

    .stats-list li {
        padding: var(--spacing-md);
        margin-bottom: var(--spacing-sm);
        background: #f8f9fa;
        border-radius: var(--border-radius);
        border-left: 4px solid var(--primary-color);
    }
""")])

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
            Button("Submit Question", type="submit", cls="primary")
        ),
        hx_post="/questions",
        hx_target="#question-section"
    )
    
    # Create list of existing questions
    question_list = Ul(
        *[Li(
            A(q.text, hx_get=f"/questions/{q.id}", hx_target="#question-section")
        ) for q in existing_questions],
        cls="question-list"
    ) if existing_questions else P("No questions yet")

    # Add links to best answers and top answers pages
    best_answers_link = A("View Questions with Multiple Answers", href="/best-answers", cls="button outline")
    top_answers_link = A("View Top Answers & Sources", href="/top-answers", cls="button outline")

    return Titled("RAG Evaluation Tool",
        Container(
            H2("Submit a New Question"),
            new_question_form,
            H2("Or Choose an Existing Question"),
            Div(best_answers_link, top_answers_link, cls="button-grid"),
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
            Button("Add URL", type="submit", cls="outline")
        ),
        hx_post=f"/questions/{id}/urls",
        hx_target="#url-list"
    )
    
    # List of submitted URLs
    url_list = Div(
        H3("Submitted URLs"),
        Ul(*[Li(u.url) for u in existing_urls], cls="url-list") if existing_urls else P("No URLs submitted yet"),
        id="url-list"
    )
    
    # User answer form
    answer_form = Form(
        Group(
            H3("Write Your Perfect Answer"),
            Textarea(id="user_answer", name="user_answer", rows=10, placeholder="Write your answer here, referencing the URLs where appropriate"),
            Button("Submit Answer", type="submit", cls="primary")
        ),
        hx_post=f"/questions/{id}/user-answer",
        hx_target="#answer-section",
        cls="answer-section"
    )
    
    return Card(
        H2(f"Question: {q.text}"),
        url_form,
        url_list,
        answer_form,
        Div(id="answer-section"),
        cls="card"
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
    return Ul(*[Li(u.url) for u in url_list], cls="url-list")

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
                P(user_answer, cls="answer-text"),
                header="User Generated"
            ),
            Card(
                H4("LLM Answer"),
                P(llm_answer, cls="answer-text"),
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
            Button("Submit Final Answer", type="submit", cls="primary"),
            hx_post=f"/questions/{id}/final-answer/{answer.id}",
            hx_target="#final-section"
        ),
        Div(id="final-section"),
        cls="card"
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
        A("Start New Evaluation", href="/", cls="button outline"),
        cls="card"
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
        ) for q, count in questions_with_answers],
        cls="question-list"
    ) if questions_with_answers else P("No questions with multiple answers yet")

    return Titled("Questions with Multiple Answers",
        Container(
            H2("Select Best Answer"),
            P("The following questions have multiple answers. Click to select the best one."),
            question_list,
            A("Back to Home", href="/", cls="button outline")
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
    
    # Get all URLs for this question
    all_urls = urls(where="question_id = ?", where_args=[id])
    
    # Create pairs of answers for comparison
    answer_pairs = []
    for i in range(0, len(all_answers), 2):
        if i + 1 < len(all_answers):
            answer_pairs.append((all_answers[i], all_answers[i + 1]))
    
    return Titled(f"Select Best Answer for: {q.text}",
        Container(
            H2(q.text),
            *[Card(
                H3("Compare Answers"),
                Grid(
                    Card(
                        H4(pair[0]['type']),
                        P(pair[0]['text'], cls="answer-text"),
                        *([] if not pair[0]['sources'] else [P("Sources:", pair[0]['sources'])]),
                        Form(
                            Hidden(name="answer_id", value=pair[0]['record_id']),
                            Hidden(name="answer_type", value="user" if pair[0]['type'] == 'User Answer' else "llm"),
                            Hidden(name="question_id", value=id),
                            Button("Select as Best Answer", type="submit", cls="outline"),
                            hx_post=f"/best-answers/{id}/select"
                        ),
                        cls="card"
                    ),
                    Card(
                        H4(pair[1]['type']),
                        P(pair[1]['text'], cls="answer-text"),
                        *([] if not pair[1]['sources'] else [P("Sources:", pair[1]['sources'])]),
                        Form(
                            Hidden(name="answer_id", value=pair[1]['record_id']),
                            Hidden(name="answer_type", value="user" if pair[1]['type'] == 'User Answer' else "llm"),
                            Hidden(name="question_id", value=id),
                            Button("Select as Best Answer", type="submit", cls="outline"),
                            hx_post=f"/best-answers/{id}/select"
                        ),
                        cls="card"
                    )
                ),
                cls="card"
            ) for pair in answer_pairs],
            H3("Rate All Sources"),
            Form(
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
                Button("Save Source Ratings", type="submit", cls="primary"),
                hx_post=f"/best-answers/{id}/rate-sources",
                hx_target="#rating-result"
            ),
            Div(id="rating-result"),
            A("Back to Questions", href="/best-answers", cls="button outline")
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
        A("Back to Questions", href="/best-answers", cls="button outline"),
        cls="card"
    )

@rt("/best-answers/{id}/rate-sources")
async def post(request, id: int):
    # Get form data
    form_data = await request.form()
    
    # Get all URLs for this question
    url_list = urls(where="question_id = ?", where_args=[id])
    
    # Extract URL rankings and relevance from form
    url_data = []
    for u in url_list:
        rank = form_data.get(f"rank_{u.id}", "0")
        relevant = "1" if form_data.get(f"relevant_{u.id}") else "0"
        url_data.append(f"{u.url}:{rank}:{relevant}")
    
    # Update all answers for this question with the URL data
    answer_records = answers(where="question_id = ?", where_args=[id])
    for a in answer_records:
        answers.update(dict(
            url_ranking=",".join(url_data)
        ), a.id)
    
    return Card(
        H3("Source Ratings Saved"),
        P("Your source ratings have been saved successfully."),
        A("Back to Questions", href="/best-answers", cls="button outline"),
        cls="card"
    )

@rt("/top-answers")
def get():
    # Get all questions
    all_questions = questions()
    
    # Create list of questions
    question_list = Ul(
        *[Li(
            A(q.text, href=f"/top-answers/{q.id}")
        ) for q in all_questions],
        cls="question-list"
    ) if all_questions else P("No questions yet")

    return Titled("Top Answers & Sources",
        Container(
            H2("Select a Question"),
            P("Click on a question to see its top answers and most relevant sources."),
            question_list,
            A("Back to Home", href="/", cls="button outline")
        )
    )

@rt("/top-answers/{id}")
def get(id: int):
    q = questions[id]
    answer_records = answers(where="question_id = ?", where_args=[id])
    
    # Count frequency of each final answer
    answer_counts = {}
    for record in answer_records:
        if record.final_answer:
            answer_counts[record.final_answer] = answer_counts.get(record.final_answer, 0) + 1
    
    # Sort answers by frequency
    sorted_answers = sorted(answer_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Count frequency of relevant sources
    url_counts = {}
    for record in answer_records:
        if record.url_ranking:
            for url_data in record.url_ranking.split(','):
                # Split on last two colons to handle URLs containing colons
                parts = url_data.rsplit(':', 2)
                if len(parts) == 3:
                    url, _, relevant = parts
                    if relevant == "1":
                        url_counts[url] = url_counts.get(url, 0) + 1
    
    # Sort sources by frequency
    sorted_sources = sorted(url_counts.items(), key=lambda x: x[1], reverse=True)
    
    return Titled(f"Top Answers & Sources for: {q.text}",
        Container(
            H2(q.text),
            Card(
                H3("Most Selected Answers"),
                Ul(*[Li(
                    P(f"Selected {count} times:"),
                    P(answer, cls="answer-text")
                ) for answer, count in sorted_answers], cls="stats-list") if sorted_answers else P("No answers selected yet"),
                header="Top Answers",
                cls="stats-card"
            ),
            Card(
                H3("Most Relevant Sources"),
                Ul(*[Li(
                    f"{url} (marked relevant {count} times)"
                ) for url, count in sorted_sources], cls="stats-list") if sorted_sources else P("No sources marked as relevant yet"),
                header="Top Sources",
                cls="stats-card"
            ),
            A("Back to Questions", href="/top-answers", cls="button outline")
        )
    )

def redirect_to_question(id: int):
    return RedirectResponse(f"/questions/{id}", status_code=303)

serve()
