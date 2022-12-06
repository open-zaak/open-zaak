# Open Zaak cache directory

The files in this directory (except for this `README.md`) are used to cache certain
resources.

This cache is populated by running the `src/manage.py warm_cache` management command,
which is executed as part of the docker image build.

## Do not mount this directory as a volume

You should _not_ mount a volume on this directory, as the image build will contain
the (cached) resources that are only generated at build time.
