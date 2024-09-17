.. _development_howtos_data_generation:

Data generation
===============

To fill in the test environment with data (for example for :ref:`performance_index`)
``generate_data`` management command can be used.
It generates resources for Zaken, Catalogi, Documenten and Besluiten APIs and relations between them.

To use this command run:

   .. code-block:: bash

       $ python src/manage.py generate_data


By default it generates 100 zaaktypen, 1 mln zaken, 1 mln documents and 1 mln besluiten.
The number of generated objects can be specified in the arguments:

* ``zaaktypen`` - number of zaaktypen, besluittypen and informatieobjecten. Default is 100.
* ``zaken`` - number of zaken, besluiten and documents. Default is 1 mln. Should be a multiple of ``zaaktypen``

For example, if you want to generate 1 zaaktype and 2 zaken you can run:

   .. code-block:: bash

       $ python src/manage.py generate_data --zaaktypen 1 --zaken 2

This command is memory consuming, so to manage the memory usage you can the specify command argument:

* ``partition`` - number of objects stored in python variables. Default is 10000. Large numbers can lead to OOM error.

.. note:: ``generate_data`` command can be run only locally on the development environment.
   The docker build doesn't include ``factory_boy`` library which is used to generate objects.
   If you need to generate data on the environment deployed with the docker image, the easiest way would be
   to generate data locally and then to use ``pg_dump`` to export the data.
