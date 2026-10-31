"""Creating invoices, running billing, and recording payments."""
from datetime import timedelta
from decimal import Decimal
from smtplib import SMTPException

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from apps.catalog.models import DiscountRule
from apps.common import email
from apps.common.exceptions import DomainError
from apps.common.sequences import next_value
from apps.subscriptions import services as subscription_services
from apps.subscriptions.models import Subscription
from apps.subscriptions.periods import period_bounds

from .models import BillingRun, Invoice, InvoiceLine, Payment
from .pricing import DiscountInput, LineInput, price_invoice

DOUBLE_BILLING_CONSTRAINT = "invoice_one_live_per_period"
SQLITE_DOUBLE_BILLING = "billing_invoice.subscription_id, billing_invoice.period_start"


def _is_double_billing(error):
    """Postgres names the constraint in its error, and SQLite names the columns."""
    return DOUBLE_BILLING_CONSTRAINT in str(error) or SQLITE_DOUBLE_BILLING in str(error)


# --- Pricing a subscription ---

def _tax_for(rule):
    if rule and rule.is_active:
        return rule.name, rule.rate_percent
    return "", Decimal("0.00")


def _line_inputs(subscription):
    inputs = []
    for line in subscription.lines.select_related("product__tax_rule"):
        rule = line.product.tax_rule if line.product else subscription.plan.tax_rule
        tax_name, tax_rate = _tax_for(rule)
        inputs.append(LineInput(
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            tax_name=tax_name,
            tax_rate=tax_rate,
            product_id=line.product_id,
        ))
    return inputs


def _is_usable(rule, on_date):
    """Stops by itself once it expires or runs out."""
    return (
        rule.is_active
        and rule.starts_on <= on_date
        and (rule.ends_on is None or on_date <= rule.ends_on)
        and (rule.usage_limit is None or rule.times_used < rule.usage_limit)
    )


def _discount_input(rule):
    products = None
    if rule.scope == DiscountRule.Scope.PRODUCTS:
        products = frozenset(rule.products.values_list("id", flat=True))
    return DiscountInput(
        kind=rule.kind,
        value=rule.value,
        product_ids=products,
        min_amount=rule.min_amount,
        min_quantity=rule.min_quantity,
    )


def preview_invoice(subscription, on_date=None):
    """What the next invoice would be. Writes nothing, so quote screens can call it freely."""
    on_date = on_date or timezone.localdate()
    rule = subscription.discount
    discount = _discount_input(rule) if rule and _is_usable(rule, on_date) else None
    return price_invoice(_line_inputs(subscription), discount)


# --- Creating invoices ---

def _create_invoice(subscription, period_start, period_end, *, issue_date, billing_run=None):
    """Build one invoice. The caller holds the subscription lock inside a transaction."""
    # Locked so two subscriptions can't both take a discount's last use.
    rule = None
    if subscription.discount_id:
        rule = DiscountRule.objects.select_for_update().get(pk=subscription.discount_id)
        if not _is_usable(rule, period_start):
            rule = None

    priced = price_invoice(_line_inputs(subscription), _discount_input(rule) if rule else None)
    customer = subscription.customer
    invoice = Invoice.objects.create(
        number=f"INV-{issue_date.year}-{next_value(f'invoice-{issue_date.year}'):06d}",
        subscription=subscription,
        customer=customer,
        billing_run=billing_run,
        period_start=period_start,
        period_end=period_end,
        issue_date=issue_date,
        due_date=issue_date + timedelta(days=subscription.payment_terms_days),
        customer_name=customer.company or customer.name,
        customer_email=customer.email,
        customer_address=customer.address,
        subtotal=priced.subtotal,
        discount_total=priced.discount_total,
        tax_total=priced.tax_total,
        total=priced.total,
        discount_rule=rule if rule and priced.discount_total > 0 else None,
    )
    InvoiceLine.objects.bulk_create([
        InvoiceLine(
            invoice=invoice,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            discount_amount=line.discount_amount,
            tax_name=line.tax_name,
            tax_rate=line.tax_rate,
            tax_amount=line.tax_amount,
            line_total=line.line_total,
        )
        for line in priced.lines
    ])
    # A discount that didn't change this invoice, like an unmet minimum, doesn't use up a turn.
    if invoice.discount_rule_id:
        DiscountRule.objects.filter(pk=rule.pk).update(times_used=F("times_used") + 1)
    return invoice


