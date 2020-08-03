.. _installation_cmis:

The CMIS adapter
================

In a default installation of Open Zaak, any documents created through the
`Documenten API`_ are stored on disk and their metadata is stored in the database.
However, it is also possible to store these documents in a Document Management System
(DMS) using the CMIS standard.

Instead of storing the documents, the CMIS adapter converts API calls to CMIS requests
which are sent to the DMS to create, update and delete documents. This way, the
documents are stored in the DMS.

There are currently two supported CMIS bindings:

    1. The browser binding: which uses CMIS version 1.1. This is a JSON-based binding.
    2. The web service binding: which uses CMIS version 1.0. This binding is based on the SOAP protocol.

.. _`Documenten API`: https://documenten-api.vng.cloud/api/v1/schema/

.. warning::
   The CMIS adapter is currently an experimental feature. While we have extensive unit
   test coverage with Alfresco, we require more "real world" testing before we can
   label the feature as stable.

Using the CMIS adapter
----------------------

In order to use the CMIS adapter, the setting ``CMIS_ENABLED`` should be set to ``True``.
This can be done in the ``.env`` file.
Then, the following details need to be configured through the Admin interface of Open Zaak:

    1. The client URL
    2. The binding
    3. In case the browser binding is used, the time zone. By default this is set to UTC.
    4. The client username and password
    5. The name of the main folder in the Document Management System (DMS) where
       documents are going to be created

These can be configured under **Configuratie > CMIS configuration**. An example
configuration could be:

    1. Client URL: ``http://example.com:8888/alfresco/api/-default-/public/cmis/versions/1.1/browser``
    2. Binding: ``Browser binding (CMIS 1.1)``
    3. Time zone: ``UTC``
    4. Client Username: ``Admin``
    5. Client Password: ``SomeSecretPassw0rd``
    6. Main folder name: ``DRC``

    .. note::

        If documents are stored in one DMS and later a different DMS is used, the documents will *not* be automatically
        accessible in the new DMS. They will have to be transferred to the new DMS.

The CMIS mapper
---------------

Before a CMIS request can be performed, each attribute passed via the Document API has
to be mapped to a CMIS property.

The customised document model used in the DMS is defined in a XML file, where all the
properties of the document are specified. An example XML file is provided in
``extension/alfresco-zsdms-model.xml``.

The mapping between the Document API attributes and the names used in the XML can be
found in ``config/cmis_mapper.json``.

The keys are the names of the attributes in the Document API, while the values are the
names used in CMIS content model.

If a different custom document model is used, then the mapper file also needs to be
updated. The path to the new mapper file is specified via the setting
``CMIS_MAPPER_FILE``, which can be specified in the ``.env`` file.

Content model requirements
++++++++++++++++++++++++++

CMIS content models define a number of properties that are important for the correct
functionining of the adapter.

* Notably, the defined `Object-Type`_ must have the attribute ``queryable`` set to
  ``TRUE``, otherwise errors will pop up when we query for documents using CMIS queries.

* Additionally, a number of *properties* on the `Document Object`_ must be ``queryable``
  to use them in the ``WHERE`` clauses of the CMIS queries. In particular, this spans
  the following attributes:

    - ``bestandsnaam``
    - ``bronorganisatie``
    - ``identificatie``
    - ``informatieobjecttype``
    - ``titel``
    - ``link``
    - ``versie``
    - ``creatiedatum``
    - ``begin_registratie``

.. todo:: More properties are marked as 'index' in the shipped content model, but it's
   unclear if they're actually used at the moment.

Example CMIS request with browser binding
-----------------------------------------

The example data below shows what data is sent by Open Zaak when a CMIS request is
performed to create different objects with the browser binding.

The objects are created with a ``POST`` request to the url of the root folder.
The url of the root folder is obtained by appending ``/root/`` to the client url configured in the
Admin interface of Open Zaak.

For example, if the client url has been set to
``http://example.com/alfresco/api/-default-/public/cmis/versions/1.1/browser``,
then the root folder url is
``http://example.com/alfresco/api/-default-/public/cmis/versions/1.1/browser/root``.

Within the root folder, all content created by Open Zaak will be in a folder whose name
is specified in the configuration (by default ``DRC``).

The username and passwords used are those specified in the CMIS configuration section
of the Admin interface.

**Document objects (EnkelvoudigInformatieObject)**

