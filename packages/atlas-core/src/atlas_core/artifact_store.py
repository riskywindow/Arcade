from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True)
class StoredArtifact:
    path: Path
    sha256_hex: str
    size_bytes: int


class LocalArtifactStore:
    def __init__(self, root_dir: str | Path) -> None:
        self._root_dir = Path(root_dir)
        self._root_dir.mkdir(parents=True, exist_ok=True)

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    def save_bytes(
        self,
        *,
        run_id: str,
        artifact_id: str,
        filename: str,
        content: bytes,
    ) -> StoredArtifact:
        run_dir = self._root_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / f"{artifact_id}-{filename}"
        path.write_bytes(content)
        digest = sha256(content).hexdigest()
        return StoredArtifact(
            path=path,
            sha256_hex=digest,
            size_bytes=len(content),
        )
