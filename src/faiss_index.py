"""FAISS ANN index with a clearly-marked sklearn fallback.

FAISS (IndexFlatIP over L2-normalized embeddings) is the PRIMARY engine.
If faiss-cpu cannot be imported on this machine, a sklearn
NearestNeighbors (cosine) fallback keeps the project working. The active
engine is always exposed via `ANNIndex.engine` so the UI can display it.
"""

import numpy as np

from src import config

try:
    import faiss

    FAISS_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on machine
    FAISS_AVAILABLE = False


class ANNIndex:
    """Approximate/exact nearest-neighbour index over item embeddings."""

    def __init__(self, embeddings: np.ndarray = None, item_ids: np.ndarray = None,
                 index=None):
        self.engine = "faiss" if FAISS_AVAILABLE else "sklearn"
        self._sklearn_index = None
        self._faiss_index = index
        if embeddings is not None:
            self.build(embeddings, item_ids)

    # ------------------------------------------------------------ build
    def build(self, embeddings: np.ndarray, item_ids: np.ndarray) -> None:
        embeddings = np.ascontiguousarray(embeddings, dtype="float32")
        self.item_ids = np.asarray(item_ids)
        if FAISS_AVAILABLE:
            dim = embeddings.shape[1]
            self._faiss_index = faiss.IndexFlatIP(dim)  # inner product == cosine
            self._faiss_index.add(embeddings)
        else:
            from sklearn.neighbors import NearestNeighbors

            self._sklearn_index = NearestNeighbors(
                n_neighbors=min(200, len(embeddings)), metric="cosine"
            ).fit(embeddings)

    # ------------------------------------------------------------ persist
    def save(self, path=None) -> None:
        path = str(path or config.FAISS_INDEX_PATH)
        if FAISS_AVAILABLE:
            faiss.write_index(self._faiss_index, path)

    @classmethod
    def load(cls, path=None, item_ids: np.ndarray = None) -> "ANNIndex":
        path = str(path or config.FAISS_INDEX_PATH)
        obj = cls()
        obj.item_ids = np.asarray(item_ids)
        if FAISS_AVAILABLE:
            obj._faiss_index = faiss.read_index(path)
        else:
            # Without faiss we rebuild nothing here; the recommender
            # reconstructs the sklearn fallback from saved embeddings.
            obj._sklearn_index = None
        return obj

    # ------------------------------------------------------------ search
    def search(self, query_vectors: np.ndarray, k: int):
        """Return (indices, scores) of top-k items for each query row."""
        query_vectors = np.ascontiguousarray(query_vectors, dtype="float32")
        if FAISS_AVAILABLE:
            scores, idx = self._faiss_index.search(query_vectors, k)
            return idx, scores
        # sklearn fallback: cosine distance -> similarity = 1 - distance
        dist, idx = self._sklearn_index.kneighbors(query_vectors, n_neighbors=k)
        return idx, 1.0 - dist

    @property
    def size(self) -> int:
        if FAISS_AVAILABLE and self._faiss_index is not None:
            return self._faiss_index.ntotal
        if self._sklearn_index is not None:
            return self._sklearn_index.n_samples_fit_
        return 0