The data below is an example of what is sent from Open Zaak to create a document object according to the default document model.
The first property (``objectId``) is the ID of the folder that will contain the new document.

    .. code-block::

        POST http://example.com/alfresco/api/-default-/public/cmis/versions/1.1/browser/root
        User-Agent: python-requests/2.21.0
        Accept-Encoding: gzip, deflate
        Accept: application/json
        Connection: keep-alive
        Content-Length: 1241
        Content-Type: x-www-form-urlencoded
        Authorization: Basic YWRtaW46YWRtaW4=

        objectId=02bc165a-4f55-4d65-818a-e0b9d4ace38f&cmisaction=createDocument&propertyId%5B0%5D=cmis%3Aname&propertyValue%5B0%5D=some+titel-HWVLOF&propertyId%5B1%5D=cmis%3AobjectTypeId&propertyValue%5B1%5D=D%3Adrc%3Adocument&propertyId%5B2%5D=drc%3Adocument__identificatie&propertyValue%5B2%5D=6cd3cf4a-320d-4167-a192-fb33a34184ac&propertyId%5B3%5D=drc%3Adocument__bronorganisatie&propertyValue%5B3%5D=275318941&propertyId%5B4%5D=drc%3Adocument__creatiedatum&propertyValue%5B4%5D=2018-06-27T00%3A00%3A00.000Z&propertyId%5B5%5D=drc%3Adocument__titel&propertyValue%5B5%5D=some+titel&propertyId%5B6%5D=drc%3Adocument__auteur&propertyValue%5B6%5D=some+auteur&propertyId%5B7%5D=drc%3Adocument__formaat&propertyValue%5B7%5D=some+formaat&propertyId%5B8%5D=drc%3Adocument__taal&propertyValue%5B8%5D=nld&propertyId%5B9%5D=drc%3Adocument__informatieobjecttype&propertyValue%5B9%5D=http%3A%2F%2Ftestserver%2Fcatalogi%2Fapi%2Fv1%2Finformatieobjecttypen%2F4123f2e5-8201-46a9-9030-3d629ca5baeb&propertyId%5B10%5D=drc%3Adocument__vertrouwelijkaanduiding&propertyValue%5B10%5D=openbaar&propertyId%5B11%5D=drc%3Adocument__beschrijving&propertyValue%5B11%5D=old&propertyId%5B12%5D=drc%3Adocument__begin_registratie&propertyValue%5B12%5D=2020-06-23T13%3A02%3A11.000Z

The data present in the body is also shown below in a more readable format:

    .. code-block::

        {
            'objectId': '5353495a-3441-42d5-bf52-f9388dc0eef8',
            'cmisaction': 'createDocument',
            'propertyId[0]': 'cmis:name',
            'propertyValue[0]': 'some titel-4IP28I',
            'propertyId[1]': 'cmis:objectTypeId',
            'propertyValue[1]': 'D:drc:document',
            'propertyId[2]': 'drc:document__identificatie',
            'propertyValue[2]': UUID('e6b0499e-c9ee-4473-b4fc-7f942564b2dc'),
            'propertyId[3]': 'drc:document__bronorganisatie',
            'propertyValue[3]': '768254103',
            'propertyId[4]': 'drc:document__creatiedatum',
            'propertyValue[4]': '2018-06-27T00:00:00.000Z',
            'propertyId[5]': 'drc:document__titel',
            'propertyValue[5]': 'some titel',
            'propertyId[6]': 'drc:document__auteur',
            'propertyValue[6]': 'some auteur',
            'propertyId[7]': 'drc:document__formaat',
            'propertyValue[7]': 'some formaat',
            'propertyId[8]': 'drc:document__taal',
            'propertyValue[8]': 'nld',
            'propertyId[9]': 'drc:document__informatieobjecttype',
            'propertyValue[9]': 'http://testserver/catalogi/api/v1/informatieobjecttypen/5b020631-8fd1-4f88-a237-b605f715e168',
            'propertyId[10]': 'drc:document__vertrouwelijkaanduiding',
            'propertyValue[10]': 'openbaar',
            'propertyId[11]': 'drc:document__beschrijving',
            'propertyValue[11]': 'old',
            'propertyId[12]': 'drc:document__begin_registratie',
            'propertyValue[12]': '2020-06-22T11:26:44.000Z',
        }


**Usage rights objects (Gebruiksrechten)**

