from flask import Flask, request, render_template_string, jsonify, redirect, Response
from pathlib import Path
from fuzzywuzzy import fuzz
import os
from urllib.parse import quote
from datetime import datetime
import unicodedata

def normalize_text(text):
    """Μετατρέπει κείμενο σε πεζά και αφαιρεί τόνους για καλύτερη σύγκριση."""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text

def format_size(bytes_):
    for unit in ['B','KB','MB','GB']:
        if bytes_ < 1024.0:
            return f"{bytes_:.1f} {unit}"
        bytes_ /= 1024.0
    return f"{bytes_:.1f} TB"

app = Flask(__name__)
TEXT_FOLDER = Path("mip_texts")
PDF_FOLDER = Path("static/mip_pdfs")

def search_keyword_in_file(file_path, keyword):
    keyword = normalize_text(keyword)
    results = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        lines = file.readlines()
        for idx, line in enumerate(lines):
            if keyword in normalize_text(line):
                context = '... ' + line.strip()[:200] + ' ...'
                results.append({"line": idx + 1, "snippet": context})
    return results

@app.route("/")
def index():
    return render_template_string('''
        <html>
        <head><title>Document Search</title></head>
        <body style="font-family: Arial; padding: 2rem;">
            <h2>Search MIP Text Files</h2>
            <form method="get" action="/search" style="margin-bottom: 1.5rem;">
                <input type="text" name="q" placeholder="Enter keyword or phrase" style="width:300px"/>
                <input type="submit" value="Search" />
            </form>

            <hr style="margin: 1.5rem 0;">

            <h3>🔎 Find official PDF forms</h3>
            <a href="/pretty_pdf">
                <button type="button" style="padding:0.5rem 1rem;">Open PDF Finder</button>
            </a>
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

@app.route('/get_pdf/<query>')
def get_multiple_pdfs(query):
    q_norm = normalize_text(query)
    matched_files = []

    for filename in os.listdir(PDF_FOLDER):
        if not filename.endswith('.pdf'):
            continue

        name_norm = normalize_text(filename)

        if any(fuzz.partial_ratio(word, name_norm) >= 70 for word in q_norm.split()):
            file_path = os.path.join(str(PDF_FOLDER), filename)
            size_bytes = os.path.getsize(file_path)
            mtime = os.path.getmtime(file_path)
            matched_files.append({
                "filename": filename,
                "url": f"/static/mip_pdfs/{filename}",
                "size": format_size(size_bytes),
                "modified": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            })

    if not matched_files:
        return jsonify({"query": query, "message": "No matching PDF files found."}), 404

    return jsonify({"query": query, "matched_files": matched_files})

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

# -------- NEW: JSON endpoint for Easy-Peasy --------
@app.route("/api/search_text")
def api_search_text():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({
            "message": "❌ Empty query.\n\n👉 Open PDF Finder: https://mipengine-melina.onrender.com/pretty_pdf"
        })

    # ίδια λογική με /api/search
    matches = []
    for txt_file in TEXT_FOLDER.glob("*.txt"):
        results = search_keyword_in_file(txt_file, query)
        if results:
            matches.append({"file": txt_file.name, "matches": results})

    if matches:
        lines = [f"📄 Found {len(matches)} file(s) for “{query}”:\n"]
        for item in matches:
            lines.append(f"• {item.get('file', '(no file)')}")
            # δείξε έως 6 αποσπάσματα ανά αρχείο (βάλ’ το [:3] αν το θες πιο σύντομο)
            for m in item.get("matches", [])[:6]:
                line_no = m.get("line", "?")
                snippet = (m.get("snippet") or "").strip()
                lines.append(f"  - line {line_no}: {snippet}")
            lines.append("")  # κενή γραμμή μεταξύ αρχείων

        lines.append(f"🔎 See matching PDFs: https://mipengine-melina.onrender.com/pretty_pdf/{quote(query)}")
        text = "\n".join(lines)
        return jsonify({"message": text})

    # no matches
    return jsonify({
        "message": f"❌ No matches found for “{query}”.\n\n👉 Try the PDF Finder:\nhttps://mipengine-melina.onrender.com/pretty_pdf"
    })
# ---------------------------------------------------

@app.route('/pretty_pdf', methods=['GET', 'POST'])
def pretty_pdf_search_form():
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if query:
            return redirect(f'/pretty_pdf/{quote(query)}')

    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Search PDF Forms</title>
            <style>
                body { font-family: Arial; background-color: #f4f4f4; padding: 2rem; }
                h1 { color: #333; }
                form {
                    background: white;
                    padding: 1rem;
                    border-radius: 8px;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
                    max-width: 500px;
                    margin: auto;
                }
                input[type="text"] {
                    width: 100%;
                    padding: 0.5rem;
                    margin-bottom: 1rem;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }
                input[type="submit"] {
                    background-color: #007BFF;
                    color: white;
                    border: none;
                    padding: 0.5rem 1rem;
                    border-radius: 4px;
                    cursor: pointer;
                }
                input[type="submit"]:hover {
                    background-color: #0056b3;
                }
            </style>
        </head>
        <body>
            <h1>🔍 Search Migration PDF Forms</h1>
            <form method="POST">
                <input type="text" name="query" placeholder="e.g. visa, domestic worker, employer liability" />
                <input type="submit" value="Search" />
            </form>
        </body>
        </html>
    ''')

