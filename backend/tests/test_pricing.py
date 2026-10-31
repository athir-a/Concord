"""The calculations alone. Expected values are worked out by hand."""
from datetime import date
from decimal import Decimal as D

import pytest

from apps.billing.pricing import DiscountInput, LineInput, price_invoice
from apps.common.money import round_money
from apps.subscriptions.periods import add_periods, period_bounds


def line(unit="100.00", quantity=1, rate="0", product_id=1):
    return LineInput(description="Item", quantity=quantity, unit_price=D(unit), tax_rate=D(rate), product_id=product_id)


def test_tax_on_quantity():
    priced = price_invoice([line("999.00", quantity=3, rate="18")])
    assert priced.subtotal == D("2997.00")
    assert priced.tax_total == D("539.46")
    assert priced.total == D("3536.46")


def test_rounds_half_up_not_to_even():
    assert round_money(D("0.125")) == D("0.13")
    assert round_money(D("0.135")) == D("0.14")


def test_tax_is_calculated_after_the_discount():
    discount = DiscountInput(kind="percent", value=D("10"))
    priced = price_invoice([line("1000.00", rate="18")], discount)
    assert priced.discount_total == D("100.00")
    assert priced.tax_total == D("162.00")  # 18% of 900, not of 1000
    assert priced.total == D("1062.00")


def test_total_is_the_sum_of_rounded_lines():
    priced = price_invoice([line("0.33", rate="18"), line("0.33", rate="18"), line("0.33", rate="18")])
    assert priced.tax_total == D("0.18")  # 0.06 x 3; rounding the combined 0.1782 would give 0.18 too
    assert priced.total == sum(p.line_total for p in priced.lines)
    assert priced.total == priced.subtotal - priced.discount_total + priced.tax_total


def test_fixed_discount_can_not_go_below_zero():
    priced = price_invoice([line("100.00")], DiscountInput(kind="fixed", value=D("500")))
    assert priced.discount_total == D("100.00")
    assert priced.total == D("0.00")


def test_fixed_discount_splits_exactly_across_lines():
    lines = [line("100.00"), line("100.00"), line("100.00")]
    priced = price_invoice(lines, DiscountInput(kind="fixed", value=D("100")))
    assert [p.discount_amount for p in priced.lines] == [D("33.33"), D("33.33"), D("33.34")]
    assert priced.discount_total == D("100.00")


def test_product_scope_only_touches_those_lines():
    lines = [line("100.00", product_id=1), line("100.00", product_id=2), line("100.00", product_id=None)]
    priced = price_invoice(lines, DiscountInput(kind="percent", value=D("50"), product_ids=frozenset({2})))
    assert [p.discount_amount for p in priced.lines] == [D("0.00"), D("50.00"), D("0.00")]


@pytest.mark.parametrize("minimums, applies", [
    ({"min_amount": D("200.00")}, True),
    ({"min_amount": D("200.01")}, False),
    ({"min_quantity": 2}, True),
    ({"min_quantity": 3}, False),
])
def test_discount_minimums(minimums, applies):
    priced = price_invoice([line("100.00", quantity=2)], DiscountInput(kind="percent", value=D("10"), **minimums))
    assert (priced.discount_total > 0) is applies


def test_minimum_counts_only_the_covered_lines():
    lines = [line("100.00", product_id=1), line("900.00", product_id=2)]
    discount = DiscountInput(kind="percent", value=D("10"), product_ids=frozenset({1}), min_amount=D("500"))
    assert price_invoice(lines, discount).discount_total == D("0.00")


@pytest.mark.parametrize("interval, count, expected", [
    ("daily", 3, date(2026, 2, 3)),
    ("weekly", 2, date(2026, 2, 28)),
    ("monthly", 1, date(2026, 3, 14)),
    ("yearly", 1, date(2027, 2, 14)),
])
def test_each_interval(interval, count, expected):
    start = date(2026, 1, 31) if interval == "daily" else date(2026, 2, 14)
    assert add_periods(start, interval, count) == expected


def test_month_end_does_not_drift():
    anchor = date(2026, 1, 31)
    assert add_periods(anchor, "monthly", 1) == date(2026, 2, 28)
    assert add_periods(anchor, "monthly", 2) == date(2026, 3, 31)
    assert add_periods(anchor, "monthly", 3) == date(2026, 4, 30)


def test_periods_join_with_no_gap():
    anchor = date(2026, 1, 31)
    for index in range(24):
        _, end = period_bounds(anchor, "monthly", index)
        next_start, _ = period_bounds(anchor, "monthly", index + 1)
        assert end == next_start
