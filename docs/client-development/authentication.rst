.. _client-development-auth:

Authentication and authorization
================================

All endpoints are authorization protected, per the upstream `Standard`_.

Open Zaak uses the described authentication and authorization mechanism based on
JSON Web Tokens (JWT in short).

To connect to Open Zaak, you have received a Client ID and a Secret, which you must use
to build a JWT. You can read more about JWT's on https://jwt.io

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

Generating JWT Examples:
------------------------

Example of how to generate JWT tokens in Java, JavaScript, PHP and Python with example libraries.
There is a link to a list of more libraries for these and other languages below.

.. tabs::

    .. group-tab:: Python

        Using the `pyjwt`_ for python.

        .. code-block:: python

            import jwt
            import requests
            import time

            CLIENT_ID = "example"
            SECRET = "secret"

            payload = {
                "iss": CLIENT_ID,
                "iat": int(time.time()),  # current time in seconds
                "client_id": CLIENT_ID,
                "user_id": "eample@example.com",
                "user_representation": "Example Name",
            }
            jwt_token = jwt.encode(payload, SECRET, algorithm="HS256")

            # add token token to the authentication HTTP header of your request library
            zaaktype_url = "https://openzaak.gemeente.local/catalogi/api/v1/zaaktypen/4acb5ab8-f189-4559-b18a-8a54553a74ff"
            headers = {"Authorization": "Bearer {token}".format(token=jwt_token)}
            response = requests.get(
                zaaktype_url,
                headers=headers,
            )
            print(response.json())

    .. group-tab:: JavaScript

        In JavaScript, most of the token can be generated with the `jsonwebtoken`_ package.

        .. code-block:: javascript

            import jwt from 'jsonwebtoken';

            const CLIENT_ID = 'example';
            const SECRET = 'secret';

            const getJWT = () => {
              return jwt.sign(
                {
                    // iat: placed automatically
                    client_id: CLIENT_ID,
                    user_id: "eample@example.com",
                    user_representation: "Example Name"
                },
                SECRET,
                {
                  algorithm: 'HS256',
                  issuer: CLIENT_ID, // iss in payload
                }
              );
            };


            var jwt_token = getJWT()

            // add token token to the authentication HTTP header of fetch
            const zaaktype_url = "https://openzaak.gemeente.local/catalogi/api/v1/zaaktypen/4acb5ab8-f189-4559-b18a-8a54553a74ff";
            fetch(
              zaaktype_url,
              {
                method: 'get',
                headers: {
                  'Authorization': `Bearer ${jwt_token}`,
                  'Accept': 'application/json',
                },
              }
            ).then(response => {
              console.log(response);
            });

    .. group-tab:: PHP

        The `php-jwt`_ package is available for PHP which can generate the JWT token for you.

        .. code-block:: php

            use Firebase\JWT\JWT;

            $CLIENT_ID = "example";
            $SECRET = "secret";

            $payload = [
                "iss" => $CLIENT_ID,
                "iat" => time(),
                "client_id" => $CLIENT_ID,
                "user_id" => "eample@example.com",
                "user_representation" => "Example Name",
            ];

            $jwt_token = JWT::encode($payload, $SECRET, "HS256");
            // add token token to the authentication HTTP header of your request library
            $headers = [
                "Authorization" => "Bearer " . $jwt_token,
            ];
            $zaaktype_url ="https://openzaak.gemeente.local/catalogi/api/v1/zaaktypen/4acb5ab8-f189-4559-b18a-8a54553a74ff";

            $client = new \GuzzleHttp\Client();
            $response = $client->request("GET", $zaaktype_url, [
                "headers" => $headers,
                'http_errors' => false
            ]);

            echo $response->getBody();

    .. group-tab:: Java

        The `java-jwt`_ package is available for java which can generate the JWT token for you.

        .. code-block:: java

            final String CLIENT_ID = "example";
            final String SECRET = "secret";

            Algorithm algorithm = Algorithm.HMAC256(SECRET);

            String jwt_token = JWT.create()
                .withIssuer(CLIENT_ID) // iss
                .withIssuedAt(new Date()) // iat
                .withClaim("client_id", CLIENT_ID)
                .withClaim("user_id", "eample@example.com")
                .withClaim("user_representation", "Example Name")
                .sign(algorithm);

            // add token token to the authentication HTTP header of your request library
            try {
                URL zaaktype_url = new URL("https://openzaak.gemeente.local/catalogi/api/v1/zaaktypen/4acb5ab8-f189-4559-b18a-8a54553a74ff");
                URLConnection zaaktype_connection = zaaktype_url.openConnection();

                zaaktype_connection.setRequestProperty ("Authorization", "Bearer "+jwt_token);
                zaaktype_connection.addRequestProperty("Accept", "application/json");

                BufferedReader in = new BufferedReader(
                        new InputStreamReader(
                            zaaktype_connection.getInputStream()));
                // do stuff with buffer

            } catch (Exception exception){
                // exception code
            }

Useful Links

   * `More indepth JWT Explanation`_
   * `JWT implementations for various languages`_

.. _More indepth JWT Explanation: https://jwt.io/introduction
.. _JWT implementations for various languages: https://jwt.io/libraries

.. _pyjwt: https://pypi.org/project/PyJWT/
.. _jsonwebtoken: https://www.npmjs.com/package/jsonwebtoken
.. _php-jwt: https://github.com/firebase/php-jwt
.. _java-jwt: https://github.com/auth0/java-jwt
