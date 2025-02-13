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
- [ ] Check translations
- [ ] Bump API version number (if applicable)
  - [ ] Version bump
  - [ ] Regenerate API spec
  - [ ] Update READMEs with release dates + links
- [ ] Bump version number with `bumpversion <major|minor|patch>` or `bump-my-version bump <major|minor|patch>`
- [ ] Run performance tests
  - [ ] Create and push tag for performance tests (e.g. `<version>-perftest`)
  - [ ] Deploy the new version
  - [ ] Run performance tests and add the results to the docs
- [ ] Update changelog
