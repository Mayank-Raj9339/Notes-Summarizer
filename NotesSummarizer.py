"""
Note Summarizer - paste study material, get a clickable flowchart.
Click a box in the flowchart to expand it into point-wise and sub-point-wise notes.
Pure Python 3 (standard library only). Run:  python note_summarizer.py
"""
import re
import math
from collections import Counter
 
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:  # lets analyze() be imported/tested without a display
    tk = None
 
# ----------------------------------------------------------------- NLP part
STOP = set("""a about above after again all also am an and any are as at be because been before being
below between both but by can could did do does doing down during each few for from further had has have
having he her here hers him his how i if in into is it its itself just me more most my no nor not of off on
once only or other our out over own same she should so some such than that the their them then there these
they this those through to too under until up very was we were what when where which while who whom why
will with would you your yours may might also many much""".split())
CUES = re.compile(r"\b(is defined as|refers to|is called|is known as|means|consists of|is a|are a|"
                  r"important|key|main|essential|because|therefore|results? in|leads? to)\b", re.I)
 
 
def tokens(s):
    return [w for w in re.findall(r"[a-zA-Z][a-zA-Z\-']+", s.lower()) if w not in STOP and len(w) > 2]
 
 
def split_sentences(block):
    block = re.sub(r"\s+", " ", block.strip())
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", block)
    return [p.strip() for p in parts if len(p.split()) >= 4]
 
 
def shorten(s, n):
    s = s.strip().rstrip(".")
    if len(s) <= n:
        return s
    return s[:n].rsplit(" ", 1)[0] + "…"
 
 
def clauses(s):
    parts = re.split(r"\s*[;:]\s*|,\s+(?:which|while|whereas|because|but|so|and)\s+|\s+such as\s+", s)
    out = [p.strip(" ,.") for p in parts if len(p.split()) >= 3]
    return [p[0].upper() + p[1:] for p in out]
 
 
def chunk(sents):
    n = len(sents)
    k = max(1, round(n / 4)) if n >= 8 else 1
    size = math.ceil(n / k)
    return [sents[i:i + size] for i in range(0, n, size)]
 
 
def analyze(text):
    """Return (overview_keywords, topics). topic = {title, points:[(point, [subpoints])]}"""
    paras = [s for s in (split_sentences(b) for b in re.split(r"\n+", text.strip())) if s]
    allsents = [s for p in paras for s in p]
    if not allsents:
        return [], []
    freq = Counter(w for s in allsents for w in tokens(s))
    mx = max(freq.values())
 
    def score(s, first=False):
        ws = set(tokens(s))
        if not ws:
            return 0
        v = sum(freq[w] / mx for w in ws) / len(ws) ** 0.6
        return v * (1.25 if first else 1) * (1.2 if CUES.search(s) else 1)
 
    groups = []
    for p in paras:                      # merge one-liners into the previous paragraph
        if groups and len(p) < 2:
            groups[-1] += p
        else:
            groups.append(p)
    final = []
    for g in groups:
        final += chunk(g) if (len(g) > 9 or len(groups) == 1) else [g]
 
    topics = []
    for g in final:
        local = Counter(w for s in g for w in tokens(s))
        first = set(tokens(g[0]))
        kw = sorted(local, key=lambda w: (-(local[w] * (1.5 if w in first else 1)), w))[:3]
        n_key = min(3, max(1, round(len(g) / 3)))
        idx = sorted(sorted(range(len(g)), key=lambda i: -score(g[i], i == 0))[:n_key])
        points = []
        for j, i in enumerate(idx):
            end = idx[j + 1] if j + 1 < len(idx) else len(g)
            support = (g[:i] if j == 0 else []) + g[i + 1:end]
            subs = [shorten(x, 130) for x in support][:4]
            if not subs:
                c = clauses(g[i])
                subs = [shorten(x, 110) for x in c[:3]] if len(c) >= 2 else []
            points.append((shorten(g[i], 170), subs))
        topics.append({"title": " · ".join(w.title() for w in kw) or "Topic", "points": points})
    overview = [w.title() for w, _ in freq.most_common(4)]
    return overview, topics
 
 
