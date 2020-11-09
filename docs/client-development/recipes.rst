.. _client-development-recipes:

Recipes
=======

In the recipes documentation, we aim to describe some patterns to organize your API
calls to maximize performance.

If you can give the equivalent example in your own language-of-preference, please
submit a pull request!

Creating a Zaak, a Document and relating them
---------------------------------------------

.. tabs::

    .. group-tab:: Python (Django)

        Using Django with `zgw-consumers`_

        .. code-block:: python

            import base64
            from datetime import date

            from zgw_consumers.constants import APITypes
            from zgw_consumers.models import Service

            zrc_client = Service.objects.filter(api_type=APITypes.zrc).get()
            drc_client = Service.objects.filter(api_type=APITypes.drc).get()

            # zaak creation
            today = date.today().strftime("%Y-%m-%d")
            zaak_body = {
                "zaaktype": "https://test.openzaak.nl/catalogi/api/v1/zaaktypen/4acb5ab8-f189-4559-b18a-8a54553a74ff",
                "bronorganisatie": "123456782",
                "verantwoordelijkeOrganisatie": "123456782",
                "registratiedatum": today,
                "startdatum": today,
            }
            zaak: dict = zrc_client.create("zaak", zaak_body)

            # document creation
            with open("/tmp/some_file.txt", "rb") as some_file:
                document_body = {
                    "bronorganisatie": "123456782",
                    "creatiedatum": today,
                    "titel": "Example document",
                    "auteur": "Open Zaak",
                    "inhoud": base64.b64encode(some_file.read()).decode("utf-8"),
                    "bestandsomvang": some_file.size,
                    "bestandsnaam": some_file.name,
                    "taal": "nld",
                    "informatieobjecttype": (
                        "https://test.openzaak.nl/catalogi/api/v1/"
                        "informatieobjecttypen/abb89dae-238e-4e6a-aacd-0ba9724350a9"
                    )
                }
            document: dict = drc_client.create("enkelvoudiginformatieobject", document_body)

            # relate them
            zio_body = {
                "zaak": zaak["url"],
                "informatieobject": document["url"],
            }
            zio: dict = zrc_client.create("zaakinformatieobject", zio_body)

    .. group-tab:: Javascript

        .. code-block:: javascript

            import jwt from 'jsonwebtoken';

            const CLIENT_ID = 'example';
            const SECRET = 'secret';

            // helpers
            const getJWT = () => {
              return jwt.sign(
                {client_id: CLIENT_ID},
                SECRET,
                {
                  algorithm: 'HS256',
                  issuer: CLIENT_ID,
                }
              );
            };

            const apiCall = (url, method='get', body) => {
              const fetchBody = body ? JSON.stringify(body) : null;
              const token = getJWT();
              const response = await fetch(
                url,
                {
                  method: method,
                  headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json',
                  },
                  body: _body
                }
              );
              const responseData = await response.json();
              return responseData;
            };

            const toBase64 = file => new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.readAsDataURL(file);
                reader.onload = () => resolve(reader.result);
                reader.onerror = error => reject(error);
            });

            // zaak creation
            const today = '2020-10-16';
            const zaakBody = {
                'zaaktype': 'https://test.openzaak.nl/catalogi/api/v1/zaaktypen/4acb5ab8-f189-4559-b18a-8a54553a74ff',
                'bronorganisatie': '123456782',
                'verantwoordelijkeOrganisatie': '123456782',
                'registratiedatum': today,
                'startdatum': today,
            }
            const zaak = await apiCall(
              'https://test.openzaak.nl/zaken/api/v1/zaken',
              'POST',
              zaakBody
            );

            // document creation
            const someFile = document.querySelector('#myfile').files[0];
            const documentBody = {
              'bronorganisatie': '123456782',
              'creatiedatum': today,
              'titel': 'Example document',
              'auteur': 'Open Zaak',
              'inhoud': toBase64(someFile),
              'bestandsomvang': someFile.size,
              'bestandsnaam': someFile.name,
              'taal': 'nld',
              'informatieobjecttype': `https://test.openzaak.nl/catalogi/api/v1/
            informatieobjecttypen/abb89dae-238e-4e6a-aacd-0ba9724350a9`
            };

            const doc = await apiCall(
              'https://test.openzaak.nl/documenten/api/v1/enkelvoudiginformatieobjecten',
              'POST',
              documentBody
            );

            // relate them
            const zioBody = {
              'zaak': zaak.url,
              'informatieobject': doc.url
            };
            const zio = await apiCall(
              'https://test.openzaak.nl/zaken/api/v1/zaakinformatieobjecten',
              'POST',
              zioBody,
            );


Retrieving the documents related to a Zaak
------------------------------------------

Key problem here is that one Zaak has (probably) multiple documents related to it,
and retrieving them sequentially is a performance hit that gets worse with the amount
of documents.

The solution is to use some form of threading/concurrency offered by your language.

.. tabs::

    .. group-tab:: Python (Django)

        Using Django with `zgw-consumers`_, we can use the
        ``concurrent.fututures.ThreadPoolExecutor``, where each job will run in its own thread.
        This gets close to retrieving all the documents in parallel instead of sequentially,
        resulting in a constant-time determined by the slowest API call.

        .. code-block:: python

            from typing import List

            from zgw_consumers.constants import APITypes
            from zgw_consumers.models import Service
            from zgw_consumers.concurrent import parallel

            zrc_client = Service.objects.filter(api_type=APITypes.zrc).get()
            drc_client = Service.objects.filter(api_type=APITypes.drc).get()

            zaak_url = "https://test.openzaak.nl/zaken/api/v1/zaken/b604ea56-f01c-432e-8d61-fd4ab02893dc"
            zios: List[dict] = zrc_client.list("zaakinformatieobject", {"zaak": zaak_url})
            document_urls = [zio["informatieobject"] for zio in zios]
            with parallel() as executor:
                _documents = executor.map(
                    lambda url: drc_client.retrieve("enkelvoudiginformatieobject", url=url),
                    document_urls
                )
            documents: List[dict] = list(_documents)



    .. group-tab:: Javascript

        Similarly to the Python case, we leverage the Javacsript async/await event loop. Once
        we've collected all the URLs of documents to retrieve, we create promises and by using
        ``Promise.all``, all API calls are being performed in parallel (at least for the network
        IO part).

        .. code-block:: javascript

            import jwt from 'jsonwebtoken';

            const CLIENT_ID = 'example';
            const SECRET = 'secret';

            // helpers
            const getJWT = () => {
              return jwt.sign(
                {client_id: CLIENT_ID},
                SECRET,
                {
                  algorithm: 'HS256',
                  issuer: CLIENT_ID,
                }
              );
            };

            const get = (url) => {
              const token = getJWT();
              const response = await fetch(
                url,
                {
                  method: 'get',
                  headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json',
                  },
                }
              );
              const responseData = await response.json();
              return responseData;
            };


            const zaakUrl = 'https://test.openzaak.nl/zaken/api/v1/zaken/b604ea56-f01c-432e-8d61-fd4ab02893dc';
            const zios = await get(`https://test.openzaak.nl/zaken/api/v1/zaakinformatieobjecten?zaak=${zaakUrl}`);
            const promises = zios.map(zio => get(zio.informatieobject));
            const documents = await Promise.all(promises);


.. _zgw-consumers: https://pypi.org/project/zgw-consumers/
