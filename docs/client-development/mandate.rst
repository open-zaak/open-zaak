.. _client-development-mandate:

Management of cases on behalf of other party
============================================

.. note::
    This is an experimental feature and it doesn't rely on existing ZGW standards.


Cases can be initiated and managed by different parties. They can be individuals, organizations,
municipality employees, etc. ``Rol`` resource from Zaken API is used to store information
about such parties.

If the user is authenticated with Digid or eHerkenning, the meta information about it can be
saved into ``Rol.authenticatieContext``. The user can initiate the case on their own behalf,
but it's also possible to represent another party. Both Digid and eHerkenning support such mandates.

.. image:: _assets/machtiging.png
    :width: 100%
    :alt: Digid and eHerkenning authorized parties with and without mandates.


In the schema you can see all possible options for mandates for users:

1. An individual (``natuurlijk_persoon``) is authorized with Digid and initiates their own cases
2. An individual (``natuurlijk_persoon``) is authorized with Digid and initiates the case on
   behalf of another individual (Digid machtiging)
3. An employee of the organization (``niet_natuurlijk_persoon`` or ``vestiging``) is authorized with
   eHerkenning and initiates their own cases
4. An employee of the organization (``niet_natuurlijk_persoon`` or ``vestiging``) is authorized with
   eHerkenning and initiates the case on behalf of another individual (eHerkenning bewindvoering)
5. An employee of the organization (``niet_natuurlijk_persoon`` or ``vestiging``) is authorized with
   eHerkenning and initiates the case on behalf of another organization (eHerkenning ketenmachtiging)


Open Zaak ``/zaken/api/v1/rollen`` endpoint supports all these options. Here are examples how to use it.

Recipies to create rollen with mandates
---------------------------------------

General rules
^^^^^^^^^^^^^

* all information about mandates is stored in ``Rol.authenticatieContext``
* mandates are supported only for ``natuurlijk_persoon``, ``niet_natuurlijk_persoon`` and
  ``vestiging`` values of ``Rol.betrokkeneType``
* only ``digid`` and ``eherkenning`` are supported as sources for mandates
* an authorizee (``gemachtigde``) and a representee (``machtiginggever``) are defined by
  ``Rol.indicatieMachtiging`` attribute. If it's blank, that means that the party initiates
  their own case.
* for eHerkenning cases the employee details should be added to ``Rol.contactpersoonRol``
  attributes.

Validation rules
^^^^^^^^^^^^^^^^

* if ``representee`` is provided in ``authenticatieContext``, then:
    * ``indicatieMachtiging`` **MUST** be set to "gemachtigde"
    * ``mandate`` **MUST** be provided in the ``authenticatieContext``

* if ``betrokkeneType`` is ``natuurlijk_persoon``, then ``Rol.authenticatieContext.source``
  **MUST** be set to "digid"

* if ``betrokkeneType`` is ``niet_natuurlijk_persoon`` or ``vestiging``, then
  ``Rol.authenticatieContext.source`` **MUST** be set to "eherkenning"


Example API calls below are provided with required fields and dummy data, the focus is on the shape of
``authenticatieContext``.

1. DigiD / Without mandate
^^^^^^^^^^^^^^^^^^^^^^^^^^

**DigiD - initiator**

.. code:: http

    POST /zaken/api/v1/rollen HTTP/1.1
    Content-Type: application/json

    {
        "zaak": "http://example.com",
        "betrokkeneType": "natuurlijk_persoon",
        "roltype": "http://example.com/roltype-initiator",
        "roltoelichting": "Created zaak",
        "betrokkeneIdentificatie": {
            "inpBsn": "123456782"
        },
        "authenticatieContext": {
            "source": "digid",
            "levelOfAssurance": "urn:oasis:names:tc:SAML:2.0:ac:classes:MobileTwoFactorContract"
        }
    }


2. DigiD / With mandate
^^^^^^^^^^^^^^^^^^^^^^^

**DigiD - initiator**

The authorizee is the "initiator" of the case (cleared up from VNG github), the representee
is a "belanghebbende".

