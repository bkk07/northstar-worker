"""Policy thresholds: versioned defaults mirroring `biz.policies` seeds.

`biz.policies` is the source of truth at runtime (loaded as facts);
these defaults apply when a row is absent, so the engine never blocks on
missing configuration. Amounts are paise ints. Keep in sync with
`database/seeds/policies.yaml` — a test pins the parity.
"""

# P-REF-001: small refunds auto-approve inside count and amount caps.
REF_AUTO_MAX_PAISE = 500000  # Rs. 5,000
REF_MAX_COUNT_90D = 2

# P-REF-002: repeat refunders stay automatic only for tiny amounts.
REF_REPEAT_AUTO_MAX_PAISE = 100000  # Rs. 1,000
REF_WINDOW_DAYS = 90

# P-REF-003: mid-range refunds need a human (up to this cap).
REF_APPROVAL_MAX_PAISE = 5000000  # Rs. 50,000

# P-REPL-001: replacements auto-approve up to this line total.
REPL_AUTO_MAX_PAISE = 15000000  # Rs. 1,50,000

# E-REPL-001: eligibility window after delivery.
REPL_WINDOW_DAYS = 30

# E-REF-002: categories that can never be refunded.
NON_REFUNDABLE_CATEGORIES = frozenset({"final_sale"})

# Ticket categories (or subject/body hints) reporting damage.
DAMAGE_CATEGORIES = frozenset({"damage"})
DAMAGE_HINTS = frozenset(
    {
        "damag",
        "crack",
        "shatter",
        "broken",
        "dent",
        "torn",
        "defect",
        "faulty",
        "dead",
        "stuck",
        "zipper",
        "seam",
        "stitch",
    }
)

DEFAULTS = {
    "P-REF-001": {"max_paise": REF_AUTO_MAX_PAISE, "max_count_90d": REF_MAX_COUNT_90D},
    "P-REF-002": {
        "repeat_auto_max_paise": REF_REPEAT_AUTO_MAX_PAISE,
        "window_days": REF_WINDOW_DAYS,
        "max_count_90d": REF_MAX_COUNT_90D,
    },
    "P-REF-003": {"max_paise": REF_APPROVAL_MAX_PAISE},
    "P-REF-004": {},
    "P-REPL-001": {"max_paise": REPL_AUTO_MAX_PAISE},
    "P-REPL-002": {},
    "E-REPL-001": {"window_days": REPL_WINDOW_DAYS},
    "E-REF-001": {},
    "E-REF-002": {"non_refundable_categories": sorted(NON_REFUNDABLE_CATEGORIES)},
    "P-CAP-001": {},
    "P-OWN-001": {},
    "P-NOTE-001": {},
    "P-DUP-001": {},
    "P-FAIL-CLOSED": {},
}
