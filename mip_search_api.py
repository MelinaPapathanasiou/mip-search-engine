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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
