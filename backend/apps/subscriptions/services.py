"""Every change to a subscription's status or lines goes through here."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import DomainError
from apps.common.money import round_money
from apps.common.sequences import next_value

from .models import Subscription, SubscriptionEvent, SubscriptionLine
from .periods import add_periods

Status = Subscription.Status

# The whole state machine. Any move not listed here is refused.
TRANSITIONS = {
    Status.DRAFT: {Status.QUOTATION, Status.CLOSED},
    Status.QUOTATION: {Status.DRAFT, Status.CONFIRMED, Status.CLOSED},
    Status.CONFIRMED: {Status.ACTIVE, Status.CLOSED},
    Status.ACTIVE: {Status.PAUSED, Status.CLOSED},
    Status.PAUSED: {Status.ACTIVE, Status.CLOSED},
    Status.CLOSED: set(),
}


def _invalid(message, field):
    return DomainError(message, code="validation_error", status_code=422, fields={field: message})


def lock(subscription):
    """Hold this row until the transaction ends, so two actions can't overlap on it."""
    return Subscription.objects.select_for_update(of=("self",)).select_related("plan").get(pk=subscription.pk)


def transition(subscription, to_status, *, actor=None, note=""):
    """The only place a status changes. The caller must already hold the lock."""
    from_status = subscription.status
    if to_status not in TRANSITIONS[from_status]:
        raise DomainError(
            f"A {from_status} subscription can't become {to_status}.", code="invalid_transition"
        )
    subscription.status = to_status
    subscription.save()
    SubscriptionEvent.objects.create(
        subscription=subscription, from_status=from_status, to_status=to_status, actor=actor, note=note
    )


def _check_plan_available(plan, on_date):
    if not plan.is_active:
        raise _invalid("This plan is no longer offered.", "plan")
    if plan.available_from and on_date < plan.available_from:
        raise _invalid(f"This plan isn't available until {plan.available_from}.", "plan")
    if plan.available_to and on_date > plan.available_to:
        raise _invalid(f"This plan stopped being available on {plan.available_to}.", "plan")


def _write_lines(subscription, line_specs):
    """Replace all lines: the plan fee, if any, plus one line per product.

    Each spec has product, quantity, and optionally variant and unit_price. Without a
    unit_price, the line charges the product's sales price plus the variant's extra.
    """
    plan = subscription.plan
    subscription.lines.all().delete()
    if plan.price > 0:
        SubscriptionLine.objects.create(
            subscription=subscription, description=f"{plan.name} plan", quantity=1, unit_price=plan.price
        )
    for spec in line_specs:
        product, variant = spec["product"], spec.get("variant")
        if not product.is_active:
            raise _invalid(f"{product.name} is no longer offered.", "lines")
        if variant and variant.product_id != product.id:
            raise _invalid(f"{variant} isn't a variant of {product.name}.", "lines")
        if spec["quantity"] < plan.min_quantity:
            raise _invalid(f"{plan.name} needs a quantity of at least {plan.min_quantity}.", "lines")
        unit_price = spec.get("unit_price")
        if unit_price is None:
            unit_price = product.sales_price + (variant.extra_price if variant else Decimal("0"))
        SubscriptionLine.objects.create(
            subscription=subscription,
            product=product,
            variant=variant,
            description=f"{product.name} ({variant.value})" if variant else product.name,
            quantity=spec["quantity"],
            unit_price=unit_price,
        )
    _refresh_recurring_subtotal(subscription)


def _refresh_recurring_subtotal(subscription):
    subscription.recurring_subtotal = sum(
        (round_money(line.unit_price * line.quantity) for line in subscription.lines.all()), Decimal("0.00")
    )
    subscription.save(update_fields=["recurring_subtotal"])


