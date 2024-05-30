.. _installation_cmis:

CMIS adapter
============

In a default installation of Open Zaak, any documents created through the
`Documenten API`_ are stored on disk and their metadata is stored in the
database. However, it is also possible to store these documents in a Document
Management System (DMS) using the CMIS standard.

.. _`Documenten API`: https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/VNG-Realisatie/documenten-api/1.3.0/src/openapi.yaml

The CMIS adapter converts API calls to the Documenten API in Open Zaak, to CMIS
calls which are sent to the DMS to retrieve, create, update and delete
documents. This way, the documents are stored in, or retrieved from, the DMS
and not in or from Open Zaak.

CMIS support
------------

`CMIS 1.0`_ and `CMIS 1.1`_ have various CMIS protocol bindings that can be
used. Although according to the CMIS specification repositories must implement
Web Services and AtomPub bindings, some DMS implementation only support one
and/or recommend the newer Browser bindings.

.. _`CMIS 1.0`: https://docs.oasis-open.org/cmis/CMIS/v1.0/cmis-spec-v1.0.html
.. _`CMIS 1.1`: https://docs.oasis-open.org/cmis/CMIS/v1.1/CMIS-v1.1.html

+----------------------+-----------+-----------+
|                      |  CMIS 1.0 |  CMIS 1.1 |
+======================+===========+===========+
| Web Services binding | Supported |  Untested |
+----------------------+-----------+-----------+
| AtomPub binding      |  Untested |  Untested |
+----------------------+-----------+-----------+
| Browser binding      |    N/A    | Supported |
+----------------------+-----------+-----------+

CMIS support is built in Open Zaak using the `CMIS adapter library`_. For an
up-to-date list of supported CMIS versions and libraries, please see this
project's documentation.

.. warning::
   The CMIS adapter is currently an experimental feature. While we have
   extensive unit test coverage with `Alfresco`_, we require more "real world"
   testing before we can label the feature as stable.

.. _`Alfresco`: https://www.alfresco.com/ecm-software/alfresco-community-editions

Using the CMIS adapter
----------------------

1. Create a mapping file to match Documenten API attributes to custom
   properties in your DMS model. The format is explained in the
   `CMIS adapter library`_ *Mapping configuration* documentation.

   You can use our `default CMIS mapping`_  for inspiration or just use these
   as defaults.

   .. _`default CMIS mapping`: https://github.com/open-zaak/open-zaak/blob/master/config/cmis_mapper.json
   .. _`Alfresco model`: https://github.com/open-zaak/alfresco-content-model/blob/main/openzaak-alfresco-platform/src/main/resources/alfresco/module/openzaak-alfresco-platform/model/alfresco-zsdms-model.xml

2. Make sure the content model is loaded in your DMS and matches the CMIS
   mapping described in step 1. It's important that all attributes are present.
   Some need to be indexed to allow the proper CMIS queries to be executed.

   You can use our `Alfresco model`_ that matches the default mapping. The
   detailed explanation is described in the `CMIS adapter library`_
   *DMS Content model configuration* documentation.

3. Enable the CMIS adapter. In the environment (or ``.env`` file), add or
   update the variable ``CMIS_ENABLED`` and ``CMIS_MAPPER_FILE``:

    .. code-block:: bash

        # Enables the CMIS-backend and the Open Zaak admin interface for configuring
        # the DMS settings.
        CMIS_ENABLED = True

        # Absolute path to the mapping of Documenten API attributes to (custom)
        # properties in your DMS model.
        CMIS_MAPPER_FILE = /path/to/cmis_mapper.json


4. *Optional*: enable URL mapping. In DMSs such as Corsa, queryable text fields can only be up to 100 characters long.
   However, documents in the Document API have URLs associated with it that are longer.
   The URL mapper feature shrinks the URLs so that they fit in queryable text fields.

   In the environment (or ``.env`` file), add or update the variable ``CMIS_URL_MAPPING_ENABLED``:

    .. code-block:: bash

        # Enables URL mapping in the CMIS-backend so that the URLs saved in
        # the DMS are shorter than 100 chars.
        CMIS_URL_MAPPING_ENABLED = True

5. You will need to restart Open Zaak for these changes to take effect.

6. Login to the Open Zaak admin interface (``/admin/``) as superuser.

7. Navigate to **Configuratie > CMIS configuration** and fill in all relevant
   fields.

.. image:: ../assets/cmis_config.png
    :width: 100%
    :alt: CMIS Configuration

8. If the URL mapping feature was enabled (point 4. above), then the mappings between the original and short
   version of a URL need to be defined. In the section **URL MAPPINGS**, fill in the field **LONG PATTERN**
   with the original URL (in format ``https://<domain>[/subpath]``) and the **SHORT PATTERN** with the URL with
   shortened domain and subpath (in format ``https://<short domain>``). The short pattern field can be at most 15
   characters. The scheme (http or https) should be the same for both the long and short pattern.

    .. warning::
        Once a mapping has been defined, it **cannot** be updated or deleted.

.. image:: ../assets/cmis_url_mapping_config.png
    :width: 100%
    :alt: CMIS URL Mapping configuration

9. Save the configuration with **Opslaan en opnieuw bewerken**.

10. You will see the **CMIS connection** status shows **OK** if everything went well.

.. _`CMIS adapter library`: https://github.com/open-zaak/cmis-adapter


Additional notes on creating documents
--------------------------------------

Depending on whether the CMIS adapter is enabled, there is a difference in behaviour for creating documents with an empty identification field.

If the CMIS adapter is disabled, the procedure to automatically generate the identification is as follows:

1. The prefix ``DOCUMENT`` is combined with the year of creation of the document. For example: ``DOCUMENT-2020-``
2. All existing documents are searched to find all those with an identification field that starts with the generated prefix. These would for example be ``DOCUMENT-2020-0000000001``, ``DOCUMENT-2020-0000000002``, ``DOCUMENT-2020-0000000003``.
3. The new document is given an identification field with a unique number that is different from those of all the other documents. This would for example be ``DOCUMENT-2020-0000000004``.

The search done in point 2. requires an SQL LIKE clause, which is not supported by all DMSs. For this reason, if the CMIS adapter is in use, the automatically generated identification field will be equal to the document UUID.