.. code:: http

    POST /zaken/api/v1/rollen HTTP/1.1
    Content-Type: application/json

    {
        "zaak": "http://example.com",
        "betrokkeneType": "natuurlijk_persoon",
        "roltype": "http://example.com/roltype-initiator",
        "roltoelichting": "Created zaak",
        "indicatieMachtiging": "gemachtigde",
        "betrokkeneIdentificatie": {
            "inpBsn": "123456782"
        },
        "authenticatieContext": {
            "source": "digid",
            "levelOfAssurance": "urn:oasis:names:tc:SAML:2.0:ac:classes:MobileTwoFactorContract"
            "representee": {
                "identifierType": "bsn",
                "identifier": "111222333"
            },
            "mandate": {
                "services": [
                    {"id": "5628edbd-333e-460d-8a69-8f083b8cf1b8"}
                ]
            }
        }
    }


**DigiD - belanghebbende**

.. code:: http

    POST /zaken/api/v1/rollen HTTP/1.1
    Content-Type: application/json

    {
        "zaak": "http://example.com",
        "betrokkeneType": "natuurlijk_persoon",
        "roltype": "http://example.com/roltype-belanghebbende",
        "roltoelichting": "Voogd",
        "indicatieMachtiging": "machtiginggever",
        "betrokkeneIdentificatie": {
            "inpBsn": "111222333"
            },
        "authenticatieContext": null
    }



3. eHerkenning / Without mandate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**eHerkenning - initiator (no branch)**

.. code:: http

    POST /zaken/api/v1/rollen HTTP/1.1
    Content-Type: application/json

    {
        "zaak": "http://example.com",
        "betrokkeneType": "niet_natuurlijk_persoon",
        "roltype": "http://example.com/roltype-initiator",
        "roltoelichting": "Created zaak",
        "contactpersoonRol": {
            "naam": "acting subject name"
        },
        "betrokkeneIdentificatie": {
            "innNnpId": "999999999"
        },
        "authenticatieContext": {
            "source": "eherkenning",
            "levelOfAssurance": "urn:etoegang:core:assurance-class:loa2plus",
            "actingSubject": "4B75A0EA107B3D36C82FD675B5B78CC2F181B22E33D85F2D4A5DA63452EE3018@2D8FF1EF10279BC2643F376D89835151"
        }
    }


**eHerkenning - initiator (branch)**

.. code:: http

    POST /zaken/api/v1/rollen HTTP/1.1
    Content-Type: application/json

    {
        "zaak": "http://example.com",
        "betrokkeneType": "vestiging",
        "roltype": "http://example.com/roltype-initiator",
        "roltoelichting": "Created zaak",
        "contactpersoonRol": {
            "naam": "acting subject name"
        },
        "betrokkeneIdentificatie": {
            "kvkNummer": "12345678",
            "vestigingsNummer": "123456789012"
        },
        "authenticatieContext": {
            "source": "eherkenning",
            "levelOfAssurance": "urn:etoegang:core:assurance-class:loa2plus",
            "actingSubject": "4B75A0EA107B3D36C82FD675B5B78CC2F181B22E33D85F2D4A5DA63452EE3018@2D8FF1EF10279BC2643F376D89835151"
        }
    }


4. eHerkenning / With mandate (bewindvoering)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**eHerkenning - initiator**

.. code:: http

    POST /zaken/api/v1/rollen HTTP/1.1
    Content-Type: application/json

    {
        "zaak": "http://example.com",
        "betrokkeneType": "vestiging",
        "roltype": "http://example.com/roltype-initiator",
        "roltoelichting": "Created zaak",
        "contactpersoonRol": {
            "naam": "acting subject name"
        },
        "indicatieMachtiging": "gemachtigde",
        "betrokkeneIdentificatie": {
            "kvkNummer": "12345678",
            "vestigingsNummer": "123456789012"
        },
        "authenticatieContext": {
            "source": "eherkenning",
            "levelOfAssurance": "urn:etoegang:core:assurance-class:loa2plus",
            "representee": {
                "identifierType": "bsn",
                "identifier": "111222333"
            },
            "actingSubject": "4B75A0EA107B3D36C82FD675B5B78CC2F181B22E33D85F2D4A5DA63452EE3018@2D8FF1EF10279BC2643F376D89835151"
            "mandate": {
                "role": "bewindvoerder",
                "services": [{
                    "id": "urn:etoegang:DV:00000001002308836000:services:9113",
                    "uuid": "34085d78-21aa-4481-a219-b28d7f3282fc"
                }]
            }
        }
    }


