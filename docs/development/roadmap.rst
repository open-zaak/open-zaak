.. _development_roadmap:

Roadmap
=======

The roadmap for Open Zaak includes high-level overview of future and in-progress
development efforts. These can be feature-oriented, or aimed at cleaning up technical
debt in the project and/or enhancing the meta-stuff around the actual development.

Bugfixing
---------

Bugs are considered defects. Bugs must be classified by severity:

- data loss risk
- security vulnerability
- annoying but workaround available

The first two are high-prio and should be fixed as soon as possible, the third item is
low prio.

Features
--------

Feature implementation is the connection between the product steering team and the
technical team. The product steering team will usually bring up request features or
consider the requested (big) features from the Github issues.

Current list is created from issue skimming on Github.

**Post-installation configuration**

After installation, some configuration must now be done in the admin interface. However,
a user-friendly initial-setup wizard could be provided that simplifies this and collects
the fragmented aspects in an intuitive user interface.

*Impact*

- would drastically simplify post-installation initial configuration
- affects new installations by service providers installing Open Zaak
- sizing: medium

**i-Navigator (and others) support**

There are existing applications/tools containing catalogus data. Supporting these data
formats is beneficial to adoption of Open Zaak since the users don't have to type over
all the data. However, it's not necessary an Open Zaak thing because it should make use
of the API standard.

*Impact*

- improves adoption
- affects people maintaining/migrating zaaktype-catalogi to Open Zaak
- not sure if this is our scope
- sizing: large

**Better Catalogus management interface**

Currently the content is managed through the Django admin interface with some
customization, which is limited in how far you can beat it into submission.

There should be a separately developed project to interface, based on the API standard
which provides a more native (=well integrated with the tree structure) interface to
manage catalogi, zaaktypen, informatieobjecttypen, besluittypen and any related data.

*Impact*

- affects people maintaining catalogi (managing zaaktypes etc.)
- would probably be it's own, independent project that could be installed along Open Zaak,
  leaning on OZ's user management
- sizing: large

**Improve archiving parameters integration**

Choices you make with an effect on archiving parameters are now validated server side,
which is an annoying feedback cycle for administrators. The interface can include the
logic to automatically show/hide/filter the available dependent options.

*Impact*

- affects people maintaining catalogi (managing zaaktypes etc.)
- once done, reduces frustration and decreases amount of mistakes
- sizing: small/medium

**Implement password reset functionality**

This is currently not available, which requires admin-user intervention if a user
forgets their password.

*Impact*

- relieves administrators of Open Zaak to reset passwords
- prevents administrators knowing Open Zaak users' passwords
- sizing: small

**Provide selectielijst.openzaak.nl on NLX**

Related to https://github.com/open-zaak/open-zaak/issues/644 - ensure that firewalls
can stay closed by giving the option to use NLX.

*Impact*

- increases inter-operability
- affects system/networks administrators
- sizing: small

Documentation
-------------

**Provide documentation for the Ansible collection**

The Ansible collection is really the heart of the deployment infrastructure/code and
currently a magical black box. The collection itself should be documented, with target
audiences: developers, devops, sysadmins.

*Impact*

- affects possible contributors
- may provide a reference for service providers on how to correctly install OZ
- sizing: medium

**User manual: add selectielijst configuration**

The user-interface for the configuration of selectielijsten must be included in the
manual for day-to-day administrators managing the content of catalogi.

*Impact*

- affects Open Zaak administrators / people maintaining catalogi
- sizing: small

Technical debt / clean-up / codebase quality
--------------------------------------------

**Inclusion of API specs for validation**

Currently, OAS specs are linked to (raw.github.com) for validation of remote resources.
Instead of requiring an open internet connection to github, we should fetch these specs
at build time and include them as static files in the Docker image. This is good for
performance, security and reliability.

See https://github.com/open-zaak/open-zaak/issues/644

*Impact*

- affects system/network administrators
- allows firewalls to (stay or) be more strict
- small performance improvement
- sizing: small

**Check if we can change the API timezone to UTC and interface TZ to Europe/Amsterdam**

This would display the correct local times for users browsing in the admin interface,
while keeping API times in UTC for simplicity.

*Impact*

- affects people maintaining catalogi in the admin
- affects people investigating data in the admin (zaken, documenten...)
- sizing: small

**Setup requires.io integration**

This is a (free) service to monitor dependencies that are either out-of-date or have
security vulnerabilities. Github handles the security vulnerabilities well, but you
want to quickly see if you can update other deps without breaking changes, so you don't
lag behind making the upgrade harder.

*Impact*

- affects Open Zaak development
- improves Open Zaak security
- sizing: small

**Refactor ``FooConfig`` to use ``zgw_consumers.Service``**

In various places, we configure API root URLs for which service to use (
notifications API, authorizations API...). Additionally, we also must configure auth/NLX
through the services for these endpoints. It would make more sense to centralize the
service config and point to a particular service instead of storing the API root *again*.

*Impact*

- affects new installation configuration
- affects complexity of codebase (makes it less complex/confusing)
- sizing: small

**Include newer Postgres versions in CI**

Currently Open Zaak is tested against Postgres 10, while 11 and 12 are out. A test
matrix for all versions of Open Zaak seems appropriate.

*Impact*

- demonstrates compatibility
- explicit support gives more possible target deploy platforms
- sizing: small

**Prepare update to Django 3.x**

Recently Django 3.1 was released, after 3.0. Open Zaak is on Django 2.2 (LTS). We plan
to jump from LTS to LTS - Django 3.2 (LTS) should be released around April 2021.

*Impact*

- security & future security
- affects: developers, contributors, users (API clients), municipalities with a deployed
  version
- sizing: medium

**Structurally check security updates**

Django publishes patch releases at the beginning of each month. Open Zaak should include
those as soon as possible for security and stability reasons. We can also check at the
same time if other dependencies can/should be updated to new patch releases.

*Impact*

- good security record
- sizing: small

Developer tooling/experience
----------------------------

**Tick of FFPC items**

The checklist from the Foundation For Public Code includes a number of project-setup
improvements that could/should help get potential contributors started.

*Impact*

- ability to say you're FFPC compliant :-)
- sizing: small

**Document dev/virtualenv setup**

There are some best-practices w/r to storing ``KUBECONFIG`` in project-specific
locations and/or installing the Ansible dependencies inside of the virtualenv instead
of the global system directories. This should be documented with an example setup.

*Impact*

- less confusion for (potential) service providers by having a reference
- sizing: small

**Automate the Ansible collection publishing to Ansible galaxy**

Currently, publishing is a manual action by uploading the artifact through the browser.

This can be automated after a succesful CI build on Travis instead, which would also
make it easier for committers other than Joeri/Sergei to publish changes.

*Impact*

- removes manual step from contributors
- removes need to manage auth/permissions on Ansible Galaxy
- sizing: small

**Docker Hub paid plan**

Open Zaak & related Docker images are published on Docker Hub, which is a free and
public image registry. Recently Docker Hub announced changes to the image retention
policy for free plans, which will have an impact for organizations running on older
versions that are not frequently pulled/updated.

To guarantee availability, alternative solutions should be researched or consider
signing up the Open Zaak organization to a paid plan.

*Impact*

- research with likely financial implications
- not doing it might break deployed (older) Open Zaak versions, in particular patch
  releases
- sizing: medium

**Add automated OAS-comparison to the standard**

We should have a (cron) job on the CI to check that the (semantics of the) API specs
are still the same as the upstream standard API specs.

Order/encoding does not matter, so we should compare the resolved python dicts/objects.

*Impact*

- automation of staying compliant with the upstream standard
- sizing: medium