def _bill_due_periods(subscription, as_of, billing_run=None):
    """Invoice every period that has come due. The caller holds the lock.

    The loop is what prevents skips: three missed months produce three invoices. The
    date moves forward in the same transaction as the invoice, so a crash can never
    leave one without the other.
    """
    plan = subscription.plan
    created = 0
    while subscription.next_billing_date <= as_of and subscription.next_billing_date < subscription.expiry_date:
        start, end = period_bounds(subscription.billing_anchor, plan.interval, subscription.periods_billed)
        _create_invoice(
            subscription, start, min(end, subscription.expiry_date), issue_date=as_of, billing_run=billing_run
        )
        subscription.periods_billed += 1
        subscription.next_billing_date = end
        created += 1
    subscription.save(update_fields=["periods_billed", "next_billing_date"])
    return created


@transaction.atomic
def activate(subscription, *, actor=None, today=None):
    """Start the subscription and bill what's already due, all or nothing.

    This lives in billing because activating creates an invoice, and the subscriptions
    app is not allowed to depend on billing.
    """
    subscription = subscription_services.lock(subscription)
    today = today or timezone.localdate()
    if subscription.expiry_date <= today:
        raise DomainError("This subscription's expiry date has already passed.", code="invalid_transition")
    subscription_services.transition(subscription, Subscription.Status.ACTIVE, actor=actor)
    subscription.billing_anchor = subscription.start_date
    subscription.periods_billed = 0
    subscription.next_billing_date = subscription.start_date
    subscription.save()
    _bill_due_periods(subscription, today)
    return subscription


# --- The billing run ---

def _due_subscription_ids(as_of):
    return list(
        Subscription.objects.filter(
            status=Subscription.Status.ACTIVE,
            next_billing_date__lte=as_of,
            next_billing_date__lt=F("expiry_date"),
        ).values_list("id", flat=True)
    )


def _bill_one(subscription_id, as_of, run):
    """Returns the number of invoices created. Each subscription is its own transaction."""
    with transaction.atomic():
        # skip_locked: if another run is on this subscription, leave it to that run. The
        # filter is checked again under the lock, in case it was just billed.
        subscription = (
            Subscription.objects.select_for_update(skip_locked=True, of=("self",))
            .select_related("plan", "customer")
            .filter(
                pk=subscription_id,
                status=Subscription.Status.ACTIVE,
                next_billing_date__lte=as_of,
            )
            .first()
        )
        if subscription is None:
            return 0
        return _bill_due_periods(subscription, as_of, billing_run=run)


def _close_expired(as_of):
    expired = Subscription.objects.filter(
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.PAUSED],
        plan__auto_close=True,
        expiry_date__lte=as_of,
    )
    for subscription in expired:
        subscription_services.close_at_expiry(subscription)


def run_billing(*, as_of=None, triggered_by=None):
    """Bill everything due. Safe to run any number of times, even at once.

    Running twice creates nothing the second time, because each subscription's billing
    date has moved on. If that protection ever failed, the database constraint on
    subscription and period would still refuse the duplicate.
    """
    today = timezone.localdate()
    as_of = as_of or today
    if as_of > today and not settings.BILLING_ALLOW_FUTURE_AS_OF:
        raise DomainError("Billing can't run for a future date.", code="future_as_of", status_code=422)

    run = BillingRun.objects.create(as_of=as_of, triggered_by=triggered_by)
    for subscription_id in _due_subscription_ids(as_of):
        try:
            created = _bill_one(subscription_id, as_of, run)
            if created:
                run.created_count += created
            else:
                run.skipped_count += 1
        except IntegrityError as error:
            if not _is_double_billing(error):
                run.failed_count += 1
                run.errors.append({"subscription": subscription_id, "error": str(error)})
            else:
                run.skipped_count += 1
                run.errors.append({"subscription": subscription_id, "error": "Already invoiced for this period."})
        except Exception as error:  # One bad subscription must not stop the rest of billing day.
            run.failed_count += 1
            run.errors.append({"subscription": subscription_id, "error": str(error)})
    _close_expired(as_of)
    run.finished_at = timezone.now()
    run.save()
    return run


# --- Invoice actions ---

def _lock_invoice(invoice):
    return Invoice.objects.select_for_update().get(pk=invoice.pk)


