from datetime import datetime

from django.db.models import Count, F
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from theatre.models import (
    Genre,
    Actor,
    TheatreHall,
    Play,
    Performance,
    Reservation,
    Ticket,
)
from theatre.permissions import IsAdminOrIfAuthenticatedReadOnly
from theatre.serializers import (
    GenreSerializer,
    ActorSerializer,
    TheatreHallSerializer,
    PlaySerializer,
    PlayListSerializer,
    PlayDetailSerializer,
    PerformanceSerializer,
    PerformanceListSerializer,
    PerformanceDetailSerializer,
    ReservationSerializer,
    ReservationListSerializer,
    TicketSerializer,
)


class GenreViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class ActorViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class TheatreHallViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet
):
    queryset = TheatreHall.objects.all()
    serializer_class = TheatreHallSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class PlayViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Play.objects.prefetch_related("genres", "actors")
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        title = self.request.query_params.get("title")
        genres = self.request.query_params.get("genres")
        actors = self.request.query_params.get("actors")

        queryset = self.queryset

        if title:
            queryset = queryset.filter(title__icontains=title)

        if genres:
            genre_ids = [int(id) for id in genres.split(",")]
            queryset = queryset.filter(genres__id__in=genre_ids)

        if actors:
            actor_ids = [int(id) for id in actors.split(",")]
            queryset = queryset.filter(actors__id__in=actor_ids)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return PlayListSerializer
        if self.action == "retrieve":
            return PlayDetailSerializer
        return PlaySerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "genres",
                type={"type": "list", "items": {"type": "number"}},
                description="Filter by genre id",
            ),
            OpenApiParameter(
                "actors",
                type={"type": "list", "items": {"type": "number"}},
                description="Filter by actor id",
            ),
            OpenApiParameter(
                "title", type=OpenApiTypes.STR, description="Filter by title"
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class PerformanceViewSet(viewsets.ModelViewSet):
    queryset = Performance.objects.select_related("play", "theatre_hall").annotate(
        tickets_available=(
            F("theatre_hall__rows") * F("theatre_hall__seats_in_row") - Count("tickets")
        )
    )
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        date = self.request.query_params.get("date")
        play_id = self.request.query_params.get("play")

        queryset = self.queryset

        if date:
            date = datetime.strptime(date, "%Y-%m-%d").date()
            queryset = queryset.filter(show_time__date=date)

        if play_id:
            queryset = queryset.filter(play_id=int(play_id))

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PerformanceListSerializer
        if self.action == "retrieve":
            return PerformanceDetailSerializer
        return PerformanceSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "play", type=OpenApiTypes.INT, description="Filter by play id"
            ),
            OpenApiParameter(
                "date", type=OpenApiTypes.DATE, description="Filter by performance date"
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ReservationPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


class ReservationViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, GenericViewSet
):
    queryset = Reservation.objects.prefetch_related(
        "tickets__performance__play", "tickets__performance__theatre_hall"
    )
    serializer_class = ReservationSerializer
    pagination_class = ReservationPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return ReservationListSerializer
        return ReservationSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
