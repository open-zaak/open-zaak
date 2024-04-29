from django.test import TestCase

from django.contrib.auth.models import Permission, Group
from .factories import UserFactory


class AuthorizationMatrixTests(TestCase):
