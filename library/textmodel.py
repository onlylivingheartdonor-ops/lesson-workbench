"""Small, dependency-free text tools for subject tagging: tokenizing, a light
stemmer, and sparse TF-IDF vectors with cosine similarity."""

import math
import re
from collections import Counter

STOP = set("""
a about above after again against all also am an and any are as at be because been before being below between
both but by can could did do does doing down during each either else even ever every few for from further had
has have having he her here hers herself him himself his how i if in into is it its itself just let like may
me might more most much must my myself neither no nor not now o of off on once only or other ought our ours
ourselves out over own same say said says shall she should so some such than that the their theirs them
themselves then there these they this those thou thee thy thine through to too under until unto up upon us
very was we were what when where whether which while who whom whose why will with within without would ye
yet you your yours yourself yourselves hath doth art wilt shalt hast didst one two three first also
verse verses chapter chap ver see compare comp viz ii iii iv vi vii viii ix xi xii etc thus therefore
hence whereby wherein thereof thereby therein made make many great us our god lord
""".split())
# 'god' and 'lord' are so frequent in every work that they carry no topical signal.

_WORD = re.compile(r"[a-z]+")


def stem(w):
    if len(w) <= 3:
        return w
    for suf, rep in (("iness", "y"), ("fulness", "ful"), ("ousness", "ous"), ("iveness", "ive"), ("ness", ""),
                     ("ational", "ate"), ("ations", "ate"), ("ation", "ate"), ("ments", ""), ("ment", ""),
                     ("ities", "ity"), ("ies", "y"), ("sses", "ss"), ("ings", ""), ("ing", ""), ("edly", ""),
                     ("ed", ""), ("ly", ""), ("es", ""), ("s", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            if suf == "s" and w.endswith("ss"):
                break
            w = w[: len(w) - len(suf)] + rep
            break
    if w.endswith("e") and len(w) > 4:
        w = w[:-1]
    return w


def tokens(text):
    return [stem(w) for w in _WORD.findall(text.lower()) if w not in STOP and len(w) > 2]


class TfIdf:
    def __init__(self):
        self.df = Counter()
        self.n_docs = 0

    def fit(self, token_lists):
        for toks in token_lists:
            self.n_docs += 1
            self.df.update(set(toks))

    def idf(self, t):
        return math.log((1 + self.n_docs) / (1 + self.df.get(t, 0))) + 1.0

    def vector(self, toks, top=None, min_df=2):
        tf = Counter(toks)
        vec = {}
        for t, c in tf.items():
            if self.df.get(t, 0) < min_df:
                continue
            vec[t] = (1 + math.log(c)) * self.idf(t)
        if top and len(vec) > top:
            vec = dict(sorted(vec.items(), key=lambda kv: -kv[1])[:top])
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}


def build_postings(vectors):
    """vectors: {doc_id: {term: weight}} -> {term: [(doc_id, weight)]}"""
    post = {}
    for did, vec in vectors.items():
        for t, w in vec.items():
            post.setdefault(t, []).append((did, w))
    return post


def cosine_top(vec, postings, k=10):
    scores = Counter()
    for t, w in vec.items():
        for did, w2 in postings.get(t, ()):
            scores[did] += w * w2
    return scores.most_common(k)
