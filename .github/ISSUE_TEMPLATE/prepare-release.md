---
name: Prepare release
about: Checklist for new releases
title: Prepare release x.y.z
labels: ''
type: Release
projects: ["maykinmedia/15"]
---

- [ ] Resolve release blockers
  - [ ] ...
- [ ] Upgrade `open-api-framework` to latest version
- [ ] Check security tab and upgrade packages to fix vulnerabilities
- [ ] Check translations
- [ ] Bump API version number (if applicable)
  - [ ] Version bump
  - [ ] Regenerate API spec
  - [ ] Update READMEs with release dates + links
- [ ] Bump version number with `bin/bump-my-version.sh bump <major|minor|patch>`
- [ ] Run performance tests (see https://bitbucket.org/maykinmedia/open-zaak-performance-test/src/master/README.rst > Kubernetes)
  - [ ] Create and push tag for performance tests (e.g. `<version>-perftest`)
  - [ ] Deploy the new version on Kubernetes
  - [ ] Run performance tests and add the results to the docs
- [ ] Update changelog
- [ ] Update ``docs/introduction/versioning.rst``
- [ ] Check the impact of this release on the Helm charts and make issues for this in https://github.com/maykinmedia/charts if needed, e.g.
  - [ ] New environment variables were added
  - [ ] New setup configuration steps or changes to format
  - [ ] New containers required
  - [ ] ...