@transaction.atomic
def create_subscription(
    *, customer, plan, start_date, line_specs, actor=None, expiry_date=None,
    payment_terms_days=30, discount=None, quote_valid_until=None,
):
    if not customer.is_active:
        raise _invalid("This customer is inactive.", "customer")
    _check_plan_available(plan, start_date)
    expiry_date = expiry_date or add_periods(start_date, plan.interval, plan.term_periods)
    if expiry_date <= start_date:
        raise _invalid("Expiry must be after the start date.", "expiry_date")

    subscription = Subscription.objects.create(
        number=f"SUB-{next_value('subscription'):06d}",
        customer=customer,
        plan=plan,
        discount=discount,
        start_date=start_date,
        expiry_date=expiry_date,
        payment_terms_days=payment_terms_days,
        quote_valid_until=quote_valid_until,
    )
    _write_lines(subscription, line_specs)
    SubscriptionEvent.objects.create(
        subscription=subscription, to_status=Status.DRAFT, actor=actor, note="Created"
    )
    return subscription


def create_from_template(*, template, customer, start_date, actor=None, today=None):
    """Start from a template: its plan and lines, valid for its set number of days."""
    today = today or timezone.localdate()
    specs = [
        {"product": line.product, "variant": line.variant, "quantity": line.quantity}
        for line in template.lines.select_related("product", "variant")
    ]
    return create_subscription(
        customer=customer,
        plan=template.plan,
        start_date=start_date,
        line_specs=specs,
        actor=actor,
        quote_valid_until=add_periods(today, "daily", template.validity_days),
    )


@transaction.atomic
def update_draft(subscription, *, line_specs=None, actor=None, **fields):
    """Terms and lines can only be edited while it's still a draft."""
    subscription = lock(subscription)
    if subscription.status != Status.DRAFT:
        raise DomainError("Only a draft can be edited. Revise the quotation first.", code="invalid_transition")
    allowed = {"plan", "start_date", "expiry_date", "payment_terms_days", "quote_valid_until", "discount"}
    for name, value in fields.items():
        if name not in allowed:
            raise ValueError(f"{name} can't be edited here.")
        setattr(subscription, name, value)
    _check_plan_available(subscription.plan, subscription.start_date)
    if subscription.expiry_date <= subscription.start_date:
        raise _invalid("Expiry must be after the start date.", "expiry_date")
    subscription.save()
    if line_specs is None and "plan" in fields:
        # The plan fee line belongs to the plan, so changing plan rewrites the lines.
        line_specs = [
            {"product": line.product, "variant": line.variant, "quantity": line.quantity, "unit_price": line.unit_price}
            for line in subscription.lines.select_related("product", "variant")
            if line.product
        ]
    if line_specs is not None:
        _write_lines(subscription, line_specs)
    return subscription


def available_actions(subscription):
    """What can be done next, so screens only offer buttons that will work."""
    plan = subscription.plan
    status = subscription.status
    actions = []
    if status == Status.DRAFT:
        actions.append("send")
    if status == Status.QUOTATION:
        actions += ["confirm", "revise"]
    if status == Status.CONFIRMED:
        actions.append("activate")
    if status == Status.ACTIVE and plan.pausable:
        actions.append("pause")
    if status == Status.PAUSED:
        actions.append("resume")
    if status in {Status.ACTIVE, Status.PAUSED} and plan.renewable:
        actions.append("renew")
    if status != Status.CLOSED and (status not in {Status.ACTIVE, Status.PAUSED} or plan.closable):
        actions.append("close")
    return actions


@transaction.atomic
def send_quotation(subscription, *, actor=None, today=None):
    subscription = lock(subscription)
    today = today or timezone.localdate()
    if not subscription.lines.exists():
        raise _invalid("Add at least one line before sending.", "lines")
    if subscription.quote_valid_until and subscription.quote_valid_until < today:
        raise _invalid("The validity date has passed. Set a new one before sending.", "quote_valid_until")
    transition(subscription, Status.QUOTATION, actor=actor)
    return subscription


