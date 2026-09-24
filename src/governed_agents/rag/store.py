"""A deliberately boring retriever.

Lexical scoring over chunked markdown, no embedding service. The governance
behaviour this repo demonstrates is identical whichever retriever sits here, and
a dependency-free store means the tests and the eval suite run on a laptop with
no API key. Swap in a real vector store by replacing `search` and keeping the
`{"id", "text", "source"}` contract that the groundedness scorer relies on.
"""
import os
import re
from typing import Dict, List

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> List[str]:
    return _WORD.findall(text.lower())


class DocumentStore:
    def __init__(self, directory: str):
        self.chunks: List[Dict[str, str]] = []
        self._load(directory)

    def _load(self, directory: str) -> None:
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".md"):
                continue
            path = os.path.join(directory, name)
            with open(path, "r", encoding="utf-8") as handle:
                raw = handle.read()
            # One chunk per section keeps citations legible to a human reviewer,
            # which matters more here than packing an embedding window.
            for index, section in enumerate(s for s in raw.split("\n## ") if s.strip()):
                self.chunks.append(
                    {
                        "id": "%s#%d" % (name[:-3], index),
                        "text": section.strip(),
                        "source": name,
                    }
                )

    def search(self, query: str, k: int = 4) -> List[Dict[str, str]]:
        wanted = set(_tokens(query))
        if not wanted:
            return []
        scored = []
        for chunk in self.chunks:
            overlap = len(wanted & set(_tokens(chunk["text"])))
            if overlap:
                scored.append((overlap, chunk))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
        return [chunk for _, chunk in scored[:k]]
