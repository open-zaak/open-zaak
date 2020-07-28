# Contribution guidelines for Open Zaak

If you want to contribute to Open Zaak, we ask you to follow these guidelines.

## Reporting bugs
If you have encountered a bug in Open Zaak, please check if an issue already exists in the list of existing [issues](https://github.com/open-zaak/open-zaak/issues), if such an issue does not exist, you can create one [here](https://github.com/open-zaak/open-zaak/issues/new/choose). When writing the bug report, try to add a clear example that shows how to reproduce said bug.

## Adding new features
Before making making changes to the code, we advise you to first check the list of existing [issues](https://github.com/open-zaak/open-zaak/issues) for Open Zaak to see if an issue for the suggested changes already exists. If such an issue does not exist, you can create one [here](https://github.com/open-zaak/open-zaak/issues/new/choose). Creating an issue gives an opportunity for other developers to give tips even before you start coding. If you are in the early idea phase, or if your feature requires larger changes, you can also discuss it on [the mailing list](https://lists.publiccode.net/mailman/postorius/lists/openzaak-discuss.lists.publiccode.net/) to make sure you are heading in the right direction.

### Code style
To keep the code clean and readable, Open Zaak uses:
- [`isort`](https://github.com/timothycrosley/isort) to order the imports
- [`black`](https://github.com/psf/black) to format the code and keep diffs for pull requests small
- [`flake8`](https://github.com/PyCQA/flake8) to clean up code (removing unused imports, etc.)

Whenever a branch is pushed or a pull request is made, the code will be checked in CI by the tools mentioned above, so make sure to install these tools and run them locally before pushing branches/making PRs.

Open Zaak aims to meet the criteria of the [Standard for Public Code](https://standard.publiccode.net). Please make sure that your pull requests are compliant, that will make the reviews quicker.

### Forking the repository
In order to implement changes to Open Zaak when you do not have rights for the [Open Zaak repository](https://github.com/open-zaak/open-zaak), you must first fork the repository. Once the repository is forked, you can clone it to your local machine.

### Making the changes
On your local machine, create a new branch, and name it like:
- `feature/some-new-feature`, if the changes implement a new feature
- `issue/some-issue`, if the changes fix an issue

Once you have made changes or additions to the code, you can commit them (try to keep the commit message descriptive but short). If an issue exists in the [Open Zaak issue list](https://github.com/open-zaak/open-zaak/issues/) for the changes you made, be sure to format your commit message like `"Fixes #<issue_id> -- description of changes made`, where `<issue_id>"` corresponds to the number of the issue on GitHub. To demonstrate that the changes implement the new feature/fix the issue, make sure to also add tests to the existing Django testsuite.

### Making a pull request
If all changes have been committed, you can push the branch to your fork of the repository and create a pull request to the `master` branch of the Open Zaak repository. Your pull request will be reviewed, if applicable feedback will be given and if everything is approved, it will be merged.

### Reviews on releases

All pull requests will be reviewed before they are merged to a release branch. As well as being reviewed for functionality and following the code style they will be checked against the [Standard for Public Code](https://standard.publiccode.net) by a [codebase steward](https://publiccode.net/codebase-stewardship/) from the [Foundation for Public Code](https://publiccode.net). Reviews will usually start within two business days of a submitted pull request.

## Under Foundation for Public Code incubating codebase stewardship

Open Zaak is in incubation [codebase stewardship](https://publiccode.net/codebase-stewardship/) with the [Foundation for Public Code](https://publiccode.net).

The [codebase stewardship activities](https://about.publiccode.net/activities/codebase-stewardship/activities.html) by the Foundation for Public Code on this codebase include:

* facilitating the community and its members
* help all contributors contribute in line with the contributing guidelines and the [Standard for Public Code](https://standard.publiccode.net/)
* work with the community to tell their stories, create their brand and market their products
* support the technical and product steering teams