@transaction.atomic
def revise_quotation(subscription, *, actor=None):
    subscription = lock(subscription)
    transition(subscription, Status.DRAFT, actor=actor, note="Sent back for changes")
    return subscription


@transaction.atomic
def confirm_quotation(subscription, *, actor=None, today=None):
    subscription = lock(subscription)
    today = today or timezone.localdate()
    if (
        subscription.status == Status.QUOTATION
        and subscription.quote_valid_until
        and subscription.quote_valid_until < today
    ):
        raise DomainError("This quotation has expired.", code="quote_expired")
    transition(subscription, Status.CONFIRMED, actor=actor)
    return subscription


@transaction.atomic
def pause(subscription, *, actor=None):
    subscription = lock(subscription)
    if not subscription.plan.pausable:
        raise DomainError("This plan can't be paused.", code="invalid_transition")
    transition(subscription, Status.PAUSED, actor=actor)
    return subscription


@transaction.atomic
def resume(subscription, *, actor=None, today=None):
    """Periods that passed while paused aren't billed.

    If the period already billed is still running, the schedule stays as it was, so
    the customer isn't charged twice for the same days. Otherwise billing restarts today.
    """
    subscription = lock(subscription)
    today = today or timezone.localdate()
    transition(subscription, Status.ACTIVE, actor=actor)
    if subscription.next_billing_date and subscription.next_billing_date < today:
        subscription.billing_anchor = today
        subscription.periods_billed = 0
        subscription.next_billing_date = today
        subscription.save()
    return subscription


@transaction.atomic
def renew(subscription, *, actor=None):
    """Extend the expiry by one term. Billing continues on the same schedule."""
    subscription = lock(subscription)
    if not subscription.plan.renewable:
        raise DomainError("This plan can't be renewed.", code="invalid_transition")
    if subscription.status not in {Status.ACTIVE, Status.PAUSED}:
        raise DomainError(f"A {subscription.status} subscription can't be renewed.", code="invalid_transition")
    old_expiry = subscription.expiry_date
    plan = subscription.plan
    subscription.expiry_date = add_periods(old_expiry, plan.interval, plan.term_periods)
    subscription.save()
    SubscriptionEvent.objects.create(
        subscription=subscription,
        from_status=subscription.status,
        to_status=subscription.status,
        actor=actor,
        note=f"Renewed: expiry moved from {old_expiry} to {subscription.expiry_date}",
    )
    return subscription


def _close(subscription, *, actor=None, note=""):
    subscription.closed_at = timezone.now()
    subscription.next_billing_date = None
    transition(subscription, Status.CLOSED, actor=actor, note=note)


@transaction.atomic
def close(subscription, *, actor=None, note=""):
    """Stops all future billing. Existing invoices stay as they are, with no refund."""
    subscription = lock(subscription)
    started = subscription.status in {Status.ACTIVE, Status.PAUSED}
    if started and not subscription.plan.closable:
        raise DomainError("This plan can't be closed early.", code="invalid_transition")
    _close(subscription, actor=actor, note=note)
    return subscription


@transaction.atomic
def close_at_expiry(subscription):
    """The system closing an auto-close plan. Not an early closure, so `closable` doesn't apply."""
    subscription = lock(subscription)
    _close(subscription, note="Closed automatically at expiry")
    return subscription


@transaction.atomic
def set_discount(subscription, discount, *, actor=None):
    """Attach or remove a discount. It appears on the next invoice by itself."""
    subscription = lock(subscription)
    if subscription.status == Status.CLOSED:
        raise DomainError("A closed subscription can't change.", code="invalid_transition")
    subscription.discount = discount
    subscription.save(update_fields=["discount"])
    SubscriptionEvent.objects.create(
        subscription=subscription,
        from_status=subscription.status,
        to_status=subscription.status,
        actor=actor,
        note=f"Discount set to {discount.name}" if discount else "Discount removed",
    )
    return subscription
