from django.test import TestCase
from django_dynamic_fixture import G, F


from datetime import datetime

from ticket.models import Event, Order, Ticket, TicketType
from django.contrib.auth import get_user_model


UserModel = get_user_model()


class TicketTypeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.event = G(Event)

    def test_avaialble_tickets(self):
        ticket_type = G(TicketType, name="Test", quantity=5, event=self.event)
        all_tickets = list(ticket_type.tickets.all())

        five_available_tickets = set(ticket_type.available_tickets())

        # book one ticket
        ticket = all_tickets[0]
        ticket.order = G(Order, ticket_type=ticket_type, quantity=1)
        ticket.save()

        four_available_tickets = set(ticket_type.available_tickets())

        self.assertCountEqual(five_available_tickets, all_tickets)
        self.assertCountEqual(four_available_tickets, set(all_tickets) - {ticket})

    def test_save(self):
        """Verifying that the save method creates Ticket(s) upon TicketType creation"""

        ticket_type_1 = G(TicketType, name="Without quantity", event=self.event)
        ticket_type_5 = G(TicketType, name="Test", quantity=5, event=self.event)

        one_ticket = ticket_type_1.tickets.count()
        five_tickets = ticket_type_5.tickets.count()

        self.assertEqual(one_ticket, 1)
        self.assertEqual(five_tickets, 5)


class OrderTest(TestCase):
    def test_book_tickets(self):
        order = G(Order, ticket_type=F(quantity=5), quantity=3)

        pre_booking_ticket_count = order.tickets.count()
        order.book_tickets()
        post_booking_ticket_count = order.tickets.count()

        with self.assertRaisesRegexp(Exception, r"Order already fulfilled"):
            order.book_tickets()

        self.assertEqual(pre_booking_ticket_count, 0)
        self.assertEqual(post_booking_ticket_count, 3)


class EventModelTests(TestCase):
    def setUp(self):
        # Create an event
        self.event = Event.objects.create(
            name="My Event", description="This is my event"
        )

        # Create a ticket type for the event
        self.ticket_type = TicketType.objects.create(
            name="My Ticket Type", event=self.event, quantity=10
        )

        # Create a few orders for the event
        self.orders = [
            Order.objects.create(
                user=UserModel.objects.create_user(
                    username="testuser1", password="password", email="test@example.com"
                ),
                ticket_type=self.ticket_type,
                quantity=1,
                fulfilled=True,
            ),
            Order.objects.create(
                user=UserModel.objects.create_user(
                    username="testuser2", password="password", email="test@example.com"
                ),
                ticket_type=self.ticket_type,
                quantity=1,
                fulfilled=False,
            ),
            Order.objects.create(
                user=UserModel.objects.create_user(
                    username="testuser3", password="password", email="test@example.com"
                ),
                ticket_type=self.ticket_type,
                quantity=1,
                fulfilled=False,
            ),
            Order.objects.create(
                user=UserModel.objects.create_user(
                    username="testuser4", password="password", email="test@example.com"
                ),
                ticket_type=self.ticket_type,
                quantity=2,
                fulfilled=True,
            ),
        ]

    def test_get_orders_and_cancellation_rate(self):
        # Test the get_orders_and_cancellation_rate method
        total_orders, cancellation_rate = self.event.get_orders_and_cancellation_rate()

        # Assert that the total number of orders is correct
        self.assertEqual(total_orders, 4)

        # Assert that the cancellation rate is correct
        self.assertEqual(cancellation_rate, 50)

    def test_get_date_with_highest_number_of_cancelled_tickets(self):
        # Test the get_date_with_highest_number_of_cancelled_tickets method
        date_with_highest_cancelled_tickets = (
            self.event.get_date_with_highest_number_of_cancelled_tickets()
        )

        # Assert that the date with the highest number of cancelled tickets is correct
        self.assertEqual(date_with_highest_cancelled_tickets, self.orders[1].created_at)