@app.route('/pretty_pdf/<query>')
def pretty_pdf(query):
    q_norm = normalize_text(query)
    matched_files = []

    for filename in os.listdir(PDF_FOLDER):
        if not filename.endswith('.pdf'):
            continue

        name_norm = normalize_text(filename)

        if any(fuzz.partial_ratio(word, name_norm) >= 70 for word in q_norm.split()):
            file_path = os.path.join(str(PDF_FOLDER), filename)
            size_bytes = os.path.getsize(file_path)
            mtime = os.path.getmtime(file_path)

            matched_files.append({
                "filename": filename,
                "url": f"/static/mip_pdfs/{filename}",
                "size": format_size(size_bytes),
                "modified": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                "modified_ts": mtime  # για ταξινόμηση με ακρίβεια
            })

    # ταξινόμηση: πιο πρόσφατα πρώτα
    matched_files.sort(key=lambda x: x["modified_ts"], reverse=True)

    if not matched_files:
        return render_template_string('''
            <html>
            <head><title>No PDFs Found</title></head>
            <body style="font-family: Arial; padding: 2rem;">
                <h2>❌ No matching PDF files found for "{{ query }}"</h2>
                <a href="/">⬅ Back to search</a>
            </body>
            </html>
        ''', query=query)

    return render_template_string('''
        <html>
        <head>
            <title>PDF Results</title>
            <style>
                body { font-family: Arial; padding: 2rem; background: #f9f9f9; }
                h2 { color: #333; }
                ul { list-style: none; padding: 0; }
                li {
                    background: white;
                    padding: 0.8rem 1rem;
                    margin-bottom: 0.7rem;
                    border-radius: 8px;
                    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
                }
                a { font-weight: bold; color: #007BFF; text-decoration: none; }
                a:hover { text-decoration: underline; }
                .meta { color: #666; font-size: 0.9rem; margin-left: 8px; }
                .modified { color: #999; font-size: 0.85rem; font-style: italic; margin-left: 6px; }
            </style>
        </head>
        <body>
            <h2>📂 Matching PDFs for "{{ query }}"</h2>
            <ul>
            {% for file in matched_files %}
                <li>
                  <a href="{{ file.url }}" target="_blank">{{ file.filename }}</a>
                  <span class="meta">{{ file.size }}</span>
                  <span class="modified">{{ file.modified }}</span>
                </li>
            {% endfor %}
            </ul>
            <a href="/">⬅ Back to search</a>
        </body>
        </html>
    ''', query=query, matched_files=matched_files)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)