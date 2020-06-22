.. _installation_cmis:

The CMIS adapter
================

In the standard installation of Open Zaak, any documents created through the `Documenten API`_ are stored
on disk and their metadata is stored in the database.
However, it is also possible to store these documents in a Document Management System (DMS).
Instead of storing the documents, the CMIS adapter converts API calls to CMIS requests which are sent to the
DMS to create, update and delete documents.
In this way, the documents are stored in the DMS.

.. _`Documenten API`: https://documenten-api.vng.cloud/api/v1/schema/

Using the CMIS adapter
----------------------

In order to use the CMIS adapter, the setting ``CMIS_ENABLED`` should be set to ``True``.
This can be done in the ``.env`` file.
Then, the following details need to be configured through the Admin interface of Open Zaak:

    1. The client URL
    2. The client username/password
    3. The name of the main folder in the Document Management System (DMS) where documents are going to be created

These can be configured under **Configuratie > CMIS configuration**. An example configuration could be:

    1. Client URL: ``http://example.com:8888/alfresco/api/-default-/public/cmis/versions/1.1/browser``
    2. Client Username: ``Admin``
    3. Client Password: ``SomeSecretPassw0rd``
    4. Main folder name: ``DRC``


The CMIS mapper
---------------

Before a CMIS request can be performed, each attribute passed via the Document API has to be mapped to a CMIS property.
The customised document model used in the DMS is defined in a XML file,
where all the properties of the document are specified.
An example XML file is ``extension/alfresco-zsdms-model.xml``.
The mapping between the Document API attributes and the names used in the XML is in the file ``config/cmis_mapper.json``.
The keys are the names of the attributes in the Document API, while the values are the names used in the XML file.

If a different custom document model is used, then the mapper file also needs to be updated.
The path to the new mapper file is specified in the variable ``CMIS_MAPPER_FILE``. This can also be configured in the
``.env`` file.


Example CMIS request
--------------------

The example data below shows what data is sent by Open Zaak when a CMIS request is performed to create different objects.
The objects are created with a POST request to the url of the root folder.
The url of the root folder is obtained by appending ``/root/`` to the client url configured in the
Admin interface of Open Zaak.
For example, if the client url has been set to ``http://example.com/alfresco/api/-default-/public/cmis/versions/1.1/browser``,
then the root folder url is ``http://example.com/alfresco/api/-default-/public/cmis/versions/1.1/browser/root``.
Within the root folder, all content created by Open Zaak will be in a folder whose name is specified in
the configuration (by default ``DRC``).

The username and passwords used are those specified in the CMIS configuration section of the Admin interface.

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
