.. _client-development-auth:

Authentication and authorization
================================

All endpoints are authorization protected, per the upstream `Standard`_.

Open Zaak uses the described authentication and authorization mechanism based on
JSON Web Tokens (JTW in short). You can read more about JWT's on https://jwt.io

To connect to Open Zaak, you have received a Client ID and a Secret, which you must use
to build a JWT.

The payload of the JWT is:

.. code-block:: json

    {
        "iss": "<value of Client ID>",
        "iat": 1602857301,
        "client_id": "<value of Client ID>",
        "user_id": "<unique user ID of the actual end user>",
        "user_representation": "<e.g. the name of the actual end user>"
    }

The JWT must be generated with the ``HS256`` algorithm and signed with the secret you
received. ``iat`` is the Unix timestamp when token-creation happened.

Next, for every API call you make, you must include this token in the appropriate header:

.. code-block:: none

    Authorization: Bearer <jwt>

An example:
-----------

Given a Client ID ``docs`` and secret ``example-secret``, the header of the JWT is:

.. code-block:: json

    {
        "typ": "JWT",
        "alg": "HS256"
    }

The payload is:

.. code-block:: json

    {
      "iss": "docs",
      "iat": 1602857301,
      "client_id": "docs",
      "user_id": "docs@example.com",
      "user_representation": "Documentation Example"
    }

Which leads to the following JWT:

.. code-block:: none

    eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJkb2NzIiwiaWF0IjoxNjAyODU3MzAxLCJjbGllbnRfaWQiOiJkb2NzIiwidXNlcl9pZCI6ImRvY3NAZXhhbXBsZS5jb20iLCJ1c2VyX3JlcHJlc2VudGF0aW9uIjoiRG9jdW1lbnRhdGlvbiBFeGFtcGxlIn0.DZu7E780xG4zqRiT8ZhrBeMudz45301wNVDT0ra-Iyw

This would then be used in an API call like:

.. code-block:: http

    GET https://test.openzaak.nl/besluiten/api/v1/besuiten HTTP/1.1
    Host: test.open-zaak.nl
    Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJkb2NzIiwiaWF0IjoxNjAyODU3MzAxLCJjbGllbnRfaWQiOiJkb2NzIiwidXNlcl9pZCI6ImRvY3NAZXhhbXBsZS5jb20iLCJ1c2VyX3JlcHJlc2VudGF0aW9uIjoiRG9jdW1lbnRhdGlvbiBFeGFtcGxlIn0.DZu7E780xG4zqRiT8ZhrBeMudz45301wNVDT0ra-Iyw

.. warning::

    Note that you are expected to generate a JWT almost for every call! Open Zaak by
    default expires JWT's one hour past the ``iat`` timestamp, and for audit-purposes,
    the ``user_id`` and ``user_representation`` claims should match the end-user of
    the application.

.. _Standard: https://vng-realisatie.github.io/gemma-zaken/
