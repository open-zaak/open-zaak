# Contribution guidelines for Open Zaak

If you want to contribute to Open Zaak, we ask you to follow these guidelines.

## Reporting bugs
If you have encountered a bug in Open Zaak, please check if an issue already exists in the list of existing [issues](https://github.com/open-zaak/open-zaak/issues), if such an issue does not exist, you can create one [here](https://github.com/open-zaak/open-zaak/issues/new/choose). When writing the bug report, try to add a clear example that shows how to reproduce said bug.

## Adding new features
Before making making changes to the code, we advise you to first check the list of existing [issues](https://github.com/open-zaak/open-zaak/issues) for Open Zaak to see if an issue for the suggested changes already exists. If such an issue does not exist, you can create one [here](https://github.com/open-zaak/open-zaak/issues/new/choose). Creating an issue gives an opportunity for other developers to give tips even before you start coding.

### Code style
To keep the code clean and readable, Open Zaak uses:

- [`ruff`](https://docs.astral.sh/ruff/) to format and clean up code (removing unused imports, etc.)

Whenever a branch is pushed or a pull request is made, the code will be checked in CI by Ruff, so
make sure to install and run it locally before pushing branches/making pull requests.

Open Zaak aims to meet the criteria of the [Standard for Public Code](https://standard.publiccode.net). Please make sure that your pull requests are compliant, that will make the reviews quicker.

### Forking the repository
In order to implement changes to Open Zaak when you do not have rights for the [Open Zaak repository](https://github.com/open-zaak/open-zaak), you must first fork the repository. Once the repository is forked, you can clone it to your local machine.

### Making the changes
On your local machine, create a new branch, and name it like:
- `feature/some-new-feature`, if the changes implement a new feature
- `issue/some-issue`, if the changes fix an issue

Once you have made changes or additions to the code, you can commit them (try to keep the commit message descriptive but short). If an issue exists in the [Open Zaak issue list](https://github.com/open-zaak/open-zaak/issues/) for the changes you made, be sure to format your commit message like `"Fixes #<issue_id> -- description of changes made`, where `<issue_id>"` corresponds to the number of the issue on GitHub. To demonstrate that the changes implement the new feature/fix the issue, make sure to also add tests to the existing Django testsuite.

### Making a pull request
If all changes have been committed, you can push the branch to your fork of the repository and create a pull request to the `main` branch of the Open Zaak repository. Your pull request will be reviewed, if applicable feedback will be given and if everything is approved, it will be merged.

### Reviews on releases

All pull requests will be reviewed before they are merged to a release branch.
