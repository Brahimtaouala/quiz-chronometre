"""Serveur local : sert index.html et partage questions.json / scores_python.json
avec le quiz web. Aucune installation nécessaire (bibliothèque standard uniquement).

Lancer :  python server.py     puis ouvrir  http://localhost:8000
"""
import json
import pathlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE = pathlib.Path(__file__).resolve().parent
QUESTIONS = BASE / 'questions.json'
SCORES = BASE / 'scores_python.json'   # même fichier que quiz.py (Tkinter)
PORT = 8000


def read_json(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError):
        return []
    return data if isinstance(data, list) else []


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE), **kwargs)

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/api/questions':
            self.send_json(read_json(QUESTIONS))
        elif self.path == '/api/scores':
            self.send_json(read_json(SCORES))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path != '/api/scores':
            self.send_json({'error': 'introuvable'}, 404)
            return
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length > 10_000:
                raise ValueError('requête trop grande')
            new = json.loads(self.rfile.read(length).decode('utf-8'))
            clean = [{'name': str(p['name']).strip()[:20] or 'Joueur', 'score': int(p['score'])}
                     for p in new]
        except (ValueError, KeyError, TypeError):
            self.send_json({'error': 'données invalides'}, 400)
            return
        scores = read_json(SCORES) + clean
        SCORES.write_text(json.dumps(scores, ensure_ascii=False, indent=2), encoding='utf-8')
        self.send_json({'ok': True})


if __name__ == '__main__':
    print(f'Quiz web : http://localhost:{PORT}  (Ctrl+C pour arrêter)')
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
