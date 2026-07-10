"""Balanced Williams-style crossover sequence allocator.

For 3 conditions (A, B, C), the six balanced sequences are:

    ABC, BCA, CAB, CBA, ACB, BAC

These provide:
- Position balance: each condition appears equally in each period
- First-order carryover balance: each ordered pair AB, AC, BA, BC, CA, CB
  appears exactly once across the six sequences

The allocator selects the least-used sequence for each new participant,
using a deterministic tie-break from the study seed. Allocation is
persisted and immutable once committed.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from app.research.governance import AllocationIntegrityError
from app.schemas.research import FeedbackCondition
from app.storage.database import get_db

WILLIAMS_SEQUENCES: list[tuple[str, list[FeedbackCondition]]] = [
    ("ABC", [FeedbackCondition.ADAPTIVE, FeedbackCondition.FIXED, FeedbackCondition.YOKED]),
    ("BCA", [FeedbackCondition.FIXED, FeedbackCondition.YOKED, FeedbackCondition.ADAPTIVE]),
    ("CAB", [FeedbackCondition.YOKED, FeedbackCondition.ADAPTIVE, FeedbackCondition.FIXED]),
    ("CBA", [FeedbackCondition.YOKED, FeedbackCondition.FIXED, FeedbackCondition.ADAPTIVE]),
    ("ACB", [FeedbackCondition.ADAPTIVE, FeedbackCondition.YOKED, FeedbackCondition.FIXED]),
    ("BAC", [FeedbackCondition.FIXED, FeedbackCondition.ADAPTIVE, FeedbackCondition.YOKED]),
]


def _tie_break(study_seed: int, participant_id: str, seq_label: str) -> int:
    h = hashlib.sha256(f"{study_seed}:{participant_id}:{seq_label}".encode()).hexdigest()
    return int(h[:8], 16)


async def allocate_sequence(
    study_id: str,
    participant_id: str,
    study_seed: int,
) -> tuple[str, list[FeedbackCondition]]:
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")

        cursor = await db.execute(
            "SELECT allocation_id FROM sequence_allocations "
            "WHERE study_id = ? AND participant_id = ?",
            (study_id, participant_id),
        )
        existing = await cursor.fetchone()
        if existing:
            alloc_cursor = await db.execute(
                "SELECT sequence_id, sequence_label FROM sequence_allocations "
                "WHERE study_id = ? AND participant_id = ?",
                (study_id, participant_id),
            )
            row = await alloc_cursor.fetchone()
            seq_label = row["sequence_label"]
            for label, seq in WILLIAMS_SEQUENCES:
                if label == seq_label:
                    await db.commit()
                    return label, seq
            await db.commit()
            valid_labels = [lbl for lbl, _ in WILLIAMS_SEQUENCES]
            raise AllocationIntegrityError(
                f"Persisted sequence label '{seq_label}' is not in the allowed set {valid_labels}. "
                "This indicates data corruption — refusing to substitute silently."
            )

        count_cursor = await db.execute(
            "SELECT sequence_label, COUNT(*) as cnt FROM sequence_allocations "
            "WHERE study_id = ? GROUP BY sequence_label",
            (study_id,),
        )
        counts: dict[str, int] = {}
        for row in await count_cursor.fetchall():
            counts[row["sequence_label"]] = row["cnt"]

        min_count = min((counts.get(label, 0) for label, _ in WILLIAMS_SEQUENCES), default=0)
        candidates = [
            (label, seq) for label, seq in WILLIAMS_SEQUENCES
            if counts.get(label, 0) == min_count
        ]

        candidates.sort(key=lambda x: _tie_break(study_seed, participant_id, x[0]))
        chosen_label, chosen_seq = candidates[0]

        tie_val = _tie_break(study_seed, participant_id, chosen_label)
        allocation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.execute(
            "INSERT INTO sequence_allocations "
            "(allocation_id, study_id, participant_id, sequence_id, sequence_label, "
            "study_seed, tie_break_value, allocated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                allocation_id, study_id, participant_id,
                chosen_label, chosen_label,
                study_seed, tie_val, now,
            ),
        )
        await db.commit()
        return chosen_label, chosen_seq
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()


async def get_allocation(study_id: str, participant_id: str) -> tuple[str, list[FeedbackCondition]] | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT sequence_label FROM sequence_allocations "
            "WHERE study_id = ? AND participant_id = ?",
            (study_id, participant_id),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        seq_label = row["sequence_label"]
        for label, seq in WILLIAMS_SEQUENCES:
            if label == seq_label:
                return label, seq
        valid_labels = [lbl for lbl, _ in WILLIAMS_SEQUENCES]
        raise AllocationIntegrityError(
            f"Persisted sequence label '{seq_label}' is not in the allowed set {valid_labels}. "
            "This indicates data corruption — refusing to substitute silently."
        )
    finally:
        await db.close()


def verify_williams_balance() -> dict:
    conditions = [FeedbackCondition.ADAPTIVE, FeedbackCondition.FIXED, FeedbackCondition.YOKED]
    n_seqs = len(WILLIAMS_SEQUENCES)

    position_counts: dict[tuple[int, str], int] = {}
    carryover_counts: dict[tuple[str, str], int] = {}

    for _, seq in WILLIAMS_SEQUENCES:
        for pos, cond in enumerate(seq):
            key = (pos, cond.value)
            position_counts[key] = position_counts.get(key, 0) + 1
        for i in range(len(seq) - 1):
            pair = (seq[i].value, seq[i + 1].value)
            carryover_counts[pair] = carryover_counts.get(pair, 0) + 1

    position_balanced = all(
        position_counts.get((pos, c.value), 0) == n_seqs // len(conditions)
        for pos in range(len(conditions))
        for c in conditions
    )

    all_pairs = [(a.value, b.value) for a in conditions for b in conditions if a != b]
    carryover_values = [carryover_counts.get(pair, 0) for pair in all_pairs]
    carryover_balanced = len(set(carryover_values)) <= 1 and all(v > 0 for v in carryover_values)

    return {
        "n_sequences": n_seqs,
        "position_balanced": position_balanced,
        "carryover_balanced": carryover_balanced,
        "position_counts": {f"pos{k[0]}_{k[1]}": v for k, v in sorted(position_counts.items())},
        "carryover_counts": {f"{k[0]}->{k[1]}": v for k, v in sorted(carryover_counts.items())},
    }
