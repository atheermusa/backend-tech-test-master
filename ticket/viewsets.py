from rest_framework import mixins, viewsets, exceptions, response, status

from .models import Event, TicketType, Order
from .serializers import EventSerializer, TicketTypeSerializer, OrderSerializer
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin


class EventViewSet(
    CreateModelMixin, ListModelMixin, RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = EventSerializer
    queryset = Event.objects.prefetch_related("ticket_types")

    def create(self, request):
        # Get the data for the new event and order from the request
        event_data = request.data.get("event")
        order_data = request.data.get("order")

        # Create a new event instance
        event = Event.objects.create(
            name=event_data.get("name"), description=event_data.get("description")
        )

        # Create a new order instance for the event
        order = Order.objects.create(
            user=order_data.get("user"),
            ticket_type=order_data.get("ticket_type"),
            quantity=order_data.get("quantity"),
        )

        # Serialize the event and order instances and return the response
        event_serializer = EventSerializer(event)
        order_serializer = OrderSerializer(order)
        data = {"event": event_serializer.data, "order": order_serializer.data}
        return response.Response(data, status=status.HTTP_201_CREATED)

    def list(self, request):
        # Get the queryset of events
        queryset = self.get_queryset()

        # Add the extra information to each event instance in the queryset
        for event in queryset:
            # Get the number of orders and cancellation rate for the event
            total_orders, cancellation_rate = event.get_orders_and_cancellation_rate()

            # Get the date with the highest number of cancelled tickets for the event
            date_with_highest_cancelled_tickets = (
                event.get_date_with_highest_number_of_cancelled_tickets()
            )

            # Add the extra information to the event instance
            event.total_orders = total_orders
            event.cancellation_rate = cancellation_rate
            event.date_with_highest_cancelled_tickets = (
                date_with_highest_cancelled_tickets
            )

        # Serialize the queryset and return the response
        serializer = self.get_serializer(queryset, many=True)
        return response.Response(serializer.data)


class OrderViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)

    def perform_create(self, serializer):
        order = serializer.save(user=self.request.user)
        order.book_tickets()
        if not order.fulfilled:
            order.delete()
            raise exceptions.ValidationError("Couldn't book tickets")
