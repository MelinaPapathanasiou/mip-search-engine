import os
import json
from pathlib import Path
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

TEXT_FOLDER = Path("mip_texts")

def search_keyword_in_file(file_path, keyword):
    keyword = keyword.lower()
    results = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        lines = file.readlines()
        for idx, line in enumerate(lines):
            if keyword in line.lower():
                context = '... ' + line.strip()[:200] + ' ...'
                results.append({"line": idx + 1, "snippet": context})
    return results

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return Response(json.dumps({"error": "Missing query parameter 'q'"},
                                   ensure_ascii=False), mimetype='application/json', status=400)

    matches = []
    for txt_file in TEXT_FOLDER.glob("*.txt"):
        results = search_keyword_in_file(txt_file, query)
        if results:
            matches.append({
                "file": txt_file.name,
                "matches": results
            })

    return Response(json.dumps({"query": query, "results": matches},
                               ensure_ascii=False), mimetype='application/json')
from difflib import get_close_matches
PDF_FOLDER = Path("mip_pdfs")

@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    if not query:
        return Response(json.dumps({"error": "Missing 'q' parameter"}), mimetype='application/json', status=400)

    matches = []
    for txt_file in TEXT_FOLDER.glob("*.txt"):
        results = search_keyword_in_file(txt_file, query)
        if results:
            matches.append({"file": txt_file.name, "matches": results})

    return Response(json.dumps({"query": query, "results": matches}, ensure_ascii=False), mimetype='application/json')


@app.route("/api/get_pdf_link")
def api_get_pdf_link():
    query = request.args.get("q", "").strip().lower()
    if not query:
        return Response(json.dumps({"error": "Missing 'q' parameter"}), mimetype='application/json', status=400)

    pdf_files = [f.name for f in PDF_FOLDER.glob("*.pdf")]
    matches = get_close_matches(query, pdf_files, n=1, cutoff=0.3)

    if matches:
        filename = matches[0]
        link = f"https://mip-search-engine.onrender.com/get_pdf/{filename}"
        return Response(json.dumps({"query": query, "link": link}), mimetype='application/json')

    return Response(json.dumps({"query": query, "link": None, "message": "No matching PDF found."}), mimetype='application/json')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
