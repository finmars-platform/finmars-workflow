import json
import random
import string

import factory
from faker import Faker

from workflow.models import Space, User, WorkflowTemplate

fake = Faker()


def random_code(length):
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("user_name")
    is_staff = factory.Faker("boolean")
    is_superuser = factory.Faker("boolean")


class SpaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Space

    name = factory.Faker("word")
    # realm code is word lengh 5 lettera or digits
    realm_code = factory.LazyAttribute(lambda _: f"realm{random_code(5)}")
    space_code = factory.LazyAttribute(lambda _: f"space{random_code(5)}")


class WorkflowTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkflowTemplate

    name = factory.Faker("word")
    user_code = factory.LazyAttribute(lambda _: f"{fake.word()}.{fake.word()}.{fake.word()}:{fake.word()}")
    notes = factory.Faker("text")
    data = factory.LazyAttribute(lambda _: json.dumps({"version": "2", "workflow": {}}))
    space = factory.SubFactory(SpaceFactory)
    owner = factory.SubFactory(UserFactory)
