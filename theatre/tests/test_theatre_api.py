from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from theatre.models import Play, Genre, Actor
from theatre.serializers import PlayListSerializer, PlayDetailSerializer

PLAY_URL = reverse("theatre:play-list")  # name з urls.py
def detail_url(play_id):
    return reverse("theatre:play-detail", args=[play_id])

def sample_play(**params):
    defaults = {
        "title": "Sample Play",
        "description": "A touching drama",
        "duration": 120,
    }
    defaults.update(params)
    return Play.objects.create(**defaults)


class PublicPlayTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(PLAY_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivatePlayTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@test.com", "testpass"
        )
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
        genre1 = Genre.objects.create(name="Drama")
        genre2 = Genre.objects.create(name="Comedy")
        play1 = sample_play(title="Play 1")
        play2 = sample_play(title="Play 2")
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