**eHerkenning - belanghebbende**

.. code:: http

    POST /zaken/api/v1/rollen HTTP/1.1
    Content-Type: application/json

    {
        "zaak": "http://example.com",
        "betrokkeneType": "natuurlijk_persoon",
        "roltype": "http://example.com/roltype-belanghebbende",
        "roltoelichting": "Persoon waarover bewind gevoerd wordt",
        "indicatieMachtiging": "machtiginggever",
        "betrokkeneIdentificatie": {
            "inpBsn": "111222333"
        },
        "authenticatieContext": null
    }


5. eHerkenning / With mandate (ketenmachtiging)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**eHerkenning - initiator**

.. code:: http

    POST /zaken/api/v1/rollen HTTP/1.1
    Content-Type: application/json

    {
        "zaak": "http://example.com",
        "betrokkeneType": "vestiging",
        "roltype": "http://example.com/roltype-initiator",
        "roltoelichting": "Created zaak",
        "contactpersoonRol": {
            "naam": "acting subject name"
        },
        "indicatieMachtiging": "gemachtigde",
        "betrokkeneIdentificatie": {
            "kvkNummer": "12345678",
            "vestigingsNummer": "123456789012"
        },
        "authenticatieContext": {
        "source": "eherkenning",
        "levelOfAssurance": "urn:etoegang:core:assurance-class:loa2plus",
        "representee": {
            "identifierType": "kvkNummer",
            "identifier": "99998888"
        },
        "actingSubject": "4B75A0EA107B3D36C82FD675B5B78CC2F181B22E33D85F2D4A5DA63452EE3018@2D8FF1EF10279BC2643F376D89835151"
        "mandate": {
            "services": [{
                "id": "urn:etoegang:DV:00000001002308836000:services:9113",
                "uuid": "34085d78-21aa-4481-a219-b28d7f3282fc"
            }]
            }
        }
    }


**eHerkenning - belanghebbende**

.. code:: http

    POST /zaken/api/v1/rollen HTTP/1.1
    Content-Type: application/json

    {
        "zaak": "http://example.com",
        "betrokkeneType": "niet_natuurlijk_persoon",
        "roltype": "http://example.com/roltype-belanghebbende",
        "roltoelichting": "Bedrijf dat de intermediair machtigt",
        "indicatieMachtiging": "machtiginggever",
        "betrokkeneIdentificatie": {
            "kvkNummer": "99998888"
        },
        "authenticatieContext": null
    }


Query patterns
--------------

Below are examples how to request zaken, authorized by different parties.

**DigiD**

1. Show me my cases (based on my BSN) opened for myself:

    .. code::

        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn=<ownBsn>
             &rol__machtiging=eigen


    Additionally ``rol.omschrijvingGeneriek`` can be used to determine the "initiator"
    of the case.

    .. code::

        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn=<ownBsn>
             &rol__machtiging=eigen
             &rol__omschrijvingGeneriek=initiator


2. Show me my cases (based on my BSN) opened by an authorizee on my behalf:

    .. code::

        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn=<ownBsn>
             &rol__machtiging=machtiginggever


    Additionally ``rol.omschrijvingGeneriek`` can be used to determine the "belanghebbende"
    of the case.

    .. code::

        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn=<ownBsn>
             &rol__omschrijvingGeneriek=belanghebbende


3. Show me the cases (based on my BSN) where I represent another party:

    .. code::

        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn=<ownBsn>
             &rol__machtiging=gemachtigde


    It's also possible to filter cases based on the level of assurance and to exclude
    results where levelOfAssurance is below some required value.

    .. code::

        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn=<ownBsn>
             &rol__machtiging=gemachtigde
             &rol__machtiging__loa=urn:oasis:names:tc:SAML:2.0:ac:classes:MobileTwoFactorContract


