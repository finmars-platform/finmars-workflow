import random
import string

from django.test import TestCase


class BaseTestCase(TestCase):
    @classmethod
    def random_string(cls, length: int = 10) -> str:
        return "".join(
            random.SystemRandom().choice(string.ascii_uppercase) for _ in range(length)
        )
