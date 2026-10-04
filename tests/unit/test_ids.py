"""Phase 3: mutation keys are deterministic and scoped to (task, effect)."""

import re

from northstar_common.ids import mutation_key, sha256_hex


def test_mutation_key_deterministic():
    first = mutation_key("task-1", "replacement.create")
    assert first == mutation_key("task-1", "replacement.create")
    assert re.fullmatch(r"[0-9a-f]{64}", first)


def test_mutation_key_scoped():
    assert mutation_key("task-1", "replacement.create") != mutation_key("task-1", "refund.create")
    assert mutation_key("task-1", "refund.create") != mutation_key("task-2", "refund.create")


def test_sha256_hex_order_matters():
    assert sha256_hex("a", "b") != sha256_hex("b", "a")
