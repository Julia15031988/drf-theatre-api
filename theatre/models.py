import os
import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Genre(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Actor(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)

    def __str__(self):
        return self.first_name + " " + self.last_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class TheatreHall(models.Model):
    name = models.CharField(max_length=255)
    rows = models.IntegerField()
    seats_in_row = models.PositiveIntegerField()

    @property
    def capacity(self) -> int:
        return self.rows * self.seats_in_row

    def __str__(self):
        return self.name


class Play(models.Model):
    title = models.CharField(max_length=128)
    description = models.TextField()
    genres = models.ManyToManyField(
        Genre,
        blank=True,
        related_name="plays",
    )
    actors = models.ManyToManyField(
        Actor,
        blank=True,
        related_name="plays",
    )

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Performance(models.Model):
    show_time = models.DateTimeField()
    play = models.ForeignKey(
        Play, on_delete=models.CASCADE, related_name="performances"
    )

    theatre_hall = models.ForeignKey(
        TheatreHall, on_delete=models.CASCADE, related_name="performances"
    )

    class Meta:
        ordering = ["-show_time"]

    def __str__(self):
        return self.play.title + " " + str(self.show_time)


class Reservation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )

    def __str__(self):
        return str(self.created_at)

    class Meta:
        ordering = ["-created_at"]


class Ticket(models.Model):
    performance = models.ForeignKey(
        "Performance", on_delete=models.CASCADE, related_name="tickets"
    )
    reservation = models.ForeignKey(
        "Reservation", on_delete=models.CASCADE, related_name="tickets"
    )
    row = models.PositiveIntegerField()
    seat = models.PositiveIntegerField()

    @staticmethod
    def validate_ticket(row, seat, theatre_hall, error_to_raise):
        for value, field_name, hall_attr in [
            (row, "row", "rows"),
            (seat, "seat", "seats_in_row"),
        ]:
            max_value = getattr(theatre_hall, hall_attr)
            if not (1 <= value <= max_value):
                raise error_to_raise(
                    {
                        field_name: f"{field_name.capitalize()} must be in range 1 to {max_value}"
                    }
                )

    def clean(self):
        self.validate_ticket(
            self.row, self.seat, self.performance.theatre_hall, ValidationError
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.performance} — Row {self.row}, Seat {self.seat}"

    class Meta:
        unique_together = ("performance", "row", "seat")
        ordering = ["row", "seat"]
