# DRAFT: OpenZaak codebase goverance

## Introduction

This document contains a draft proposal for the 'governance.md' file on the OpenZaak repository.

## Principles

As a community we want make it easier for new users to become contributors and maintainers.

The OpenZaak community adheres to the following principles:

* OpenZaak is open source.
* We're a welcoming and respectful community as mentioned in our [Code of Conduct](#Code-of-Conduct).
* Transparent and accessible, changes to the OpenZaak organization, OpenZaak code repositories, and OpenZaak related activities (e.g. level, involvement, etc) are done in public.
* Ideas and contributions are accepted according to their technical merit and alignment with project objectives, scope, and design principles.

The maintainers of OpenZaak have two steering teams, a technical one and a product one.

Through codebase stewardship the Foundation for Public Code supports the governance of OpenZaak, the product and technical steering teams, and its community.

## Technical steering team

The OpenZaak technical steering team members are active contributors. As a team, they
have the joint responsibility to:

* Provide technical direction for the codebase
* Maintain a technical roadmap, an architecture and coding principles
* Resolve issues in development or conflicts between contributors
* Managing and planning releases
* Controlling rights to Open Zaak assets such as source repositories

The current team members are:

* Anton Boerma, Exxellence
* Joeri Bekker, Maykin Media
* Sergei Maertens, Maykin Media
* Tahir Malik, Contezza
* Tjerk Vaags, Contezza

Any active member of the community can request to become a technical steering team
member by asking the technical steering team. The technical steering team will vote on
it (simple majority).

On a day to day basis, these members are responsible for:

* Merging pull requests
* Overseeing the resolution and disclosure of security issues

If technical steering team members cannot reach consensus informally, the question at
hand should be forwarded to the technical steering team meeting.

The technical steering team meets regularly. Their agenda includes reivew of the
technical roadmap and issues that are at an impasse. The intention of the agenda is not
to review or approve all patches. This is mainly being done through the process
described in [the contributing guide](CONTRIBUTING.md#Reviews).

If more than one technical steering team member disagrees with a decision of the
technical steering team they may appeal to the product steering team who will make the
ultimate ruling.

Ideally, no one company or organization will employ a simple majority of the technical
steering team.

## Product steering team

Responsibilities of the product steering team:

* Maintaining the mission, vision, values, and scope of the project
* Collecting planned features and presenting them in a unified view
* Refining the governance as needed
* Making codebase level decisions
* Resolving escalated project decisions when the subteam responsible is blocked
* Managing the OpenZaak brand
* Licensing and intellectual property changes
* Controlling access to OpenZaak assets such as hosting and project calendars

Changes in codebase governance can only be done by the product steering team and requires super majority.

Anyone with an interest in Open Zaak can request to become a product steering team member by asking the product steering team. The product steering team will vote on this request (simple majority). However, no more than 1 person per organization can have a vote. Typical members are:

1) Representatives of a municipality that uses Open Zaak in some form as part of their current or future architecture.
2) Representatives of an organization that manages or delivers Open Zaak installation(s) at one or more public organizations.
3) Representatives of an organization that incorporates or uses Open Zaak in combination with their own product(s).

The current team members are:

* Joeri Bekker, Maykin Media
* Jolanda van de Kooij, Exxellence
* Peter Moen, Exxellence
* Hugo ter Doest, Dimpact
* Niels Lindeboom, Dimpact
* Tahir Malik, Contezza
* Silvion Moesan, Open.Satisfaction

## Decision making process

The default decision making process is lazy-consensus. This means that any decision is considered supported by the team making it as long as no one objects. Silence on any consensus decision is implicit agreement and equivalent to explicit agreement. Explicit agreement may be stated at will.

When a consensus cannot be found a team member can call for a majority vote on a decision. Every team member has 1 vote.

Many of the day-to-day project maintenance tasks can be done by a lazy consensus model. But the following items must be called to vote:

* Adding a team member (simple majority)
* Removing a team member (super majority)
* Changing the governance rules (this document) (super majority)
* Licensing and intellectual property changes (including new logos, wordmarks) (simple majority)
* Adding, archiving, or removing subprojects (simple majority)

## Code of Conduct

OpenZaak's Code of Conduct is explained in [this project's code of conduct](CODE_OF_CONDUCT.md).

Currently, the Technical Steering Group handles Code of Conduct violations.

If the possible violation involves a team member that member will be recused from voting
on the issue. Such issues must be escalated to the product steering team contact, and
the product steering team may choose to intervene.
