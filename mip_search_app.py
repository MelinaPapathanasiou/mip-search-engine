from flask import Flask, request, render_template_string, jsonify, send_from_directory, abort
from pathlib import Path
from difflib import get_close_matches
import json

app = Flask(__name__)
TEXT_FOLDER = Path("mip_texts")
PDF_FOLDER = Path("mip_pdfs")

def search_keyword_in_file(file_path, keyword):
    keyword = keyword.lower()
    results = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        lines = file.readlines()
        for idx, line in enumerate(lines):
            print(f"Checking line: {line.strip()}")
            if keyword in line.lower():
                context = '... ' + line.strip()[:200] + ' ...'
                results.append({"line": idx + 1, "snippet": context})
    return results

@app.route("/")
def index():
    return render_template_string('''
        <html>
        <head><title>Document Search</title></head>
        <body>
            <h2>Search MIP Text Files</h2>
            <form method="get" action="/search">
                <input type="text" name="q" placeholder="Enter keyword or phrase" style="width:300px"/>
                <input type="submit" value="Search" />
            </form>
        </body>
        </html>
    ''')

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return "Missing query parameter 'q'", 400

    matches = []
    for txt_file in TEXT_FOLDER.glob("*.txt"):
        results = search_keyword_in_file(txt_file, query)
        if results:
            matches.append({"file": txt_file.name, "matches": results})

    if request.headers.get("Accept") == "application/json":
        return jsonify({"query": query, "results": matches})

    return render_template_string('''
        <html>
        <head><title>Results for: {{ query }}</title></head>
        <body>
            <h2>Results for: <em>{{ query }}</em></h2>
            <a href="/">Back to Search</a>
            {% if results %}
                <ul>
                {% for item in results %}
                    <li>
                        <strong>{{ item.file }}</strong>
                        <ul>
                        {% for m in item.matches %}
                            <li>Line {{ m.line }}: {{ m.snippet }}</li>
                        {% endfor %}
                        </ul>
                    </li>
                {% endfor %}
                </ul>
            {% else %}
                <p>No results found.</p>
            {% endif %}
        </body>
        </html>
    ''', query=query, results=matches)

@app.route("/get_pdf/<query>")
def get_pdf_fuzzy(query):
    query = query.lower()
    pdf_files = [f.name for f in PDF_FOLDER.glob("*.pdf")]

    # Fuzzy match
    matches = get_close_matches(query, pdf_files, n=1, cutoff=0.3)

    if matches:
        filename = matches[0]
        pdf_path = PDF_FOLDER / filename
        if pdf_path.exists():
            return send_from_directory(PDF_FOLDER, filename, as_attachment=True)

    return abort(404)

@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing query parameter 'q'"}), 400

    matches = []
    for txt_file in TEXT_FOLDER.glob("*.txt"):
        results = search_keyword_in_file(txt_file, query)
        if results:
            matches.append({"file": txt_file.name, "matches": results})

    return jsonify({"query": query, "results": matches})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

