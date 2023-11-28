# Stage 1 - Compile needed python dependencies
FROM python:3.10-slim-bookworm AS build

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
        pkg-config \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./requirements /app/requirements
RUN pip install pip -U
RUN pip install -r requirements/production.txt


# Stage 2 - build frontend
FROM node:16-bookworm-slim AS frontend-build

WORKDIR /app

# copy configuration/build files
COPY ./build /app/build/
COPY ./*.json ./*.js ./.babelrc /app/

# install WITH dev tooling
RUN npm ci --legacy-peer-deps

# copy source code
COPY ./src /app/src

# build frontend
RUN npm run build


# Stage 3 - Build docker image suitable for execution and deployment
FROM python:3.10-slim-bookworm AS production

# Stage 3.1 - Set up the needed production dependencies
# install all the dependencies for GeoDjango
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
        # bare minimum to debug live containers
        procps \
        nano \
        # serve correct Content-Type headers
        mime-support \
        # (geo) django dependencies
        postgresql-client \
        gettext \
        binutils \
        libproj-dev \
        gdal-bin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ./cache /app/cache
COPY ./bin/docker_start.sh /start.sh
COPY ./bin/wait_for_db.sh /wait_for_db.sh
COPY ./bin/celery_worker.sh /celery_worker.sh
COPY ./bin/celery_flower.sh /celery_flower.sh
COPY ./bin/reset_migrations.sh /app/bin/reset_migrations.sh
COPY ./bin/uninstall_adfs.sh \
    ./bin/uninstall_django_auth_adfs_db.sql \
    ./bin/dump_configuration.sh \
    /app/bin/

RUN mkdir /app/log /app/config /app/media /app/private-media
# prevent writing to the container layer, which would degrade performance.
# This also serves as a hint for the intended volumes.
VOLUME ["/app/log", "/app/media", "/app/private-media"]

# copy backend build deps
COPY --from=build /usr/local/lib/python3.10 /usr/local/lib/python3.10
COPY --from=build /usr/local/bin/uwsgi /usr/local/bin/uwsgi
COPY --from=build /usr/local/bin/celery /usr/local/bin/celery

COPY --from=frontend-build /app/src/openzaak/static/css /app/src/openzaak/static/css
COPY --from=frontend-build /app/src/openzaak/static/js /app/src/openzaak/static/js

# Stage 3.2 - Copy source code
COPY ./config /app/config
COPY ./src /app/src

RUN groupadd -g 1000 openzaak \
    && useradd -M -u 1000 -g 1000 openzaak \
    && chown -R openzaak:openzaak /app

# drop privileges
USER openzaak

ARG COMMIT_HASH
ARG RELEASE
ENV GIT_SHA=${COMMIT_HASH}
ENV RELEASE=${RELEASE}

ENV DJANGO_SETTINGS_MODULE=openzaak.conf.docker

ARG SECRET_KEY=dummy

LABEL org.label-schema.vcs-ref=$COMMIT_HASH \
      org.label-schema.vcs-url="https://github.com/open-zaak/open-zaak" \
      org.label-schema.version=$RELEASE \
      org.label-schema.name="Open Zaak"

# Run management commands:
# * collectstatic -> bake the static assets into the image
# * compilemessages -> ensure the translation catalog binaries are present
# * warm_cache -> writes to the filesystem cache so that orgs don't need to open the
#   firewall to github
RUN python src/manage.py collectstatic --noinput \
    && python src/manage.py compilemessages \
    && python src/manage.py warm_cache

EXPOSE 8000
CMD ["/start.sh"]
