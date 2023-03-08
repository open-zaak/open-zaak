# Open-Zaak and the Standard for Public Code version 0.5.0

<!-- SPDX-License-Identifier: EUPL-1.2 -->
<!-- # Copyright (C) 2020 - 2023 Dimpact -->

Link to commitment to meet the Standard for Public Code: [CONTRIBUTING](https://github.com/open-zaak/open-zaak/blob/main/CONTRIBUTING.md)

## [Code in the open](https://standard.publiccode.net/criteria/code-in-the-open.html)

- [x] criterion met.

Requirement | meets | links and notes
-----|-----|-----
All source code for any policy in use (unless used for fraud detection) MUST be published and publicly accessible. | yes | [code](https://github.com/open-zaak/open-zaak), VNG/GEMMA2 policy linked in [README](https://github.com/open-zaak/open-zaak/blob/main/README.en.md)
All source code for any software in use (unless used for fraud detection) MUST be published and publicly accessible. | yes | [code](https://github.com/open-zaak/open-zaak)
Contributors MUST NOT upload sensitive information regarding users, their organization or third parties to the repository. | yes | 2020-05-12 review by @EricHerman; [ISO 27001](https://www.maykinmedia.nl/en/)
Any source code not currently in use (such as new versions, proposals or older versions) SHOULD be published. | yes | [releases](https://github.com/open-zaak/open-zaak/releases), [docker hub tags](https://hub.docker.com/r/openzaak/open-zaak/tags)
Documenting which source code or policy underpins any specific interaction the general public may have with an organization is OPTIONAL. |  |

## [Bundle policy and source code](https://standard.publiccode.net/criteria/bundle-policy-and-code.html)

- [x] criterion met.

Requirement | meets | links and notes
-----|-----|-----
The codebase MUST include the policy that the source code is based on. | yes | [API specs embeded in the codebase](https://github.com/open-zaak/open-zaak/blob/main/src/openzaak/components/zaken/openapi.yaml), and linked from [documentation](https://github.com/open-zaak/open-zaak)
The codebase MUST include all source code that the policy is based on, unless used for fraud detection. |  | "yes" or "not applicable", do we consider it based on the API?
Policy SHOULD be provided in machine readable and unambiguous formats. | yes | OpenAPI is in machine readable yaml format
Continuous integration tests SHOULD validate that the source code and the policy are executed coherently. | yes | [GitHub workflow](https://github.com/open-zaak/open-zaak/blob/main/.github/workflows/ci.yml), [API Test Platform](https://api-test.nl/server/1/6b5fe675-694d-4948-8896-5eae88d30ef0/14bc91f7-7d8b-4bba-a020-a6c316655e65/latest/)

## [Create reusable and portable code](https://standard.publiccode.net/criteria/reusable-and-portable-codebases.html)

- [ ] criterion met.

Requirement | meets | links and notes
-----|-----|-----
The codebase MUST be developed to be reusable in different contexts. | yes | Designed to be so from the start.
The codebase MUST be independent from any secret, undisclosed, proprietary or non-open licensed code or services for execution and understanding. | yes | installation supports docker, kubernetes, vmware appliances, bare-metal is possible
The codebase SHOULD be in use by multiple parties. | yes |
The roadmap SHOULD be influenced by the needs of multiple parties. | yes | [Dimpact](https://www.dimpact.nl/openzaak), [market consultation](https://github.com/open-zaak/open-zaak-market-consultation)
Configuration SHOULD be used to make code adapt to context specific needs. |  |
The codebase SHOULD be localizable. |  | [translations](https://github.com/open-zaak/open-zaak/tree/main/src/openzaak/conf/locale) provided for catalogs but not yet complete
Code and its documentation SHOULD NOT contain situation-specific information. | yes | Some GCloud examples but nothing required; no credentials and documentation suggests using secret generators
Codebase modules SHOULD be documented in such a way as to enable reuse in codebases in other contexts. |  |

## [Welcome contributors](https://standard.publiccode.net/criteria/open-to-contributions.html)

- [ ] criterion met.

Requirement | meets | links and notes
-----|-----|-----
The codebase MUST allow anyone to submit suggestions for changes to the codebase. | yes | [requests](https://github.com/open-zaak/open-zaak/pulls)
The codebase MUST include contribution guidelines explaining what kinds of contributions are welcome and how contributors can get involved, for example in a `CONTRIBUTING` file. | yes | [CONTRIBUTING](https://github.com/open-zaak/open-zaak/blob/main/CONTRIBUTING.md), [Documentation](https://open-zaak.readthedocs.io/en/latest/development/index.html)
The codebase MUST document the governance of the codebase, contributions and its community, for example in a `GOVERNANCE` file. | no | draft [GOVERNANCE](https://github.com/open-zaak/open-zaak/blob/main/GOVERNANCE.md) file
The codebase SHOULD advertise the committed engagement of involved organizations in the development and maintenance. | yes | [Readme](https://github.com/open-zaak/open-zaak/blob/main/README.en.md#Construction)
The codebase SHOULD have a publicly available roadmap. | no | Issues are not yet collected into a roadmap view; tech-debt and tech-wishlist not yet collected into a technical roadmap
The codebase SHOULD publish codebase activity statistics. | yes | [GitHub pulse](https://github.com/open-zaak/open-zaak/pulse)
Including a code of conduct for contributors in the codebase is OPTIONAL. |  | no email address in the [Code of conduct](https://github.com/open-zaak/open-zaak/blob/main/CODE_OF_CONDUCT.md) to report incidents

## [Make contributing easy](https://standard.publiccode.net/criteria/make-contributing-easy.html)

- [x] criterion met.

Requirement | meets | links and notes
-----|-----|-----
The codebase MUST have a public issue tracker that accepts suggestions from anyone. | yes | [issues](https://github.com/open-zaak/open-zaak/issues)
The codebase MUST include instructions for how to privately report security issues for responsible disclosure. | yes | [Reporting security issues](https://open-zaak.readthedocs.io/en/stable/support/security.html#reporting-security-issues)
The documentation MUST link to both the public issue tracker and submitted codebase changes, for example in a `README` file. | yes | [Documentation](https://open-zaak.readthedocs.io/en/latest/support/index.html), [CONTRIBUTING.md](https://github.com/open-zaak/open-zaak/blob/main/CONTRIBUTING.md)
The codebase MUST have communication channels for users and developers, for example email lists. | yes | [Mailing list](https://lists.publiccode.net/mailman/postorius/lists/openzaak-discuss.lists.publiccode.net/), github [issues](https://github.com/open-zaak/open-zaak/issues), [VNG slack channel](https://samenorganiseren.slack.com/archives/CT6UH711Q) (requires an invite)
The documentation SHOULD include instructions for how to report potentially security sensitive issues on a closed channel. | yes | [SECURITY.rst](https://github.com/open-zaak/open-zaak/blob/main/SECURITY.rst)

## [Maintain version control](https://standard.publiccode.net/criteria/version-control-and-history.html)

- [x] criterion met.

Requirement | meets | links and notes
-----|-----|-----
The community MUST have a way to maintain version control for the code. | yes | [GitHub](https://github.com/open-zaak/open-zaak)
All files in the codebase MUST be version controlled. | yes | [git](https://github.com/open-zaak/open-zaak/)
All decisions MUST be documented in commit messages. | yes | Commit messages are sufficiently detailed or contain links to detail; the repo has a [policy](https://github.com/open-zaak/open-zaak/blob/main/CONTRIBUTING.md#making-the-changes) and a `pull_request_template.md` which encourages referencing an issue and describing the changes @ericherman 2022-0321
Every commit message MUST link to discussions and issues wherever possible. | yes | for non-trivial [commits](https://github.com/open-zaak/open-zaak/commits/main)
The codebase SHOULD be maintained in a distributed version control system. | yes | git
Contributors SHOULD group relevant changes in commits. | yes | [PRs](https://github.com/open-zaak/open-zaak/pulls)
Maintainers SHOULD mark released versions of the codebase, for example using revision tags or textual labels. | yes | [releases](https://github.com/open-zaak/open-zaak/releases)
Contributors SHOULD prefer file formats where the changes within the files can be easily viewed and understood in the version control system. | yes | mostly code and Restructured Text or Markdown
It is OPTIONAL for contributors to sign their commits and provide an email address, so that future contributors are able to contact past contributors with questions about their work. | yes | Commits have email addresses, release tags GPG signed

## [Require review of contributions](https://standard.publiccode.net/criteria/require-review.html)

- [x] criterion met.

Requirement | meets | links and notes
-----|-----|-----
All contributions that are accepted or committed to release versions of the codebase MUST be reviewed by another contributor. | yes | [PRs](https://github.com/open-zaak/open-zaak/pulls)
Reviews MUST include source, policy, tests and documentation. | yes | repo is configured, tests span, practices right, yet documentation could be more explicit on this point
Reviewers MUST provide feedback on all decisions to not accept a contribution. | yes | documentations/contrib guidelines could copy-paste from the employement handbook,  [PRs](https://github.com/open-zaak/open-zaak/pulls)
Contributions SHOULD conform to the standards, architecture and decisions set out in the codebase in order to pass review. | yes | [PRs](https://github.com/open-zaak/open-zaak/pulls), django best practices
Reviews SHOULD include running both the code and the tests of the codebase. | yes | CI and manual validation required, not clearly documented yet (in handbook)
Contributions SHOULD be reviewed by someone in a different context than the contributor. |  | (some) not applicable yet
Version control systems SHOULD NOT accept non-reviewed contributions in release versions. | yes | main branch protected, [release process](https://open-zaak.readthedocs.io/en/latest/development/releasing.html)
Reviews SHOULD happen within two business days. | yes | no official policy, is the practice
Performing reviews by multiple reviewers is OPTIONAL. |  | mostly

## [Document codebase objectives](https://standard.publiccode.net/criteria/document-objectives.html)

- [x] criterion met.

Requirement | meets | links and notes
-----|-----|-----
The codebase MUST contain documentation of its objectives, like a mission and goal statement, that is understandable by developers and designers so that they can use or contribute to the codebase. | yes | "Open Zaak is based on the API reference implementations by VNG Realisatie to create a production-grade product that can be used by municipalities." [introduction](https://open-zaak.readthedocs.io/en/latest/introduction/index.html)
Codebase documentation SHOULD clearly describe the connections between policy objectives and codebase objectives. | yes |
Documenting the objectives of the codebase for the general public is OPTIONAL. |  | could elaborate for general public: Common Ground, data security, GDPR requests and such

## [Document the code](https://standard.publiccode.net/criteria/documenting.html)

- [ ] criterion met.

Requirement | meets | links and notes
-----|-----|-----
All of the functionality of the codebase, policy as well as source, MUST be described in language clearly understandable for those that understand the purpose of the code. | yes | additional docs are generated from code comments
The documentation of the codebase MUST contain a description of how to install and run the source code. | yes | [getting started](https://open-zaak.readthedocs.io/en/latest/development/getting_started.html), [post-install checklist](https://open-zaak.readthedocs.io/en/latest/installation/index.html#post-install-checklist)
The documentation of the codebase MUST contain examples demonstrating the key functionality. | yes | [Recipies](https://open-zaak.readthedocs.io/en/stable/client-development/recipes.html), improvement: add demo fixtures/instructions
The documentation of the codebase SHOULD contain a high level description that is clearly understandable for a wide audience of stakeholders, like the general public and journalists. |  | [documentation](https://open-zaak.readthedocs.io/en/latest/introduction/index.html), would like to see standard recipes and examples of more functionality
The documentation of the codebase SHOULD contain a section describing how to install and run a standalone version of the source code, including, if necessary, a test dataset. | yes | [installation](https://open-zaak.readthedocs.io/en/stable/installation/index.html#installation)
The documentation of the codebase SHOULD contain examples for all functionality. | yes | [manual](https://open-zaak.readthedocs.io/en/stable/manual/index.html)
The documentation SHOULD describe the key components or modules of the codebase and their relationships, for example as a high level architectural diagram. |  | basics about the Frontend and Backend described in [principles](https://open-zaak.readthedocs.io/en/stable/development/principles.html)
There SHOULD be continuous integration tests for the quality of the documentation. | yes | link checks, build checks, [GitHub Actions](https://github.com/open-zaak/open-zaak/blob/main/.github/workflows/ci.yml#L184-L194)
Including examples that make users want to immediately start using the codebase in the documentation of the codebase is OPTIONAL. |  |

## [Use plain English](https://standard.publiccode.net/criteria/understandable-english-first.html)

- [ ] criterion met.

Requirement | meets | links and notes
-----|-----|-----
All codebase documentation MUST be in English. |  | [manual in Dutch](https://open-zaak.readthedocs.io/en/latest/manual/index.html)
All code MUST be in English, except where policy is machine interpreted as code. |  |
All bundled policy not available in English MUST have an accompanying summary in English. |  |
Any translation MUST be up to date with the English version and vice versa. |  | TODO: add translations of user-facing texts (NL -> EN) (makemessages)
There SHOULD be no acronyms, abbreviations, puns or legal/non-English/domain specific terms in the codebase without an explanation preceding it or a link to an explanation. |  | Domain specific Dutch terms could be in a glossary which is also translated in English.
Documentation SHOULD aim for a lower secondary education reading level, as recommended by the [Web Content Accessibility Guidelines 2](https://www.w3.org/WAI/WCAG21/quickref/?showtechniques=315#readable). |  | Would be good to get an evaluation of this prior to investing in translation.
Providing a translation of any code, documentation or tests is OPTIONAL. |  |

## [Use open standards](https://standard.publiccode.net/criteria/open-standards.html)

- [x] criterion met.

Requirement | meets | links and notes
-----|-----|-----
For features of the codebase that facilitate the exchange of data the codebase MUST use an open standard that meets the [Open Source Initiative Open Standard Requirements](https://opensource.org/osr). | yes | The [Zaakgericht Werken in het Gemeentelijk Gegevenslandschap](https://www.gemmaonline.nl/images/gemmaonline/f/f6/20190620_-_Zaakgericht_werken_in_het_Gemeentelijk_Gegevenslandschap_v101.pdf) meets the 5 criteria of the [Open Standards Requirement for Software](https://opensource.org/osr)
Any non-open standards used MUST be recorded clearly as such in the documentation. | n/a |
Any standard chosen for use within the codebase MUST be listed in the documentation with a link to where it is available. | yes | [API-specifications](https://open-zaak.readthedocs.io/en/stable/api/index.html#api-index)
Any non-open standards chosen for use within the codebase MUST NOT hinder collaboration and reuse. | n/a |
If no existing open standard is available, effort SHOULD be put into developing one. | n/a |
Open standards that are machine testable SHOULD be preferred over open standards that are not. | yes | e.g.: [Zaken API](https://vng-realisatie.github.io/gemma-zaken/standaard/zaken/index)
Non-open standards that are machine testable SHOULD be preferred over non-open standards that are not. | N/A |

## [Use continuous integration](https://standard.publiccode.net/criteria/continuous-integration.html)

- [ ] criterion met.

Requirement | meets | links and notes
-----|-----|-----
All functionality in the source code MUST have automated tests. |  | 96% [codecoverage](https://codecov.io/gh/open-zaak/open-zaak), small amount of admin UI code not tested
Contributions MUST pass all automated tests before they are admitted into the codebase. | yes | github checks
The codebase MUST have guidelines explaining how to structure contributions. | yes | [CONTRIBUTING](https://github.com/open-zaak/open-zaak/blob/main/CONTRIBUTING.md)
The codebase MUST have active contributors who can review contributions. | yes | [pulse](https://github.com/open-zaak/open-zaak/pulse)
The codebase guidelines SHOULD state that each contribution should focus on a single issue. |  | single PR to solve a single issue could be clearer in guidelines
Source code test and documentation coverage SHOULD be monitored. | yes |
Testing policy and documentation for consistency with the source and vice versa is OPTIONAL. | yes |
Testing policy and documentation for style and broken links is OPTIONAL. | yes | [docs tests](https://github.com/open-zaak/open-zaak/blob/main/docs/check_sphinx.py), flake8/isort/black
Testing the code by using examples in the documentation is OPTIONAL. |  |

## [Publish with an open license](https://standard.publiccode.net/criteria/open-licenses.html)

- [x] criterion met.

Requirement | meets | links and notes
-----|-----|-----
All code and documentation MUST be licensed such that it may be freely reusable, changeable and redistributable. | yes | [copyright marks in the footer?](https://open-zaak.readthedocs.io/en/latest/index.html) -> check if we can add license to footer ([sphinx conf](https://github.com/open-zaak/open-zaak/blob/main/docs/conf.py#L30)), but explicit open license
Software source code MUST be licensed under an [OSI-approved or FSF Free/Libre license](https://spdx.org/licenses/). | yes | EUPL 1.2 [LICENSE](https://github.com/open-zaak/open-zaak/blob/main/LICENSE.md)
All code MUST be published with a license file. | yes | [LICENSE](https://github.com/open-zaak/open-zaak/blob/main/LICENSE.md)
Contributors MUST NOT be required to transfer copyright of their contributions to the codebase. | yes |
All source code files in the codebase SHOULD include a copyright notice and a license header that are machine-readable. | yes | 2020-08-03 review by @ericherman
Having multiple licenses for different types of code and documentation is OPTIONAL. |  |

## [Make the codebase findable](https://standard.publiccode.net/criteria/findability.html)

- [ ] criterion met.

Requirement | meets | links and notes
-----|-----|-----
The codebase MUST be findable using a search engine by describing the problem it solves in natural language. |  | <!-- need to check -->
The codebase MUST be findable using a search engine by codebase name. | yes |
The name of the codebase SHOULD be descriptive and free from acronyms, abbreviations, puns or organizational branding. | yes |
Maintainers SHOULD submit the codebase to relevant software catalogs. |  |
The codebase SHOULD have a website which describes the problem the codebase solves using the preferred jargon of different potential users of the codebase (including technologists, policy experts and managers). | yes | [openzaak.org](https://openzaak.org/)
The codebase SHOULD have a unique and persistent identifier where the entry mentions the major contributors, repository location and website. |  |
The codebase SHOULD include a machine-readable metadata description, for example in a [publiccode.yml](https://github.com/publiccodeyml/publiccode.yml) file. | yes | [publiccode.yaml](https://github.com/open-zaak/open-zaak/blob/main/publiccode.yaml)
A dedicated domain name for the codebase is OPTIONAL. | yes |
Regular presentations at conferences by the community are OPTIONAL. |  |

## [Use a coherent style](https://standard.publiccode.net/criteria/style.html)

- [x] criterion met.

Requirement | meets | links and notes
-----|-----|-----
The codebase MUST use a coding or writing style guide, either the codebase community's own or an existing one referred to in the codebase. | yes | [Style guides](https://github.com/open-zaak/open-zaak/blob/main/CONTRIBUTING.md)
Contributions SHOULD pass automated tests on style. | yes |
The style guide SHOULD include expectations for inline comments and documentation for non-trivial sections. | yes | add to contributing guidelines
Including expectations for [understandable English](https://standard.publiccode.net/criteria/understandable-english-first.html) in the style guide is OPTIONAL. |  |

## [Document codebase maturity](https://standard.publiccode.net/criteria/document-maturity.html)

- [x] criterion met.

Requirement | meets | links and notes
-----|-----|-----
A codebase MUST be versioned. | yes | [version list](https://open-zaak.readthedocs.io/en/latest/development/index.html)
The codebase MUST prominently document whether or not there are versions of the codebase that are ready to use. | yes |
Codebase versions that are ready to use MUST only depend on versions of other codebases that are also ready to use. | yes | [Open source dependencies](https://github.com/open-zaak/open-zaak/blob/main/docs/introduction/open-source/dependencies.rst)
A codebase SHOULD contain a log of changes from version to version, for example in the `CHANGELOG`. | yes | [changelog](https://open-zaak.readthedocs.io/en/latest/development/changelog.html)
It is OPTIONAL to use semantic versioning. | yes | Not explicitly documented as following semantic versioning
