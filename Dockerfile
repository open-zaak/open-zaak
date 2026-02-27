# Stage 1 - Compile needed python dependencies
FROM python:3.12-slim-trixie AS build

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
        pkg-config \
        build-essential \
        libpq-dev \
         # required for (log) routing support in uwsgi
         libpcre2-8-0 \
         libpcre2-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Use uv to install dependencies
RUN pip install uv -U
COPY ./requirements /app/requirements
RUN uv pip install --system -r requirements/production.txt


# Stage 2 - build frontend
FROM node:24-trixie-slim AS frontend-build

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
FROM python:3.12-slim-trixie AS production

# Stage 3.1 - Set up the needed production dependencies
# install all the dependencies for GeoDjango
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
        # bare minimum to debug live containers
        procps \
        nano \
        # serve correct Content-Type headers
        media-types \
        # (geo) django dependencies
        postgresql-client \
        gettext \
        libpcre2-8-0 \
        gdal-bin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ./cache /app/cache
COPY ./bin/docker_start.sh /start.sh
COPY ./bin/wait_for_db.sh /wait_for_db.sh
COPY ./bin/celery_worker.sh /celery_worker.sh
COPY ./bin/celery_flower.sh /celery_flower.sh
COPY ./bin/celery_beat.sh /celery_beat.sh
COPY ./bin/reset_migrations.sh /app/bin/reset_migrations.sh
COPY ./bin/uninstall_adfs.sh \
    ./bin/uninstall_django_auth_adfs_db.sql \
    ./bin/dump_configuration.sh \
    /app/bin/
COPY ./bin/check_celery_worker_liveness.py ./bin/
COPY ./bin/setup_configuration.sh /setup_configuration.sh
COPY ./bin/load_fixtures.sh /load_fixtures.sh
COPY ./bin/dump_data.sh /dump_data.sh
COPY ./bin/uwsgi.ini /

RUN mkdir /app/log /app/media /app/private-media /app/tmp
# prevent writing to the container layer, which would degrade performance.
# This also serves as a hint for the intended volumes.
VOLUME ["/app/log", "/app/media", "/app/private-media"]

# copy backend build deps
COPY --from=build /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=build /usr/local/bin/uwsgi /usr/local/bin/uwsgi
COPY --from=build /usr/local/bin/celery /usr/local/bin/celery

# copy frontend build statics
COPY --from=frontend-build /app/src/openzaak/static/ /app/src/openzaak/static/
COPY --from=frontend-build /app/node_modules/@fortawesome/fontawesome-free/webfonts /app/node_modules/@fortawesome/fontawesome-free/webfonts

# Stage 3.2 - Copy source code
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
