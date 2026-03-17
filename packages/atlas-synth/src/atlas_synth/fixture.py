from __future__ import annotations

from dataclasses import dataclass, field
from difflib import unified_diff
from json import dumps

from atlas_synth.builder import build_canonical_world
from atlas_synth.models import SyntheticWorldSnapshot


def clone_snapshot(snapshot: SyntheticWorldSnapshot) -> SyntheticWorldSnapshot:
    return SyntheticWorldSnapshot.model_validate(snapshot.model_dump(mode="python"))


def snapshot_document(snapshot: SyntheticWorldSnapshot) -> dict[str, object]:
    return snapshot.model_dump(mode="json")


def render_snapshot_diff(
    before: SyntheticWorldSnapshot,
    after: SyntheticWorldSnapshot,
) -> str:
    before_lines = dumps(snapshot_document(before), indent=2, sort_keys=True).splitlines()
    after_lines = dumps(snapshot_document(after), indent=2, sort_keys=True).splitlines()
    return "\n".join(
        unified_diff(
            before_lines,
            after_lines,
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )


@dataclass
class CanonicalFixtureSession:
    seed: str
    baseline_snapshot: SyntheticWorldSnapshot = field(init=False)
    current_snapshot: SyntheticWorldSnapshot = field(init=False)

    def __post_init__(self) -> None:
        baseline = build_canonical_world(self.seed)
        self.baseline_snapshot = clone_snapshot(baseline)
        self.current_snapshot = clone_snapshot(baseline)

    @classmethod
    def load(cls, seed: str) -> "CanonicalFixtureSession":
        return cls(seed=seed)

    def reset(self) -> SyntheticWorldSnapshot:
        self.current_snapshot = clone_snapshot(self.baseline_snapshot)
        return clone_snapshot(self.current_snapshot)

    def rehydrate(self) -> SyntheticWorldSnapshot:
        rebuilt = build_canonical_world(self.seed)
        self.baseline_snapshot = clone_snapshot(rebuilt)
        self.current_snapshot = clone_snapshot(rebuilt)
        return clone_snapshot(self.current_snapshot)

    def snapshot(self) -> SyntheticWorldSnapshot:
        return clone_snapshot(self.current_snapshot)

    def replace_current(self, snapshot: SyntheticWorldSnapshot) -> SyntheticWorldSnapshot:
        self.current_snapshot = clone_snapshot(snapshot)
        return self.snapshot()

    def diff_from_baseline(self) -> str:
        return render_snapshot_diff(self.baseline_snapshot, self.current_snapshot)
