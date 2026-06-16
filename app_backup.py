from flask import Flask, render_template, request, redirect
from pathlib import Path
from pypdf import PdfReader
from ollama import chat

app = Flask(__name__)

UPLOAD_FOLDER = Path("docs")
UPLOAD_FOLDER.mkdir(exist_ok=True)

documents = {}


def load_documents():

    docs = {}

    for file in UPLOAD_FOLDER.iterdir():

        content = ""

        if file.suffix.lower() == ".pdf":

            try:

                reader = PdfReader(file)

                for page in reader.pages:

                    text = page.extract_text()

                    if text:
                        content += text + "\n"

            except Exception:
                continue

        elif file.suffix.lower() == ".txt":

            try:

                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()

            except Exception:
                continue

        docs[file.name] = content

    return docs


documents = load_documents()


@app.route("/", methods=["GET", "POST"])
def home():

    global documents

    answer = None
    source = None
    question = None

    if request.method == "POST":

        question = request.form.get("question")

        if question:

            best_doc = None
            best_score = 0

            question_words = question.lower().split()

            for filename, content in documents.items():

                score = 0

                for word in question_words:

                    if word in content.lower():
                        score += 1

                if score > best_score:
                    best_score = score
                    best_doc = filename

            # If document appears relevant, use it
            if best_doc and best_score >= 2:

                prompt = f"""
Answer the question using the document below.

DOCUMENT NAME:
{best_doc}

DOCUMENT:
{documents[best_doc][:5000]}

QUESTION:
{question}
"""

                response = chat(
                    model="qwen3",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                answer = response.message.content
                source = best_doc

            # Otherwise behave like a normal assistant
            else:

                response = chat(
                    model="qwen3",
                    messages=[
                        {
                            "role": "user",
                            "content": question
                        }
                    ]
                )

                answer = response.message.content
                source = "General Assistant"

    return render_template(
        "index.html",
        answer=answer,
        source=source,
        question=question,
        document_count=len(documents),
        document_names=documents.keys()
    )


@app.route("/upload", methods=["POST"])
def upload():

    global documents

    uploaded_file = request.files.get("file")

    if uploaded_file and uploaded_file.filename:

        save_path = UPLOAD_FOLDER / uploaded_file.filename

        uploaded_file.save(save_path)

        documents = load_documents()

    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)