def notes_as_text(topics):
    lines = []
    for n, t in enumerate(topics, 1):
        lines.append(f"{n}. {t['title']}")
        for p, subs in t["points"]:
            lines.append(f"   • {p}")
            lines += [f"       – {s}" for s in subs]
        lines.append("")
    return "\n".join(lines)
 
 
# ----------------------------------------------------------------- GUI part
PALETTE = [("#E8F0FE", "#4285F4"), ("#E6F4EA", "#34A853"), ("#FEF7E0", "#F9AB00"),
           ("#FCE8E6", "#EA4335"), ("#F3E8FD", "#9334E6"), ("#E4F7FB", "#12B5CB")]
INK = "#1f2937"
SAMPLE = """Photosynthesis is the process by which green plants convert light energy into chemical energy stored in glucose. It takes place mainly in the chloroplasts of leaf cells, which contain the green pigment chlorophyll. Chlorophyll absorbs light mostly in the red and blue wavelengths, which is why leaves look green. The overall reaction needs carbon dioxide, water and sunlight, and it releases oxygen as a by-product.
The light-dependent reactions occur in the thylakoid membranes of the chloroplast. Here, light energy splits water molecules into hydrogen ions, electrons and oxygen. The electrons move along an electron transport chain, which pumps protons and drives the production of ATP and NADPH. These two molecules carry the energy needed for the next stage.
The Calvin cycle takes place in the stroma of the chloroplast and does not need light directly. Carbon dioxide is fixed by the enzyme RuBisCO onto a five-carbon sugar called RuBP. Using ATP and NADPH, the fixed carbon is reduced to form G3P, a three-carbon sugar. Some G3P is used to regenerate RuBP so the cycle can continue, while the rest builds glucose and other carbohydrates.
Several factors limit the rate of photosynthesis, including light intensity, carbon dioxide concentration and temperature. At low light the rate rises with intensity, but it levels off once another factor becomes limiting. Very high temperatures denature enzymes such as RuBisCO and sharply reduce the rate."""
 
 
class App:
    def __init__(self, root):
        self.root, self.topics, self.open, self.w = root, [], set(), 0
        root.title("Note Summarizer - Flowchart Notes")
        root.geometry("1150x700")
        pw = ttk.PanedWindow(root, orient="horizontal")
        pw.pack(fill="both", expand=True)
 
        left = ttk.Frame(pw, padding=8)
        ttk.Label(left, text="Paste your study material", font=("Helvetica", 12, "bold")).pack(anchor="w")
        box = ttk.Frame(left); box.pack(fill="both", expand=True, pady=6)
        self.inp = tk.Text(box, wrap="word", font=("Helvetica", 11), undo=True)
        sb = ttk.Scrollbar(box, command=self.inp.yview); self.inp.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); self.inp.pack(fill="both", expand=True)
        bar = ttk.Frame(left); bar.pack(fill="x")
        ttk.Button(bar, text="Summarize ▶", command=self.run).pack(side="left")
        ttk.Button(bar, text="Sample", command=self.sample).pack(side="left", padx=4)
        ttk.Button(bar, text="Clear", command=lambda: self.inp.delete("1.0", "end")).pack(side="left")
        pw.add(left, weight=1)
 
        right = ttk.Frame(pw, padding=8)
        bar2 = ttk.Frame(right); bar2.pack(fill="x")
        ttk.Label(bar2, text="Flowchart (click a box to expand)", font=("Helvetica", 12, "bold")).pack(side="left")
        ttk.Button(bar2, text="Export notes", command=self.export).pack(side="right")
        ttk.Button(bar2, text="Collapse all", command=self.collapse).pack(side="right", padx=4)
        ttk.Button(bar2, text="Expand all", command=self.expand).pack(side="right")
        cf = ttk.Frame(right); cf.pack(fill="both", expand=True, pady=6)
        self.cv = tk.Canvas(cf, bg="white", highlightthickness=1, highlightbackground="#ddd")
        vs = ttk.Scrollbar(cf, command=self.cv.yview); self.cv.config(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y"); self.cv.pack(fill="both", expand=True)
        pw.add(right, weight=2)
 
        self.cv.bind("<Configure>", self.on_resize)
        root.bind_all("<MouseWheel>", lambda e: self.cv.yview_scroll(-1 * (e.delta // 120 or (1 if e.delta > 0 else -1)), "units"))
        root.bind_all("<Button-4>", lambda e: self.cv.yview_scroll(-2, "units"))
        root.bind_all("<Button-5>", lambda e: self.cv.yview_scroll(2, "units"))
        self.sample()
 
    def sample(self):
        self.inp.delete("1.0", "end"); self.inp.insert("1.0", SAMPLE); self.run()
 
    def run(self):
        text = self.inp.get("1.0", "end").strip()
        if len(text.split()) < 15:
            messagebox.showinfo("Too short", "Please paste a few sentences (at least ~15 words).")
            return
        self.overview, self.topics = analyze(text)
        self.open = set(); self.draw()
 
    def expand(self): self.open = set(range(len(self.topics))); self.draw()
    def collapse(self): self.open = set(); self.draw()
 
    def toggle(self, i):
        self.open ^= {i}
        self.draw()
 
    def on_resize(self, e):
        if abs(e.width - self.w) > 5:
            self.w = e.width
            self.draw()
 
    def export(self):
        if not self.topics:
            return
        f = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if f:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(notes_as_text(self.topics))
 
    # ---- drawing
    def arrow(self, cx, y):
        self.cv.create_line(cx, y, cx, y + 28, arrow="last", width=2, fill="#9aa0a6")
        return y + 28
 
    def terminal(self, cx, y, label):
        self.cv.create_oval(cx - 70, y, cx + 70, y + 34, fill="#202124", outline="")
        self.cv.create_text(cx, y + 17, text=label, fill="white", font=("Helvetica", 10, "bold"))
        return y + 34
 
    def draw(self):
        c = self.cv
        top = c.canvasy(0)
        c.delete("all")
        if not self.topics:
            return
        W = max(c.winfo_width(), 480); cx = W // 2; bw = min(W - 60, 640); x0 = cx - bw // 2
        y = self.terminal(cx, 16, "START: " + ", ".join(self.overview[:3]).upper()[:40])
        for i, t in enumerate(self.topics):
            y = self.arrow(cx, y)
            fill, edge = PALETTE[i % len(PALETTE)]
            tag, yy = f"n{i}", y + 10
            exp = i in self.open
            head = c.create_text(x0 + 14, yy, anchor="nw", width=bw - 28, fill=INK, tags=tag,
                                 font=("Helvetica", 12, "bold"),
                                 text=f"{i + 1}. {t['title']}   {'▼' if exp else '▶'}")
            yy = c.bbox(head)[3] + 4
            if exp:
                for p, subs in t["points"]:
                    for txt, ind, fnt in [("•  " + p, 14, ("Helvetica", 11, "bold"))] + \
                                         [("–  " + s, 38, ("Helvetica", 10)) for s in subs]:
                        it = c.create_text(x0 + ind, yy, anchor="nw", width=bw - ind - 14,
                                           text=txt, fill=INK, font=fnt, tags=tag)
                        yy = c.bbox(it)[3] + 4
                    yy += 4
            else:
                n = sum(1 + len(s) for _, s in t["points"])
                it = c.create_text(x0 + 14, yy, anchor="nw", fill="#5f6368", tags=tag,
                                   font=("Helvetica", 9), text=f"{len(t['points'])} key points, {n - len(t['points'])} sub-points · click to expand")
                yy = c.bbox(it)[3] + 2
            r = c.create_rectangle(x0, y, x0 + bw, yy + 10, fill=fill, outline=edge, width=2, tags=tag)
            c.tag_lower(r)
            c.tag_bind(tag, "<Button-1>", lambda e, i=i: self.toggle(i))
            c.tag_bind(tag, "<Enter>", lambda e: c.config(cursor="hand2"))
            c.tag_bind(tag, "<Leave>", lambda e: c.config(cursor=""))
            y = yy + 10
        y = self.arrow(cx, y)
        y = self.terminal(cx, y, "END")
        c.config(scrollregion=(0, 0, W, y + 30))
        c.yview_moveto(top / (y + 30))
 
 
if __name__ == "__main__":
    if tk is None:
        raise SystemExit("tkinter is missing. Install it (Linux: sudo apt install python3-tk).")
    root = tk.Tk()
    App(root)
    root.mainloop()
