from django.core.management.base import BaseCommand
from library.services import ReservationService


class Command(BaseCommand):
    help = 'Scan and release expired reservations, cascading holds to subsequent waiting readers or restoring inventory.'

    def handle(self, *args, **options):
        self.stdout.write('Checking for expired reservations...')
        released_count, cascaded_count = ReservationService.check_and_release_expired_reservations()
        self.stdout.write(
            self.style.SUCCESS(
                f'Done! Released {released_count} expired reservation(s), '
                f'cascaded {cascaded_count} hold(s) to next reader(s).'
            )
        )
