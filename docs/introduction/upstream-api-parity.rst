.. _introduction_upstream_api_parity:

API standard alignment policy
=============================

As mentioned in the :ref:`introduction <introduction_index>`, Open Zaak implements
the API standards defined by VNG.

The base policy is that complying to these standards is a **must**, and the upstream
standard defines compliance as:

* the full API specification including run-time behaviour must be correctly implemented
* implementations are not allowed to offer (proprietary) extensions on top of this
  standard

The reasoning behind this is logical *and the Technical Steering Group supports this*.

* further API standard development may introduce conflicts with custom extensions. The
  upstream standard should not be held hostage in such situations.
* extensions create vendor lock-in and portability issues for consumer applications.

However, the Technical Steering Group also recognizes that consumer application
development may be severely impacted by missing features. This document describes
our policy on such situations and how decisions are made.

The role of the Technical Steering Group (TSG)
----------------------------------------------

The TSG understands that sometimes a small feature in Open Zaak can make a big
difference for consumer application development. We also realize that the resources
may not be available to re-visit the architecture to find alternative solutions and
a stop-gap solution is desired.

There is a risk that organizations making use of Open Zaak have a short-term need for
features that are missing from Open Zaak or the standard, and therefore decide to
fork Open Zaak and implement these features themselves.

Forks have the potential to bring substantial maintenance overhead for the organization
deciding to fork. On top of that, they may also split the ecosystem, especially if
consumer applications are developed against a fork without keeping a close eye on what
features used are part of the standard and which aren't (this is usually the path of
least resistance). This leads to "dialects" and applications that turn out not to be
portable or reusable because they (unknowningly) depend on a particular fork of Open Zaak.

The TSG tries to find balance between community-value and being strict and reliable with
regard to the upstream standard.

**Experimental features**

The TSG has the decisive power to allow experimental features to be added to and removed
from Open Zaak.

Features can be marked as *experimental* in some situations (see below). This means
that they are suitable for exploring, prototyping and solving urgent problems, but there
are no guarantees about stability.

Experimental features do not adhere to semantic versioning, they can be added, modified
or even completely removed in any release of Open Zaak. We do commit to documenting this
as a breaking change in the release notes, if it happens.

At the API level, experimental features will be marked with the ``x-experimental: true``
extension object in the machine-readable API specification, in addition to including a
textual warning in the relevant description that a feature is experimental.

Situations we recognize
-----------------------

**A feature does not exist in the standard**

Features may be requested that make sense from the perspective of the consumer
applications that don't exist (yet) in the API standard.

The correct path is to propose this to the upstream standard. Sometimes it makes sense
to explore the viability of this feature through experiments and/or prototyping. In
that case, the feature can be proposed to the TSG who will decide if we want to include
this as an *experimental* feature in Open Zaak. If this feature turns out to be a
success, the TSG shall urge you to propose this feature in the standard.

If the upstream standard decides this feature will not be added to the API, then Open
Zaak will **remove** the experimental feature, following our alignment policy.

If the upstream standard decides to accept this feature, the experimental feature will
be kept and/or updated to the variant destined for the standard. The feature will only
be promoted from experimental to a stable feature once the API version (as defined by
the standard) containing the feature is **fully** implemented in Open Zaak.

**A feature is planned for a newer API version than we support**

At the time of writing, Open Zaak only supports the 1.0.x versions of the APIs as defined
in the standard. Some parties rely on features implemented in or planned for newer
versions of the API specification.

The intent is to have Open Zaak implement complete minor versions of API specifications,
not parts thereof. The TSG wants to encourage organizations making use of Open Zaak to
invest in the ecosystem and not only serve their own needs. API version updates are
implemented in chronological order - this means that 1.0 is first, 1.1 is next and
finally 1.2 is implemented, without skipping in-between versions.

The TSG has the power to make exceptions to this principle, on the condition that the
feature is fully backwards compatible. If an exception is granted, the feature is marked
as *experimental* with all the associated warnings.

**A feature is accepted for an unreleased API version**

As it may become clear while testing release candidates for new API versions in the
standard that a feature does not have the intented or expected benefit, it may still be
scrapped again before the final release of the new API version.

As such, implementing these features is again at the discretion of the TSG. If the
feature is accepted, it is marked as *experimental*.