The data below is an example of what is sent from Open Zaak to create a usage right object.

    .. code-block::

        POST http://example.com/alfresco/api/-default-/public/cmis/versions/1.1/browser/root
        User-Agent: python-requests/2.21.0
        Accept-Encoding: gzip, deflate
        Accept: application/json
        Connection: keep-alive
        Content-Length: 706
        Content-Type: x-www-form-urlencoded
        Authorization: Basic YWRtaW46YWRtaW4=

        objectId=a6b372f2-c009-48ca-a4f9-52fd6ae5cba1&cmisaction=createDocument&propertyId%5B0%5D=cmis%3Aname&propertyValue%5B0%5D=4WN8N9&propertyId%5B1%5D=cmis%3AobjectTypeId&propertyValue%5B1%5D=D%3Adrc%3Agebruiksrechten&propertyId%5B2%5D=drc%3Agebruiksrechten__startdatum&propertyValue%5B2%5D=2020-06-23T13%3A01%3A49.000Z&propertyId%5B3%5D=drc%3Agebruiksrechten__omschrijving_voorwaarden&propertyValue%5B3%5D=Training+according+value+somebody+analysis.+Practice+special+organization+plant.+Media+treatment+protect+others+should+billion.&propertyId%5B4%5D=drc%3Agebruiksrechten__informatieobject&propertyValue%5B4%5D=http%3A%2F%2Ftestserver%2Fdocumenten%2Fapi%2Fv1%2Fenkelvoudiginformatieobjecten%2F9ba4ed73-7783-48ce-bcc0-393c1e5ef01e


The data passed in the body is also shown below in a more readable format:

    .. code-block::

        {
            'objectId': '0e921c3e-dbbb-47e7-bb57-81b5fc268daa',
            'cmisaction': 'createDocument',
            'propertyId[0]': 'cmis:name',
            'propertyValue[0]': 'TOX6GI',
            'propertyId[1]': 'cmis:objectTypeId',
            'propertyValue[1]': 'D:drc:gebruiksrechten',
            'propertyId[2]': 'drc:gebruiksrechten__startdatum',
            'propertyValue[2]': '2020-06-23T08:38:03.000Z',
            'propertyId[3]': 'drc:gebruiksrechten__omschrijving_voorwaarden',
            'propertyValue[3]': 'A sample description',
            'propertyId[4]': 'drc:gebruiksrechten__informatieobject',
            'propertyValue[4]': 'http://testserver/documenten/api/v1/enkelvoudiginformatieobjecten/5bd261cf-9fa0-4289-b5fc-a19f363b0f74'
        }


.. _Object-Type: http://docs.oasis-open.org/cmis/CMIS/v1.1/errata01/os/CMIS-v1.1-errata01-os-complete.html#x1-270003
.. _Document Object: http://docs.oasis-open.org/cmis/CMIS/v1.1/errata01/os/CMIS-v1.1-errata01-os-complete.html#x1-380004


Example CMIS request with web service binding
---------------------------------------------

The example data below shows what data is sent by Open Zaak when a CMIS request is
performed to create different objects with the web service binding.

The objects are created with a ``POST`` request to the url of the 'object service', whose URL
is obtained by appending ``/ObjectService/`` to the client url configured in the
Admin interface of Open Zaak.
For example, if the client url has been set to
``http://example.com/alfresco/cmisws/``,
then the object service url is
``http://example.com/alfresco/cmisws/ObjectService/``.

Within the root folder, all content created by Open Zaak will be in a folder whose name
is specified in the configuration (by default ``DRC``).

The username and passwords used are those specified in the CMIS configuration section
of the Admin interface. These are embedded in the SOAP envelope that is sent from Open Zaak.
They are alse included in the requests header in base64 encoding (see below example request).

**Document objects (EnkelvoudigInformatieObject)**

