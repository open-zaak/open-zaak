.. _uml_diagrams:

UML Diagrams
============

This section contains UML diagrams for resources per components.

.. note::

    These are the underlying data models and this shows the relationships between the resources,
    but not all attributes are the exact same as in the API.

.. uml_images::
    :apps: zaken catalogi documenten besluiten
    :excluded_models: SingletonModel ETagMixin AuthorizationsConfig Service ConceptMixin GeldigheidMixin OptionalGeldigheidMixin ContextMixin ReservedDocument
    :grouped_apps:
        autorisaties:
            - autorisaties
            - authorizations