@transaction.atomic
def confirm_invoice(invoice):
    invoice = _lock_invoice(invoice)
    if invoice.status != Invoice.Status.DRAFT:
        raise DomainError(f"A {invoice.status} invoice can't be confirmed.", code="invalid_transition")
    invoice.confirmed_at = timezone.now()
    # Nothing to collect on a fully discounted invoice.
    invoice.status = Invoice.Status.PAID if invoice.total == 0 else Invoice.Status.CONFIRMED
    invoice.save()
    return invoice


def bulk_confirm(invoice_ids):
    """Confirm the drafts among these. Returns how many were confirmed."""
    drafts = Invoice.objects.filter(pk__in=invoice_ids, status=Invoice.Status.DRAFT)
    count = 0
    for invoice in drafts:
        confirm_invoice(invoice)
        count += 1
    return count


@transaction.atomic
def cancel_invoice(invoice):
    invoice = _lock_invoice(invoice)
    if invoice.status not in {Invoice.Status.DRAFT, Invoice.Status.CONFIRMED}:
        raise DomainError(f"A {invoice.status} invoice can't be cancelled.", code="invalid_transition")
    if invoice.amount_paid > 0:
        raise DomainError("This invoice has payments recorded, so it can't be cancelled.", code="invoice_has_payments")
    invoice.status = Invoice.Status.CANCELLED
    invoice.cancelled_at = timezone.now()
    invoice.save()
    if invoice.discount_rule_id:
        rule = DiscountRule.objects.select_for_update().get(pk=invoice.discount_rule_id)
        rule.times_used = max(0, rule.times_used - 1)
        rule.save(update_fields=["times_used"])
    return invoice


@transaction.atomic
def reissue_invoice(invoice, *, today=None):
    """A correct replacement for a cancelled invoice's period, from the subscription as it is now."""
    invoice = _lock_invoice(invoice)
    if invoice.status != Invoice.Status.CANCELLED:
        raise DomainError("Only a cancelled invoice can be reissued.", code="invalid_transition")
    subscription = subscription_services.lock(invoice.subscription)
    try:
        with transaction.atomic():
            return _create_invoice(
                subscription, invoice.period_start, invoice.period_end, issue_date=today or timezone.localdate()
            )
    except IntegrityError as error:
        if not _is_double_billing(error):
            raise
        raise DomainError("This period already has a live invoice.", code="already_invoiced")


def send_invoice(invoice):
    """Email first, then record it, so sent_at is only set if the email actually went."""
    if invoice.status not in {Invoice.Status.CONFIRMED, Invoice.Status.PAID}:
        raise DomainError("Confirm this invoice before sending it.", code="invalid_transition")
    try:
        email.send_invoice(invoice)
    except (SMTPException, OSError):
        raise DomainError("The email couldn't be sent. Please try again.", code="email_failed", status_code=502)
    invoice.sent_at = timezone.now()
    invoice.save(update_fields=["sent_at"])
    return invoice


# --- Payments ---

@transaction.atomic
def record_payment(invoice, *, method, amount, paid_on, note="", idempotency_key=None, actor=None, today=None):
    """Record money received. Paid is only ever set here, from the balance."""
    invoice = _lock_invoice(invoice)

    # Checked first: a retry after the payment that settled the invoice must return that
    # payment, not an error saying the invoice is already paid.
    if idempotency_key:
        existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            if existing.invoice_id != invoice.pk:
                raise DomainError("This payment key was already used on another invoice.", code="idempotency_conflict")
            return existing

    if invoice.status != Invoice.Status.CONFIRMED:
        raise DomainError(f"Payments can't be recorded on a {invoice.status} invoice.", code="invoice_not_payable")
    if amount <= 0:
        raise DomainError(
            "Amount must be more than zero.", code="validation_error", status_code=422,
            fields={"amount": "Amount must be more than zero."},
        )
    outstanding = invoice.total - invoice.amount_paid
    if amount > outstanding:
        message = f"Amount exceeds the {invoice.currency} {outstanding} outstanding."
        raise DomainError(message, code="overpayment", status_code=422, fields={"amount": message})
    if paid_on > (today or timezone.localdate()):
        message = "Payment date can't be in the future."
        raise DomainError(message, code="validation_error", status_code=422, fields={"paid_on": message})

    payment = Payment.objects.create(
        invoice=invoice, method=method, amount=amount, paid_on=paid_on, note=note,
        idempotency_key=idempotency_key or None, recorded_by=actor,
    )
    invoice.amount_paid += amount
    if invoice.amount_paid == invoice.total:
        invoice.status = Invoice.Status.PAID
    invoice.save()
    return payment
