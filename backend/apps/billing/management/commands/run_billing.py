from datetime import date

from django.core.management.base import BaseCommand

from apps.billing.services import run_billing


class Command(BaseCommand):
    help = "Bill every subscription that's due. Safe to run repeatedly, for example from cron."

    def add_arguments(self, parser):
        parser.add_argument("--as-of", type=date.fromisoformat, help="Billing date, YYYY-MM-DD. Defaults to today.")

    def handle(self, *args, **options):
        run = run_billing(as_of=options["as_of"])
        self.stdout.write(
            f"Billing run {run.id} as of {run.as_of}: {run.created_count} created, "
            f"{run.skipped_count} skipped, {run.failed_count} failed."
        )
        for error in run.errors:
            self.stderr.write(f"  Subscription {error['subscription']}: {error['error']}")
