# Open-Zaak and the Standard for Public Code


## [Code in the Open](https://standard.publiccode.net/criteria/code-in-the-open.html)

- [x] Open Zaak development happens in the open on [Github](https://github.com/open-zaak)

Requirement | meets | links and notes
-----|-----|-----
All source code for any policy and software in use (unless used for fraud detection) MUST be published and publicly accessible. | yes | [code](https://github.com/open-zaak/open-zaak), VNG/GEMMA2 policy linked in [README](https://github.com/open-zaak/open-zaak/blob/master/README.en.md)
Contributors MUST NOT upload sensitive information regarding users, their organization or third parties to the repository. Examples of sensitive information include configurations, usernames and passwords, public keys and other real credentials used in the production system. | yes | 2020-05-12 review by @EricHerman; [ISO 27001](https://www.maykinmedia.nl/en/)
Any source code not currently in use (such as new versions, proposals or older versions) SHOULD be published. | yes | [releases](https://github.com/open-zaak/open-zaak/releases), [docker hub tags](https://hub.docker.com/r/openzaak/open-zaak/tags)
The source code MAY provide the general public with insight into which source code or policy underpins any specific interaction they have with your organization. | |


## [Bundle policy and source code](https://standard.publiccode.net/criteria/bundle-policy-and-code.html)

- [x] Policy bundled, tested, and linked in the documentation, some policy not available in English

Requirement | meets | links and notes
-----|-----|-----
A codebase MUST include the policy that the source code is based on. | yes | [API specs embeded in the codebase](https://github.com/open-zaak/open-zaak/blob/master/src/openzaak/components/zaken/openapi.yaml), and linked from [documentation](https://github.com/open-zaak/open-zaak)
A codebase MUST include all source code that the policy is based on. | | "yes" or "not applicable", do we consider it based on the API?
All policy and source code that the codebase is based on MUST be documented, reusable and portable. | yes | code dependencies are OSI
Policy SHOULD be provided in machine readable and unambiguous formats. | yes | OpenAPI is in machine readable yaml format
Continuous integration tests SHOULD validate that the source code and the policy are executed coherently. | yes | [Travis CI config](https://github.com/open-zaak/open-zaak/blob/master/.travis.yml#L86), [API Test Platform](https://api-test.nl/server/1/224fd5be-bc64-4d55-a190-454bee3cc8e3/14bc91f7-7d8b-4bba-a020-a6c316655e65/latest/)

## [Create reusable and portable code](https://standard.publiccode.net/criteria/reusable-and-portable-codebases.html)

- [x] designed to be reusable from the start

Requirement | meets | links and notes
-----|-----|-----
The codebase MUST be developed to be reusable in different contexts. | yes | Designed to be so from the start.
The codebase MUST be independent from any secret, undisclosed, proprietary or non-open licensed code or services for execution and understanding. | yes | installation supports docker, kubernetes, vmware appliances, bare-metal is possible
The codebase MUST be in use by multiple parties. | yes | Deployed in multiple sandbox environments (e.g: Utrecht is testing it, others Den Haag, Delft looking at it.)
The roadmap SHOULD be influenced by the needs of multiple parties. | yes | [Dimpact](https://www.dimpact.nl/openzaak), [market consultation](https://github.com/open-zaak/open-zaak-market-consultation) |
Code SHOULD be general purpose and SHOULD be configurable. |
Codebases SHOULD include a publiccode.yml metadata description so that they’re easily discoverable. | yes | [publiccode.yml](https://github.com/open-zaak/open-zaak/blob/master/publiccode.yaml)
Code and its documentation SHOULD NOT contain situation-specific information. For example, personal and organizational data as well as tokens and passwords used in the production system should never be included. | yes | Some GCloud examples but nothing required; no credentials and documentation suggests using secret generators

## [Welcome contributions](https://standard.publiccode.net/criteria/open-to-contributions.html)

- [ ]

Requirement | meets | links and notes
-----|-----|-----
The codebase MUST have a public issue tracker that accepts suggestions from anyone. | yes | [issues](https://github.com/open-zaak/open-zaak/issues)
The codebase MUST allow anyone to submit suggestions for changes to the codebase. | yes | [requests](https://github.com/open-zaak/open-zaak/pulls)
The documentation MUST link to both the public issue tracker and submitted codebase changes, for example in a README file. | yes | [Documentation](https://open-zaak.readthedocs.io/en/latest/support/index.html), [CONTRIBUTING.md](https://github.com/open-zaak/open-zaak/blob/master/CONTRIBUTING.md)
The codebase MUST include an email address for security issues and responsible disclosure. | no |
The codebase MUST include contribution guidelines explaining how contributors can get involved, for example in a CONTRIBUTING file. | yes | [CONTRIBUTING](https://github.com/open-zaak/open-zaak/blob/master/CONTRIBUTING.md), [Documentation](https://open-zaak.readthedocs.io/en/latest/development/index.html)
The project MUST have communication channels for users and developers, for example email lists. | yes | [Mailing list](https://lists.publiccode.net/mailman/postorius/lists/openzaak-discuss.lists.publiccode.net/), github [issues](https://github.com/open-zaak/open-zaak/issues), [VNG slack channel](https://samenorganiseren.slack.com/archives/CT6UH711Q) (requires an invite)
The codebase SHOULD have a publicly available roadmap. | no | Issues are not yet collected into a roadmap view; tech-debt and tech-wishlist not yet collected into a technical roadmap
The codebase SHOULD advertise the committed engagement of involved organizations in the development and maintenance. | yes | [Readme](https://github.com/open-zaak/open-zaak/blob/master/README.en.md#Construction)
The documentation SHOULD include instructions for how to report potentially security sensitive issues on a closed channel. | no |
The codebase SHOULD document the governance of the codebase, contributions and its community, for example in a GOVERNANCE file. | no | draft [GOVERNANCE](https://github.com/open-zaak/open-zaak/blob/master/GOVERNANCE.md) file
The codebase MAY include a code of conduct for contributors. | no | no email address in the [Code of conduct](https://github.com/open-zaak/open-zaak/blob/master/CODE_OF_CONDUCT.md) to report incidents



## [Maintain version control](https://standard.publiccode.net/criteria/version-control-and-history.html)

- [ ] Good, but let's wait for a commit template

Requirement | meets | links and notes
-----|-----|-----
You MUST have a way to maintain version control for your code. | yes | [GitHub](https://github.com/open-zaak/open-zaak)
All files in a codebase MUST be version controlled. | yes | [git](https://github.com/open-zaak/open-zaak/)
All decisions MUST be documented in commit messages. | | Generally good, some room for improvement, commit template may help
Every commit message MUST link to discussions and issues wherever possible. |  | yes for non-trivial [commits](https://github.com/open-zaak/open-zaak/commits/master)
You SHOULD group relevant changes in commits. | yes | [PRs](https://github.com/open-zaak/open-zaak/pulls)
You SHOULD mark different versions of your codebase, for example using revision tags or textual labels. | yes | [releases](https://github.com/open-zaak/open-zaak/releases)
You SHOULD prefer file formats that can easily be version controlled. | yes | mostly code and Restructured Text or Markdown

## [Require review of contributions](https://standard.publiccode.net/criteria/require-review.html)

- [x] Practices are good, would like to see explicit docs

Requirement | meets | links and notes
-----|-----|-----
All contributions that are accepted or committed to release versions of the codebase MUST be reviewed by another contributor. | yes | [PRs](https://github.com/open-zaak/open-zaak/pulls)
Reviews MUST include source, policy, tests and documentation. | yes | repo is configured, tests span, practices right, yet documentation could be more explicit on this point
Reviewers MUST provide feedback on all decisions made and the implementation in the review. | yes | documentations/contrib guidelines could copy-paste from the employement handbook,  [PRs](https://github.com/open-zaak/open-zaak/pulls)
Contributions SHOULD conform to the standards, architecture and decisions set out in the codebase in order to pass review. | yes | [PRs](https://github.com/open-zaak/open-zaak/pulls), django best practices
Reviews SHOULD include running both the code and the tests of the codebase. | yes | CI and manual validation required, not clearly documented yet (in handbook)
Contributions SHOULD be reviewed by someone in a different context than the contributor. | | (some) not applicable yet
Version control systems SHOULD not accept non-reviewed contributions in release versions. | yes | master branch protected, [release process](https://open-zaak.readthedocs.io/en/latest/development/releasing.html)
Reviews SHOULD happen within two business days. | yes | no official policy, is the practice
Reviews MAY be performed by multiple reviewers. | | mostly

## [Document your objectives](https://standard.publiccode.net/criteria/document-objectives.html)

- [x] Objectives are clear in the introduction documenation

Requirement | meets | links and notes
-----|-----|-----
The codebase MUST contain documentation of its objectives – like a mission and goal statement – that is understandable by designers and developers so that they can use or contribute to the codebase. | yes | "Open Zaak is based on the API reference implementations by VNG Realisatie to create a production-grade product that can be used by municipalities." [introduction](https://open-zaak.readthedocs.io/en/latest/introduction/index.html)
The codebase SHOULD contain documentation on its objectives understandable by policy makers and management. | yes |
The codebase MAY contain documentation of its objectives for the general public. | | could elaborate for general public: Common Ground, data security, GDPR requests and such


## [Document your code](https://standard.publiccode.net/criteria/documenting.html)

- [x] documentation is good across the board, "recipies" would be nice

Requirement | meets | links and notes
-----|-----|-----
All of the functionality of your codebase – policy as well as source – MUST be described in language clearly understandable for those that understand the purpose of the code. | yes | additional docs are generated from code comments
The documentation of your codebase MUST contain: a description of how to install and run the source code, examples demonstrating the key functionality. | yes | [getting started](https://open-zaak.readthedocs.io/en/latest/development/getting_started.html), [post-install checklist](https://open-zaak.readthedocs.io/en/latest/installation/index.html#post-install-checklist), improvement: add demo fixtures/instructions
The documentation of your codebase SHOULD contain: a high level description that is clearly understandable for a wide audience of stakeholders, like the general public and journalists, a section describing how to install and run a standalone version of the source code, including, if necessary, a test dataset, examples for all functionality. |  | [documentation](https://open-zaak.readthedocs.io/en/latest/introduction/index.html), would like to see standard recipies and examples of more fuctionality
There SHOULD be continuous integration tests for the quality of your documentation. | yes | link checks, build checks, [Travis config](https://github.com/open-zaak/open-zaak/blob/master/.travis.yml#L74)
The documentation of your codebase MAY contain examples that make users want to immediately start using your codebase. |
You MAY use the examples in your documentation to test your code. |

## [Use plain English](https://standard.publiccode.net/criteria/understandable-english-first.html)

- [ ]

Requirement | meets | links and notes
-----|-----|-----
All code and documentation MUST be in English. |  | [manual in Dutch](https://open-zaak.readthedocs.io/en/latest/manual/index.html)
Any translation MUST be up to date with the English version and vice-versa. | | TODO: add translations of user-facing texts (NL -> EN) (makemessages)
There SHOULD be no acronyms, abbreviations, puns or legal/domain specific terms in the codebase without an explanation preceding it or a link to an explanation. | |Domain specific Dutch terms could be in a glossary which is also translated in English.
The name of the project or codebase SHOULD be descriptive and free from acronyms, abbreviations, puns or branding. | yes |
Documentation SHOULD aim for a lower secondary education reading level, as recommended by the Web Content Accessibility Guidelines 2. | | Would be good to get an evaluation of this prior to investing in translation.
Any code, documentation and tests MAY have a translation. |

## [Use open standards](https://standard.publiccode.net/criteria/open-standards.html)

- [ ]

Requirement | meets | links and notes
-----|-----|-----
For features of a codebase that facilitate the exchange of data the codebase MUST use an open standard that meets the Open Source Initiative Open Standard Requirements. | | check with VNG
If no existing open standard is available, effort SHOULD be put into developing one. |
Standards that are machine testable SHOULD be preferred over those that are not. | yes | see test suite
Functionality using features from a non-open standard (one that doesn’t meet the Open Source  Initiative Open Standard Requirements) MAY be provided if necessary, but only in addition to compliant features. |
All non-compliant standards used MUST be recorded clearly in the documentation. | | (Will update docs after VNG discussion.)
The codebase SHOULD contain a list of all the standards used with links to where they are available. | yes |

## [Use continuous integration](https://standard.publiccode.net/criteria/continuous-integration.html)

- [ ]

Requirement | meets | links and notes
-----|-----|-----
All functionality in the source code MUST have automated tests. | | 96% [codecoverage](https://codecov.io/gh/open-zaak/open-zaak), small amount of admin UI code not tested
Contributions MUST pass all automated tests before they are admitted into the codebase. | yes | github checks
Contributions MUST be small. | | refer to contributing guidelines (single issue, single PR solves single issue)
The codebase MUST have active contributors. | yes | [pulse](https://github.com/open-zaak/open-zaak/pulse)
Source code test and documentation coverage SHOULD be monitored. | yes |
Policy and documentation MAY have testing for consistency with the source and vice versa. | yes |
Policy and documentation MAY have testing for style and broken links. | yes | [docs tests](https://github.com/open-zaak/open-zaak/blob/master/docs/check_sphinx.py), flake8/isort/black

## [Publish with an open license](https://standard.publiccode.net/criteria/open-licenses.html)

- [x] Remove confusion in the documentation footer

Requirement | meets | links and notes
-----|-----|-----
All code and documentation MUST be licensed such that it may be freely reusable, changeable and redistributable. | yes | [copyright marks in the footer?](https://open-zaak.readthedocs.io/en/latest/index.html) -> check if we can add license to footer ([sphinx conf](https://github.com/open-zaak/open-zaak/blob/master/docs/conf.py#L30)), but explicit open license
Software source code MUST be licensed under an OSI-approved open source license. | yes | [LICENSE](https://github.com/open-zaak/open-zaak/blob/master/LICENSE.md)
All code MUST be published with a license file. |yes | [LICENSE](https://github.com/open-zaak/open-zaak/blob/master/LICENSE.md)
All source code files in the codebase SHOULD include a copyright notice and a license header. | yes | 2020-08-03 review by @ericherman
Codebases MAY have multiple licenses for different types of code and documentation. | | N/A
Documentation MAY be published under Creative Commons licenses that are NOT ‘no derivatives’ or ‘non-commercial’. |  | N/A

## [Use a coherent style](https://standard.publiccode.net/criteria/style.html)

- [x]

Requirement | meets | links and notes
-----|-----|-----
Contributions MUST adhere to either a coding or writing style guide, either your own or an existing one that is advertised in or part of the codebase. | yes | [Style guides](https://github.com/open-zaak/open-zaak/blob/master/CONTRIBUTING.md)
Contributions SHOULD pass automated tests on style. | yes |
Your codebase SHOULD include inline comments and documentation for non-trivial sections. | yes | add to contributing guidelines
You MAY include sections in your style guide on understandable English. |  |

## [Pay attention to codebase maturity](https://standard.publiccode.net/criteria/document-maturity.html)

- [ ]

Requirement | meets | links and notes
-----|-----|-----
A codebase MUST be versioned. | yes | [version list](https://open-zaak.readthedocs.io/en/latest/development/index.html)
A codebase that is ready to use MUST only depend on other codebases that are also ready to use. | | [pinned dependencies](https://github.com/open-zaak/open-zaak/blob/master/requirements/base.txt), document mitigations for < 1.0.0 versions
A codebase that is not yet ready to use MUST have one of these labels: prototype - to test the look and feel, and to internally prove the concept of the technical possibilities, alpha - to do guided tests with a limited set of users, beta - to open up testing to a larger section of the general public, for example to test if the codebase works at scale, pre-release version - code that is ready to be released but hasn’t received formal approval yet. | N/A | Is ready
 A codebase SHOULD contain a log of changes from version to version, for example in the CHANGELOG. | yes | [changelog](https://open-zaak.readthedocs.io/en/latest/development/changelog.html) |
