# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from rest_framework import status


class CRUDAssertions:
    def assertCreateBlocked(self, url: str, data: dict):
        with self.subTest(action="create"):
            response = self.client.post(url, data)

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

    def assertUpdateBlocked(self, url: str):
        with self.subTest(action="update"):
            detail = self.client.get(url).data

            response = self.client.put(url, detail)

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

    def assertPartialUpdateBlocked(self, url: str):
        with self.subTest(action="partial_update"):
            response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def assertDestroyBlocked(self, url: str):
        with self.subTest(action="destroy"):
            response = self.client.delete(url)

            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, response.data
            )

    def assertCreateAllowed(self, url: str, data: dict):
        with self.subTest(action="create"):
            response = self.client.post(url, data)

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )

    def assertUpdateAllowed(self, url: str):
        with self.subTest(action="update"):
            detail = self.client.get(url).data

            response = self.client.put(url, detail)

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def assertPartialUpdateAllowed(self, url: str):
        with self.subTest(action="partial_update"):
            response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def assertDestroyAllowed(self, url: str):
        with self.subTest(action="destroy"):
            response = self.client.delete(url)

            self.assertEqual(
                response.status_code, status.HTTP_204_NO_CONTENT, response.data
            )
