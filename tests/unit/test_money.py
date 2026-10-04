"""Phase 3: money stays in integer paise with Indian Rupee formatting."""

from decimal import Decimal

from northstar_common.money import format_inr, to_paise, to_rupees


def test_to_paise_from_decimal_str_and_int():
    assert to_paise(Decimal("2500.50")) == 250050
    assert to_paise("100") == 10000
    assert to_paise(5) == 500


def test_to_paise_rounds_half_up():
    assert to_paise("99.999") == 10000
    assert to_paise("0.004") == 0


def test_to_rupees_roundtrip():
    assert to_rupees(250050) == Decimal("2500.50")
    assert to_paise(to_rupees(12345)) == 12345


def test_format_inr_indian_grouping():
    assert format_inr(250000) == "₹2,500.00"
    assert format_inr(15000000) == "₹1,50,000.00"
    assert format_inr(1000000000) == "₹1,00,00,000.00"
    assert format_inr(999) == "₹9.99"


def test_format_inr_zero_and_negative():
    assert format_inr(0) == "₹0.00"
    assert format_inr(-150) == "-₹1.50"
