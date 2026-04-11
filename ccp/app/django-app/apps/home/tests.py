"""Smoke tests for the home landing page."""

from django.test import Client, TestCase


class HomePageTests(TestCase):
    """Verify the Portuguese landing page renders successfully."""

    def test_index_renders_portuguese_header(self) -> None:
        response = Client().get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ccp - Centrifugal Compressor", response.content)
        self.assertIn("compressores centr".encode("utf-8"), response.content)
