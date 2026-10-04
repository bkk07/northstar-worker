"""Money in integer paise with Indian Rupee formatting.

All business amounts are stored and compared as integer paise; floats never
enter the domain. Formatting uses Indian digit grouping (lakhs/crores).
"""

from decimal import ROUND_HALF_UP, Decimal

MINOR_PER_MAJOR = 100


def to_paise(amount_rupees: Decimal | int | str) -> int:
    """Convert a rupee amount to integer paise (rounds half up)."""
    amount = amount_rupees if isinstance(amount_rupees, Decimal) else Decimal(amount_rupees)
    return int((amount * MINOR_PER_MAJOR).to_integral_value(rounding=ROUND_HALF_UP))


def to_rupees(paise: int) -> Decimal:
    """Convert integer paise back to a rupee Decimal."""
    return Decimal(paise) / MINOR_PER_MAJOR


def _group_indian(digits: str) -> str:
    """Group a digit string the Indian way: 150000 -> 1,50,000."""
    if len(digits) <= 3:
        return digits
    tail = digits[-3:]
    head = digits[:-3]
    parts: list[str] = []
    while len(head) > 2:
        parts.append(head[-2:])
        head = head[:-2]
    parts.append(head)
    return ",".join(reversed(parts)) + "," + tail


def format_inr(paise: int) -> str:
    """Format paise as a Rupee string, e.g. 15000000 -> ₹1,50,000.00."""
    sign = "-" if paise < 0 else ""
    magnitude = abs(paise)
    rupees, remainder = divmod(magnitude, MINOR_PER_MAJOR)
    return f"{sign}₹{_group_indian(str(rupees))}.{remainder:02d}"
