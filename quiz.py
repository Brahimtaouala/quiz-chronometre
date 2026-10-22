import tkinter as tk
from tkinter import messagebox
import json, random, pathlib

BASE = pathlib.Path(__file__).resolve().parent
SCORES = BASE / 'scores_python.json'
BG = '#eef2f8'


def load_questions():
    """Charge et valide questions.json (évite les plantages si le fichier est absent ou mal formé)."""
    try:
        data = json.loads((BASE / 'questions.json').read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError) as e:
        messagebox.showerror('Erreur', f'Impossible de lire questions.json :\n{e}')
        return []
    valid = []
    for q in data:
        try:
            if (isinstance(q['question'], str) and q['category']
                    and isinstance(q['options'], list) and len(q['options']) >= 2
                    and 0 <= q['answer'] < len(q['options'])):
                valid.append(q)
        except (KeyError, TypeError):
            continue
    return valid


class QuizApp:
    def __init__(self, root):
        self.root = root
        root.title('Quiz chronométré multijoueur - Python')
        root.geometry('760x720')
        root.configure(bg=BG)
        root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.questions = load_questions()
        self.players = []
        self.pool = []
        self.turn = 0
        self.timer_id = None
        self.build_setup()

    # ---------- utilitaires ----------
    def on_close(self):
        self.stop_timer()
        self.root.destroy()

    def stop_timer(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

    def clear(self):
        self.stop_timer()
        for widget in self.root.winfo_children():
            widget.destroy()

    def label(self, text, size=14, **kwargs):
        return tk.Label(self.root, text=text, font=('Arial', size), bg=BG, **kwargs)

    # ---------- écran de configuration ----------
    def build_setup(self):
        self.clear()
        self.label('QUIZ CHRONOMÉTRÉ MULTIJOUEUR', 22, fg='#183153').pack(pady=25)
        self.label('Nombre de joueurs (2 à 4)').pack()
        self.count = tk.IntVar(value=2)
        tk.Spinbox(self.root, from_=2, to=4, textvariable=self.count, width=5,
                   state='readonly').pack(pady=7)
        self.entries = []
        for i in range(4):
            entry = tk.Entry(self.root, width=30)
            entry.insert(0, f'Joueur {i + 1}')
            entry.pack(pady=5)
            self.entries.append(entry)
        self.label('Catégorie').pack(pady=(15, 0))
        self.category = tk.StringVar(value='Toutes')
        categories = sorted({q['category'] for q in self.questions})
        tk.OptionMenu(self.root, self.category, 'Toutes', *categories).pack()
        tk.Button(self.root, text='COMMENCER', bg='#267d40', fg='white',
                  font=('Arial', 15, 'bold'), command=self.start).pack(pady=18)
        tk.Button(self.root, text='Classement sauvegardé', command=self.show_scores).pack()

    def start(self):
        try:
            n = int(self.count.get())
        except (ValueError, tk.TclError):
            n = 2
        n = min(4, max(2, n))
        self.players = [{'name': self.entries[i].get().strip() or f'Joueur {i + 1}',
                         'score': 0, 'fifty': True, 'pass': True} for i in range(n)]
        self.pool = [q for q in self.questions
                     if self.category.get() == 'Toutes' or q['category'] == self.category.get()]
        if not self.pool:
            messagebox.showwarning('Aucune question', 'Aucune question disponible pour cette catégorie.')
            return
        random.shuffle(self.pool)
        self.turn = 0
        self.ask()

    # ---------- déroulement ----------
    def ask(self):
        if self.turn >= len(self.pool):
            self.finish()
            return
        self.clear()
        self.question = self.pool[self.turn]
        self.player = self.players[self.turn % len(self.players)]
        self.answered = False
        self.label(f"Question {self.turn + 1}/{len(self.pool)}   |   {self.player['name']}   |   "
                   f"Score : {self.player['score']}", 15, fg='#183153').pack(pady=15)
        self.time_left = 15
        self.clock = self.label('', 16, fg='#bc302c')
        self.clock.pack()
        self.label(self.question['question'], 17, fg='#183153', wraplength=700).pack(pady=20)
        self.buttons = []
        for i, choice in enumerate(self.question['options']):
            btn = tk.Button(self.root, text=f'{chr(65 + i)}. {choice}', width=47,
                            font=('Arial', 12), command=lambda j=i: self.answer(j))
            btn.pack(pady=5)
            self.buttons.append(btn)
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(pady=12)
        self.fifty_btn = tk.Button(bar, text='50/50', command=self.fifty,
                                   state='normal' if self.player['fifty'] and len(self.buttons) > 2 else 'disabled')
        self.fifty_btn.pack(side='left', padx=10)
        self.pass_btn = tk.Button(bar, text='Passer', command=self.pass_question,
                                  state='normal' if self.player['pass'] else 'disabled')
        self.pass_btn.pack(side='left', padx=10)
        self.label('Bonne réponse : +10 points | Mauvaise réponse : 0 point', 10).pack()
        # zone dédiée au message de résultat et au bouton « suivante »
        self.result_frame = tk.Frame(self.root, bg=BG)
        self.result_frame.pack(pady=5)
        self.tick()

    def tick(self):
        self.timer_id = None
        self.clock.config(text=f'Temps restant : {self.time_left} s')
        if self.time_left <= 0:
            self.answer(None)
        else:
            self.time_left -= 1
            self.timer_id = self.root.after(1000, self.tick)

    def fifty(self):
        if not self.player['fifty'] or self.answered:
            return
        self.player['fifty'] = False
        self.fifty_btn.config(state='disabled')
        wrong = [i for i in range(len(self.buttons)) if i != self.question['answer']]
        for i in random.sample(wrong, min(2, len(wrong))):
            self.buttons[i].config(state='disabled')

    def pass_question(self):
        if not self.player['pass'] or self.answered:
            return
        self.player['pass'] = False
        self.answer(None, passed=True)

    def answer(self, choice, passed=False):
        if self.answered:
            return
        self.answered = True
        self.stop_timer()
        correct = choice is not None and choice == self.question['answer']
        if correct:
            self.player['score'] += 10
        for i, btn in enumerate(self.buttons):
            btn.config(state='disabled')
            if i == self.question['answer']:
                btn.config(bg='#6dbf7d')
            elif i == choice:
                btn.config(bg='#ed8989')
        self.fifty_btn.config(state='disabled')
        self.pass_btn.config(state='disabled')
        if correct:
            msg = 'Bonne réponse ! +10'
        elif passed:
            msg = 'Question passée'
        elif choice is None:
            msg = 'Temps écoulé !'
        else:
            msg = 'Mauvaise réponse'
        tk.Label(self.result_frame, text=msg, font=('Arial', 13), bg=BG,
                 fg='#267d40' if correct else '#bc302c').pack()
        is_last = self.turn + 1 >= len(self.pool)
        tk.Button(self.result_frame, text='Voir le classement →' if is_last else 'Question suivante →',
                  command=self.next_question).pack(pady=8)

    def next_question(self):
        self.turn += 1
        self.ask()

    # ---------- fin de partie et scores ----------
    def finish(self):
        self.clear()
        ranking = sorted(self.players, key=lambda p: p['score'], reverse=True)
        self.label('CLASSEMENT FINAL', 23, fg='#183153').pack(pady=24)
        for i, p in enumerate(ranking):
            self.label(f"{i + 1}. {p['name']} — {p['score']} points", 16).pack(pady=8)
        scores = self.load_scores()
        scores.extend({'name': p['name'], 'score': p['score']} for p in self.players)
        try:
            SCORES.write_text(json.dumps(scores, ensure_ascii=False, indent=2), encoding='utf-8')
        except OSError as e:
            messagebox.showwarning('Sauvegarde impossible', f'Les scores n\'ont pas pu être enregistrés :\n{e}')
        tk.Button(self.root, text='Nouvelle partie', command=self.build_setup).pack(pady=25)

    def load_scores(self):
        try:
            data = json.loads(SCORES.read_text(encoding='utf-8'))
        except (FileNotFoundError, ValueError):
            return []
        if not isinstance(data, list):
            return []
        return [p for p in data if isinstance(p, dict) and 'name' in p and 'score' in p]

    def show_scores(self):
        scores = sorted(self.load_scores(), key=lambda p: p['score'], reverse=True)[:10]
        text = '\n'.join(f"{i + 1}. {p['name']} : {p['score']}" for i, p in enumerate(scores))
        messagebox.showinfo('Top 10 (sauvegardé)', text or 'Aucun score')


if __name__ == '__main__':
    root = tk.Tk()
    QuizApp(root)
    root.mainloop()
