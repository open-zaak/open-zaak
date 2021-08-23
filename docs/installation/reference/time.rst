.. _installation_reference_time:

=================
Dealing with time
=================

Dealing with time is a hard problem - the impression is that time is always incrementing
and consistent, but that's not the case when dealing with networks and computers in
general. Common examples are leap seconds and server or client clock drift.

General recommendations
=======================

In general, we advise to make use of `NTP`_ services for both client and server. If
possible, both client and server should use the *same* services so that their clocks are
in sync.

Where Open Zaak deals with time-aspects
=======================================

Open Zaak deals with time-based validations in a number of places, of which you can
configure how Open Zaak deals with them for a subset of these places.

API resource validation
-----------------------

Following the API standard, in certain places validation takes places that a date(time)
must be in the future or must be in the past (= may not be in the future). This
validation is performed against the server time.

JWT validation
--------------

API calls make use of JSON Web Tokens (JWT) for the authentication aspect (=which client
is making this request and is this client who it claims to be). One of the characteristics
of JWT's is that they are stateless and short-lived, therefore, the validity of a JWT
involves checking against time.

Common claims in JWT's are ``iat`` (issued at), ``nbf`` (not before) and ``exp``
(expiry). Clock drift can cause a JWT that's valid on the client to be considered not
valid (yet, or anymore) on the server, leading to unexpected HTTP 403 errors.

In Open Zaak, you can configure ``JWT_LEEWAY`` which allows you to specify the leeway
in seconds. This value should be greater than the difference between server and client
clock, but be careful to not make the value too large because that compromises security
(i.e. - a token is valid longer than intended).

Additionally, with Open Zaak the ``iat`` claim **must** be present, and it is validated
against ``JWT_EXPIRY`` which determines how long a token is considered valid. The
``JWT_LEEWAY`` configuration is also applied to this.

.. _NTP: https://en.wikipedia.org/wiki/Network_Time_Protocol