**eHerkenning**

Filters for eHerkenning authorized parties depend if it's an organization or the branch, therefore
there are two examples for each option.

1. Show me my cases (based on my KVK nummer) opened for myself:

    .. code::

        # organization
        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__nietNatuurlijkPersoon__kvk_Nummer=<ownKvk>
             &rol__machtiging=eigen

        # branch
        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__vestiging__kvkNummer=<ownKvk>
             &rol__machtiging=eigen


    For organizations it's also possible to filter on their RSIN:

    .. code::

        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__nietNatuurlijkPersoon__innNnpId=<ownRsin>
             &rol__machtiging=eigen


    Additionally ``rol.omschrijvingGeneriek`` can be used to determine the "initiator"
    of the case

    .. code::

        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__nietNatuurlijkPersoon__kvk_Nummer=<ownKvk>
             &rol__machtiging=eigen
             &rol__omschrijvingGeneriek=initiator


2. Show me my cases (based on my KVK nummer) opened by an authorizee on my behalf:

    .. code::

        # organization
        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__nietNatuurlijkPersoon__kvk_Nummer=<ownKvk>
             &rol__machtiging=machtiginggever

        # branch
        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__vestiging__kvkNummer=<ownKvk>
             &rol__machtiging=machtiginggever


    Additionally ``rol.omschrijvingGeneriek`` can be used to determine the "belanghebbende"
    of the case.

    .. code::

        # organization
        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__nietNatuurlijkPersoon__kvk_Nummer=<ownKvk>
             &rol__omschrijvingGeneriek=belanghebbende


3. Show me the cases (based on my KVK nummer) where I represent another party:

    .. code::

        # organization
        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__nietNatuurlijkPersoon__kvk_Nummer=<ownKvk>
             &rol__machtiging=gemachtigde

        # branch
        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__vestiging__kvkNummer=<ownKvk>
             &rol__machtiging=gemachtigde


    It's also possible to filter cases based on the level of assurance and to exclude
    results where levelOfAssurance is below some required value.

    .. code::

        GET /zaken/api/v1/zaken?
             rol__betrokkeneIdentificatie__nietNatuurlijkPersoon__kvk_Nummer=<ownKvk>
             &rol__machtiging=gemachtigde
             &rol__machtiging__loa=urn:etoegang:core:assurance-class:loa2plus


**Filters for rollen**

It's also possible to make requests with such filters for ``zaken/api/v1/rollen`` endpoint
to retrieve details of the parties. For example, show me the rollen (based on my BSN) where I represent another party:

    .. code::

        GET /zaken/api/v1/rollen?
             betrokkeneIdentificatie__natuurlijkPersoon__inpBsn=<ownBsn>
             &machtiging=gemachtigde
             &machtiging__loa=urn:oasis:names:tc:SAML:2.0:ac:classes:MobileTwoFactorContract


.. note::

   If it's possible that your case has several autorizees and representees, use ``zaken/api/v1/rollen`` endpoint
   for searching such cases. Filters for the ``zaken/api/v1/zaken`` endpoint don't depend on each other, so
   it's possible to show cases where one query parameter belongs to one role and another parameter belongs to
   another role. In such cases either use ``zaken/api/v1/zaken`` endpoint and add extra filtering on the client
   side or use ``zaken/api/v1/rollen`` endpoint, where all query parameters are applied to each role.


Useful documentation
--------------------

* the shape of ``Rol.authenticatieContext`` is based on `authentication-context-schemas <https://github.com/maykinmedia/authentication-context-schemas/>`_
* Clarifications on mandates for roles at `VNG Github <https://github.com/VNG-Realisatie/gemma-zaken/issues/2435>`_
* `Digid machtiging  <https://www.logius.nl/domeinen/toegang/digid-machtigen/documentatie/digid-machtigen-functionele-beschrijving>`_
* `eHerkenning ketenmachtiging <https://www.eherkenning.nl/nl/machtigen/ketenmachtiging>`_
