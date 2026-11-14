"""RepoDoc schema retained for compatibility with existing DocArray indexes."""

from typing import List, Optional

from docarray import BaseDoc
from docarray.typing import NdArray


class RepoDoc(BaseDoc):
    """Repository metadata and precomputed channel embeddings."""

    name: str
    topics: List[str]
    stars: int
    license: str
    code_embedding: Optional[NdArray[768]]
    doc_embedding: Optional[NdArray[768]]
    readme_embedding: Optional[NdArray[768]]
    requirement_embedding: Optional[NdArray[768]]
    repository_embedding: Optional[NdArray[3072]]