The data below is an example of a SOAP request sent from Open Zaak to create a document object according to the
document model with a short file content.

    .. code-block::

        POST /alfresco/cmisws/ObjectService HTTP/1.1
        Host: example.com
        Content-Type: multipart/related; type="application/xop+xml";  start-info="application/soap+xml"; boundary="----=_Part_52_1132425564.1594208078802"
        MIME-Version: 1.0
        SOAPAction:
        Authorization: Basic QWRtaW46U29tZVNlY3JldFBhc3N3MHJk

        ------=_Part_52_1132425564.1594208078802
        Content-Type: application/xop+xml; charset=UTF-8; type="application/soap+xml"
        Content-Transfer-Encoding: 8bit
        Content-ID: <rootpart@soapui.org>

        <?xml version="1.0" encoding="UTF-8"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="http://docs.oasis-open.org/ns/cmis/messaging/200908/" xmlns:ns1="http://docs.oasis-open.org/ns/cmis/core/200908/">
           <soapenv:Header>
              <Security xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
                 <Timestamp>
                    <Created>2020-07-27T12:00:00Z</Created>
                    <Expires>2020-07-28T12:00:00Z</Expires>
                 </Timestamp>
                 <UsernameToken>
                    <Username>Admin</Username>
                    <Password>SomeSecretPassw0rd</Password>
                 </UsernameToken>
              </Security>
           </soapenv:Header>
           <soapenv:Body>
              <ns:createDocument>
                 <ns:repositoryId>d6a10501-ef36-41e1-9aae-547154f57838</ns:repositoryId>
                 <ns:properties>
                    <ns1:propertyString propertyDefinitionId="drc:document__bronorganisatie">
                       <ns1:value>159351741</ns1:value>
                    </ns1:propertyString>
                    <ns1:propertyDateTime propertyDefinitionId="drc:document__creatiedatum">
                       <ns1:value>2020-07-27T12:00:00.000Z</ns1:value>
                    </ns1:propertyDateTime>
                    <ns1:propertyString propertyDefinitionId="drc:document__titel">
                       <ns1:value>detailed summary</ns1:value>
                    </ns1:propertyString>
                    <ns1:propertyString propertyDefinitionId="drc:document__auteur">
                       <ns1:value>test_auteur</ns1:value>
                    </ns1:propertyString>
                    <ns1:propertyString propertyDefinitionId="drc:document__formaat">
                       <ns1:value>txt</ns1:value>
                    </ns1:propertyString>
                    <ns1:propertyString propertyDefinitionId="drc:document__taal">
                       <ns1:value>eng</ns1:value>
                    </ns1:propertyString>
                    <ns1:propertyString propertyDefinitionId="drc:document__bestandsnaam">
                       <ns1:value>dummy.txt</ns1:value>
                    </ns1:propertyString>
                    <ns1:propertyString propertyDefinitionId="drc:document__link">
                       <ns1:value>http://een.link</ns1:value>
                    </ns1:propertyString>
                    <ns1:propertyString propertyDefinitionId="drc:document__beschrijving">
                       <ns1:value>test_beschrijving</ns1:value>
                    </ns1:propertyString>
                    <ns1:propertyString propertyDefinitionId="drc:document__vertrouwelijkaanduiding">
                       <ns1:value>openbaar</ns1:value>
                    </ns1:propertyString>
                    <ns1:propertyDecimal propertyDefinitionId="drc:document__versie">
                       <ns1:value>1</ns1:value>
                    </ns1:propertyDecimal>
                    <ns1:propertyId propertyDefinitionId="cmis:objectTypeId">
                       <ns1:value>D:drc:document</ns1:value>
                    </ns1:propertyId>
                    <ns1:propertyString propertyDefinitionId="cmis:name">
                       <ns1:value>detailed summary-5GHHQQ</ns1:value>
                    </ns1:propertyString>
                    <ns1:propertyString propertyDefinitionId="drc:document__identificatie">
                       <ns1:value>b0e06020-4b4f-44c1-8465-e28b849dcb40</ns1:value>
                    </ns1:propertyString>
                 </ns:properties>
                 <ns:folderId>workspace://SpacesStore/75cfa1ac-c417-48b4-ab65-6c42441315fb</ns:folderId>
                 <ns:contentStream>
                    <ns:mimeType>application/octet-stream</ns:mimeType>
                    <ns:stream>
                       <inc:Include xmlns:inc="http://www.w3.org/2004/08/xop/include" href="cid:d3ed3127-061e-4bcb-b38b-db46f041eb30" />
                    </ns:stream>
                 </ns:contentStream>
              </ns:createDocument>
           </soapenv:Body>
        </soapenv:Envelope>

        ------=_Part_52_1132425564.1594208078802
        Content-Type: application/octet-stream
        Content-Transfer-Encoding: binary
        Content-ID: <d3ed3127-061e-4bcb-b38b-db46f041eb30>

        some file content
        ------=_Part_52_1132425564.1594208078802--
