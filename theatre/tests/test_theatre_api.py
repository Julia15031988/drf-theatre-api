from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.test import APITestCase
from django.utils.timezone import make_aware
from datetime import datetime, timedelta
from django.urls import reverse
from theatre.models import (
    Play,
    Genre,
    Actor,
    TheatreHall,
    Performance,
    Reservation,
    Ticket,
)
from theatre.serializers import (
    PlayListSerializer,
    PlayDetailSerializer,
    PerformanceListSerializer,
)

PLAY_URL = reverse("theatre:play-list")
PERFORMANCE_URL = reverse("theatre:performance-list")
RESERVATION_URL = reverse("theatre:reservation-list")


def sample_play(**params):
    defaults = {
        "title": "Sample Play",
        "description": "A touching drama",
    }
    defaults.update(params)
    return Play.objects.create(**defaults)


def sample_genre(name="Drama"):
    return Genre.objects.create(name=name)


def sample_actor(first_name="John", last_name="Doe"):
    return Actor.objects.create(first_name=first_name, last_name=last_name)


def sample_theatre_hall(**params):
    defaults = {
        "name": "Main Hall",
        "rows": 10,
        "seats_in_row": 15,
    }
    defaults.update(params)
    return TheatreHall.objects.create(**defaults)


def sample_performance(**params):
    theatre_hall = sample_theatre_hall()
    play = sample_play()

    defaults = {
        "show_time": "2025-08-01T19:00:00Z",
        "play": play,
        "theatre_hall": theatre_hall,
    }
    defaults.update(params)
    return Performance.objects.create(**defaults)


def detail_url(play_id):
    return reverse("theatre:play-detail", args=[play_id])


class PublicPlayTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(PLAY_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivatePlayTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("user@test.com", "testpass")
        self.client.force_authenticate(self.user)

    def test_list_plays(self):
        sample_play()
        sample_play()
        res = self.client.get(PLAY_URL)

        plays = Play.objects.order_by("id")
        serializer = PlayListSerializer(plays, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_plays_by_genres(self):
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Comedy")
        play1 = sample_play(title="Play with drama")
        play2 = sample_play(title="Play with comedy")
        play1.genres.add(genre1)
        play2.genres.add(genre2)
        play3 = sample_play(title="Play without genre")

        res = self.client.get(PLAY_URL, {"genres": f"{genre1.id},{genre2.id}"})

        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_plays_by_actors(self):
        actor1 = sample_actor(first_name="Actor1", last_name="Last1")
        actor2 = sample_actor(first_name="Actor2", last_name="Last2")

        play1 = sample_play(title="Play 1")
        play2 = sample_play(title="Play 2")

        play1.actors.add(actor1)
        play2.actors.add(actor2)

        play3 = sample_play(title="Play without actors")

        res = self.client.get(PLAY_URL, {"actors": f"{actor1.id},{actor2.id}"})

        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_plays_by_title(self):
        play1 = sample_play(title="Hamlet")
        play2 = sample_play(title="Romeo and Juliet")
        play3 = sample_play(title="Macbeth")

        res = self.client.get(PLAY_URL, {"title": "romeo"})

        serializer1 = PlayListSerializer(play1)
        serializer2 = PlayListSerializer(play2)
        serializer3 = PlayListSerializer(play3)

        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer1.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_play_detail(self):
        play = sample_play()
        play.genres.add(sample_genre())
        play.actors.add(sample_actor())

        url = detail_url(play.id)
        res = self.client.get(url)

        serializer = PlayDetailSerializer(play)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_play_forbidden(self):
        payload = {
            "title": "Forbidden Play",
            "description": "Description",
        }
        res = self.client.post(PLAY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminPlayTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@test.com", "testpass", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_play(self):
        payload = {
            "title": "New Play",
            "description": "A new play created by admin",
        }
        res = self.client.post(PLAY_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        play = Play.objects.get(id=res.data["id"])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(play, key))

    def test_create_play_with_genres(self):
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Adventure")
        payload = {
            "title": "The Big Play",
            "genres": [genre1.id, genre2.id],
            "description": "A thrilling adventure.",
        }
        res = self.client.post(PLAY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        play = Play.objects.get(id=res.data["id"])
        genres = play.genres.all()
        self.assertEqual(genres.count(), 2)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)

    def test_create_play_with_actors(self):
        actor1 = sample_actor(first_name="Tom", last_name="Holland")
        actor2 = sample_actor(first_name="Tobey", last_name="Maguire")
        payload = {
            "title": "Spider Man",
            "actors": [actor1.id, actor2.id],
            "description": "A great performance.",
        }
        res = self.client.post(PLAY_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        play = Play.objects.get(id=res.data["id"])
        actors = play.actors.all()
        self.assertEqual(actors.count(), 2)
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)

    def test_put_play_not_allowed(self):
        payload = {
            "title": "New title",
            "description": "New description",
        }
        play = sample_play()
        url = detail_url(play.id)

        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_play_not_allowed(self):
        play = sample_play()
        url = detail_url(play.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class PerformanceTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("user@test.com", "testpass")
        self.client.force_authenticate(self.user)
        self.hall = TheatreHall.objects.create(name="Main Hall", rows=5, seats_in_row=5)
        self.play = Play.objects.create(
            title="Sample Play", description="A great play."
        )
        self.play2 = Play.objects.create(title="Play 1", description="Another play.")

        self.performance = Performance.objects.create(
            play=self.play,
            theatre_hall=self.hall,
            show_time=make_aware(datetime(2025, 8, 1, 19, 0)),
        )
        self.performance2 = Performance.objects.create(
            play=self.play2,
            theatre_hall=self.hall,
            show_time=make_aware(datetime(2025, 8, 2, 20, 0)),
        )

    def test_list_performances(self):
        sample_performance()
        sample_performance()

        res = self.client.get(PERFORMANCE_URL)
        performances = Performance.objects.order_by("id")
        serializer = PerformanceListSerializer(performances, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res_data_sorted = sorted(res.data, key=lambda x: x["id"])
        serializer_data_sorted = sorted(serializer.data, key=lambda x: x["id"])

        for res_item, ser_item in zip(res_data_sorted, serializer_data_sorted):

            res_copy = {k: v for k, v in res_item.items() if k != "tickets_available"}
            ser_copy = {k: v for k, v in ser_item.items() if k != "tickets_available"}
            self.assertEqual(res_copy, ser_copy)


class ReservationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("user@test.com", "testpass")
        self.client.force_authenticate(self.user)
        self.performance = sample_performance()
        self.performance_with_taken_seats = sample_performance(
            theatre_hall=sample_theatre_hall(rows=10, seats_in_row=10),
            show_time="2025-09-01T20:00:00Z",
        )
        Ticket.objects.create(
            performance=self.performance_with_taken_seats,
            reservation=Reservation.objects.create(user=self.user),
            row=1,
            seat=1,
        )

    def test_create_reservation(self):
        payload = {
            "tickets": [
                {"row": 1, "seat": 2, "performance": self.performance.id},
                {"row": 1, "seat": 3, "performance": self.performance.id},
            ]
        }
        res = self.client.post(RESERVATION_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.count(), 2)

    def test_create_reservation_with_taken_seat(self):
        payload = {
            "tickets": [
                {
                    "row": 1,
                    "seat": 1,
                    "performance": self.performance_with_taken_seats.id,
                },
            ]
        }
        res = self.client.post(RESERVATION_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", res.data["tickets"][0])
        self.assertIn("unique", str(res.data["tickets"][0]["non_field_errors"]))

    def test_create_reservation_invalid_seat(self):
        payload = {
            "tickets": [
                {"row": 99, "seat": 99, "performance": self.performance.id},
            ]
        }
        res = self.client.post(RESERVATION_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Row must be in range", str(res.data))


class AdminPerformanceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@test.com", "testpass", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_performance_as_admin(self):
        play = sample_play()
        theatre_hall = sample_theatre_hall()
        payload = {
            "show_time": "2025-08-01T20:00:00Z",
            "play": play.id,
            "theatre_hall": theatre_hall.id,
        }
        res = self.client.post(PERFORMANCE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        performance = Performance.objects.get(id=res.data["id"])
        self.assertEqual(performance.play, play)
        self.assertEqual(performance.theatre_hall, theatre_hall)
