.. _manual_adfs:

===============================
ADFS (On premise) being removed
===============================

.. warning::

   The ADFS integration is being removed. Instead you can use the generic
   :ref:`OpenID Connect <manual_oidc>` integration. Open Zaak automatically migrates
   your ADFS/AAD configuration to the generic OIDC configuration.

   Note that you should update your application Redirect URI in ADFS/AAD - the path
   ``/adfs/callback`` should be changed into ``/oidc/callback``.

   Open Zaak 1.7.0 provides a redirect from the old to the new URL, which will be
   removed in Open Zaak 1.8.0.

Uninstalling
============

The uninstaller can be run from Open Zaak 1.8.0 onwards, after we have removed the
external dependencies.

.. tabs::

 .. group-tab:: single-server

   .. code-block:: bash

       $ docker exec openzaak-0 /app/bin/uninstall_adfs.sh

       BEGIN
       DROP TABLE
       DELETE 3
       COMMIT


 .. group-tab:: Kubernetes

   .. code-block:: bash

       $ kubectl get pods
       NAME                        READY   STATUS    RESTARTS   AGE
       cache-79455b996-jxk9r       1/1     Running   0          2d9h
       nginx-8579d9dfbd-gdtbf      1/1     Running   0          2d9h
       nginx-8579d9dfbd-wz6wn      1/1     Running   0          2d9h
       openzaak-7b696c8fd5-hchbq   1/1     Running   0          2d9h
       openzaak-7b696c8fd5-kz2pb   1/1     Running   0          2d9h

       $ kubectl exec openzaak-7b696c8fd5-hchbq -- /app/bin/uninstall_adfs.sh

       BEGIN
       DROP TABLE
       DELETE 3
       COMMIT
