from __future__ import annotations
import faiss
import numpy as np

class FaissIndex:
    def __init__(self, dim: int):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)  # dot == cosine (при L2-норме)
        self.ids: list[int] = []

    def add_one(self, vec: np.ndarray, doc_id: int):
        self.index.add(vec.reshape(1, -1))
        self.ids.append(doc_id)

    def add_batch(self, vecs: np.ndarray, ids: list[int]):
        self.index.add(vecs)
        self.ids.extend(ids)

    def search(self, vec: np.ndarray, k: int = 30) -> list[tuple[int, float]]:
        D, I = self.index.search(vec.reshape(1, -1), k)
        sims = D[0].tolist(); idxs = I[0].tolist()
        out = []
        for sim, idx in zip(sims, idxs):
            if idx == -1: continue
            out.append((self.ids[idx], float(sim)))
        return out

    def size(self) -> int:
        return len(self.ids)