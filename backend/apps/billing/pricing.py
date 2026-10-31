"""How an invoice's numbers are calculated. Pure functions, with no database access.

Order for each line: quantity x price, minus discount, then tax on what's left.
Each line is rounded once, and totals are the sum of rounded lines, so a printed
invoice always adds up.
"""
from dataclasses import dataclass, field
from decimal import Decimal

from apps.common.money import round_money

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class LineInput:
    description: str
    quantity: int
    unit_price: Decimal
    tax_name: str = ""
    tax_rate: Decimal = ZERO
    product_id: int | None = None

    @property
    def gross(self):
        return round_money(self.unit_price * self.quantity)


@dataclass(frozen=True)
class DiscountInput:
    kind: str  # "fixed" or "percent"
    value: Decimal
    product_ids: frozenset | None = None  # None means the whole subscription
    min_amount: Decimal = ZERO
    min_quantity: int = 0

    def covers(self, line):
        return self.product_ids is None or line.product_id in self.product_ids


@dataclass(frozen=True)
class PricedLine:
    description: str
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal
    tax_name: str
    tax_rate: Decimal
    tax_amount: Decimal
    line_total: Decimal


@dataclass(frozen=True)
class PricedInvoice:
    lines: list = field(default_factory=list)
    subtotal: Decimal = ZERO
    discount_total: Decimal = ZERO
    tax_total: Decimal = ZERO
    total: Decimal = ZERO


def _discount_per_line(lines, discount):
    """How much of the discount falls on each line. All zeros if it doesn't qualify."""
    amounts = [ZERO] * len(lines)
    if discount is None:
        return amounts

    covered = [i for i, line in enumerate(lines) if discount.covers(line)]
    base = sum((lines[i].gross for i in covered), ZERO)
    quantity = sum(lines[i].quantity for i in covered)
    if base <= 0 or base < discount.min_amount or quantity < discount.min_quantity:
        return amounts

    if discount.kind == "percent":
        for i in covered:
            amounts[i] = round_money(lines[i].gross * discount.value / 100)
        return amounts

    # A fixed amount can't exceed what it's taken off, and is shared in proportion to
    # each line's value. The last line takes any rounding remainder, so the parts
    # always add up to exactly the discount.
    remaining = min(round_money(discount.value), base)
    for position, i in enumerate(covered):
        if position == len(covered) - 1:
            amounts[i] = remaining
        else:
            amounts[i] = round_money(min(discount.value, base) * lines[i].gross / base)
            remaining -= amounts[i]
    return amounts


def price_invoice(lines, discount=None):
    priced = []
    for line, discount_amount in zip(lines, _discount_per_line(lines, discount)):
        taxable = line.gross - discount_amount
        tax_amount = round_money(taxable * line.tax_rate / 100)
        priced.append(PricedLine(
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            discount_amount=discount_amount,
            tax_name=line.tax_name,
            tax_rate=line.tax_rate,
            tax_amount=tax_amount,
            line_total=taxable + tax_amount,
        ))
    return PricedInvoice(
        lines=priced,
        subtotal=sum((line.gross for line in lines), ZERO),
        discount_total=sum((p.discount_amount for p in priced), ZERO),
        tax_total=sum((p.tax_amount for p in priced), ZERO),
        total=sum((p.line_total for p in priced), ZERO),
    )
