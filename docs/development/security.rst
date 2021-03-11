Security measures in Open Zaak
==============================

The following is a non-exhaustive list of configurations in Open Zaak to enhance
security.

nginx template considerations
-----------------------------

When deploying Open Zaak on a VM, nginx is used as a reverse proxy. A number of headers
are set in the virtual host:

``Referrer-Policy: "same-origin";``
    the ``HTTP_REFERER`` header is sent only to Open Zaak pages

``X-Content-Type-Options: "nosniff";``
    protects against user-uploaded content, which is relevant because of the Documents
    API and serving of that user content

``X-XSS-Protection: "1; mode=block";``
    note that this is not honored by most browsers anymore, but it doesn't hurt to
    include it

``Content-Security-Policy``
    opt-in, configure the deployment playbook accordingly

``Feature-Policy: "autoplay 'none'; camera 'none'" always;``
    there's no need for these :-)

Open Zaak settings
------------------

``X-Frame-Options`` is set to ``DENY``
    no (i)frames are allowed at all
