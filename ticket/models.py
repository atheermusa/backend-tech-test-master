from django.db import models, transaction
from django.conf import settings
from django.db.models import Count, Sum
from django.contrib.auth import get_user_model


UserModel = get_user_model()


class Event(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def get_orders_and_cancellation_rate(self):
        # Get the total number of orders for the given event
        total_orders = self.orders.count()

        # Get the total number of cancelled tickets for the given event
        cancelled_tickets = self.tickets.filter(order__fulfilled=False).count()

        # Calculate the cancellation rate as a percentage
        cancellation_rate = (cancelled_tickets / total_orders) * 100

        return total_orders, cancellation_rate

    def get_date_with_highest_number_of_cancelled_tickets(self):
        # Get the date with the highest number of cancelled tickets for the given event
        # Note that we are only considering tickets that have not been fulfilled (i.e. cancelled tickets)
        date_with_highest_cancelled_tickets = (
            self.tickets.filter(order__fulfilled=False)
            .annotate(cancelled_tickets=Count("order__created_at", distinct=True))
            .order_by("-cancelled_tickets")
            .first()
            .order__created_at
        )

        return date_with_highest_cancelled_tickets


class TicketType(models.Model):
    name = models.CharField(max_length=255)
    event = models.ForeignKey(
        Event, related_name="ticket_types", on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1, editable=False)

    quantity.help_text = "The number of actual tickets available upon creation"

    def available_tickets(self):
        return self.tickets.filter(order__isnull=True)

    def save(self, *args, **kwargs):
        new = not self.pk
        super().save(*args, **kwargs)
        if new:
            self.tickets.bulk_create([Ticket(ticket_type=self)] * self.quantity)


class Ticket(models.Model):
    ticket_type = models.ForeignKey(
        TicketType, related_name="tickets", on_delete=models.CASCADE
    )
    order = models.ForeignKey(
        "ticket.Order",
        related_name="tickets",
        default=None,
        null=True,
        on_delete=models.SET_NULL,
    )


class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="orders", on_delete=models.PROTECT
    )
    ticket_type = models.ForeignKey(
        TicketType, related_name="orders", on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField()
    fulfilled = models.BooleanField(default=False)

    def book_tickets(self):
        if self.fulfilled:
            raise Exception("Order already fulfilled")
        qs = self.ticket_type.available_tickets().select_for_update(skip_locked=True)[
            : self.quantity
        ]
        try:
            with transaction.atomic():
                updated_count = self.ticket_type.tickets.filter(id__in=qs).update(
                    order=self
                )
                if updated_count != self.quantity:
                    raise Exception
        except Exception:
            return
        self.fulfilled = True
        self.save(update_fields=["fulfilled"])
