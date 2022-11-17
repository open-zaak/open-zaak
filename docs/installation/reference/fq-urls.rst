.. _installation_reference_fq_urls:

Deploying behind API gateways
=============================

Open Zaak relies on fully qualified URLs - that is, URLs with scheme, host/domain, and
path segments - to locate resources, both provided by the Open Zaak instance itself or
external resource.

API resources are identified by these fully qualified URLs and determine if Open Zaak
can do a database lookup (because the resource is owned by Open Zaak) or if a network
call needs to be made to retrieve it (e.g. a reference to a geometric object in the BAG).

This requires that Open Zaak is deployed on "a canonical" domain. Most deployments are
automatically configured correctly for this, but API gateways tend to complicate this.

This reference documents your configuration options when you are using advanced network
topology, such as deploying behind an API gateway (like NLX) without also 'publicly'
exposing the service.

How Open Zaak builds URLs
-------------------------

Normally Open Zaak builds absolute URIs based on the context of the incoming HTTP
request by looking at the ``Host`` header. This allows you to expose the service on
multiple host names (e.g. internal Kubernetes service names and a public host name
protected with TLS certificates).

Reverse proxies (such as Kubernetes ingresses) typically take the incoming HTTP request
and relay this information in the ``X-Forwarded-Host`` header which is received by
Open Zaak.

API gateways
------------

Not all API gateways correctly rewrite the host or even path information from the
original incoming request.

Consider the following scenario:

* API gateway is "publicly" accessible at ``gateway.example.com``
* the Zaken API is exposed at ``https://gateway.example.com/zaken/api/v1/``
* internally, the Open Zaak service is available on the DNS name
  ``open-zaak.namespace.svc.cluster.local``

1. The client then makes a request ``GET https://gateway.example.com/zaken/api/v1/``
2. The API gateway translates this into a
   ``GET http://open-zaak.namespace.svc.cluster.local:8000``
3. Open Zaak gets the ``Host: open-zaak.namespace.svc.cluster.local`` header, and will
   build all response data URLs based on this host.

This is problematic, as the client cannot handle these internal service names and use
them for follow up API calls.

Additionally, there may be another layer of abstraction where the client hits a
URL/service that is specific to that client, which is the case with NLX outways.

Forcing host rewrites
---------------------

To mitigate this, you can force Open Zaak to rewrite the ``Host`` header if this cannot
be solved at the infrastructure level, by using two settings:

* ``OPENZAAK_DOMAIN``, which specifies the canonical host of your Open Zaak instance.
  Any incoming HTTP request will then be rewritten as if this was the host requested by
  the client.
* ``OPENZAAK_REWRITE_HOST`` must be set to ``True`` for this to take effect, and this
  setting conflict with the ``USE_X_FORWARDED_HOST`` setting. The latter will tell Open
  Zaak to trust and use the value set by reverse proxy in front of Open Zaak. It is
  ignored if you force rewrites with ``OPENZAAK_DOMAIN``

Absolute URLs outside of HTTP requests contexts
-----------------------------------------------

At times Open Zaak needs to build absolute URLs without an HTTP request context being
available, such as command-line scripts or certain admin synchronization steps.

If the ``OPENZAAK_DOMAIN`` is not empty, then this value will be used for those URLs,
otherwise the ``Site`` configuration (from the admin) will be used.
