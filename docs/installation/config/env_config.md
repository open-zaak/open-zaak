# Environment configuration reference

Open Zaak can be ran both as a Docker container or directly on a VPS or
dedicated server. It relies on other services, such as database and cache
backends, which can be configured through environment variables.

## Available environment variables

### Required

* `DJANGO_SETTINGS_MODULE`: which environment settings to use. Available options:
  - `openzaak.conf.production`
  - `openzaak.conf.staging`
  - `openzaak.conf.docker`
  - `openzaak.conf.dev`
  - `openzaak.conf.ci`

* `SECRET_KEY`: secret key that's used for certain cryptographic utilities. You
  should generate one via
  [miniwebtool](https://www.miniwebtool.com/django-secret-key-generator/)

* `ALLOWED_HOSTS`: a comma separated (without spaces!) list of domains that
  serve the installation. Used to protect against `Host` header attacks.

**Docker**

Additionally, the following optional envvars MUST be set/changed when running
on Docker, since `localhost` is contained within the container:

* `CACHE_DEFAULT`
* `CACHE_AXES`
* `EMAIL_HOST`

### Optional

* `SITE_ID`: defaults to `1`. The database ID of the site object. You usually
  won't have to touch this.

* `DEBUG`: defaults to `False`. Only set this to `True` on a local development
  environment. Various other security settings are derived from this setting!

* `IS_HTTPS`: defaults to the inverse of `DEBUG`. Used to construct absolute
  URLs and controls a variety of security settings.

* `DB_HOST`: hostname of the PostgreSQL database. Defaults to `localhost`,
  unless you're using the `docker` environment, then it defaults to `db`.

* `DB_USER`: username of the database user. Defaults to `openzaak`,
  unless you're using the `docker` environment, then it defaults to `postgres`.

* `DB_PASSWORD`: password of the database user. Defaults to `openzaak`,
  unless you're using the `docker` environment, then it defaults to no password.

* `DB_NAME`: name of the PostgreSQL database. Defaults to `openzaak`,
  unless you're using the `docker` environment, then it defaults to `postgres`.

* `DB_PORT`: port number of the database, defaults to `5432`.

* `CACHE_DEFAULT`: redis cache address for the default cache. Defaults to
  `localhost:6379/0`.

* `CACHE_AXES`: redis cache address for the brute force login protection cache.
  Defaults to `localhost:6379/0`.

* `EMAIL_HOST`: hostname for the outgoing e-mail server. Defaults to
  `localhost`.

* `EMAIL_PORT`: port number of the outgoing e-mail server. Defaults to `25`.
  Note that if you're on Google Cloud, sending e-mail via port 25 is completely
  blocked and you should use 487 for TLS.

* `EMAIL_HOST_USER`: username to connect to the mail server. Default empty.

* `EMAIL_HOST_PASSWORD`: password to connect to the mail server. Default empty.

* `EMAIL_USE_TLS`: whether to use TLS or not to connect to the mail server.
  Defaults to `False`. Should be `True` if you're changing the `EMAIL_PORT` to
  `487`.

* `MIN_UPLOAD_SIZE`: the max allowed size of POST bodies, in bytes. Defaults to
  4GB. Note that you should also configure your web server to allow this.

* `SENDFILE_BACKEND`: which backend to use for authorization-secured upload
  downloads. Defaults to `sendfile.backends.nginx`. See
  [django-sendfile2](https://pypi.org/project/django-sendfile2/) for available
  backends.

* `SENTRY_DSN`: URL of the sentry project to send error reports to. Default
  empty, i.e. -> no monitoring set up. Highly recommended to configure this.

* `JWT_EXPIRY`: duration a JWT is considered to be valid, in seconds. Defaults to 3600 -
  1 hour.

* `LOG_STDOUT`: whether to log to stdout or not. For Docker environments, defaults to
  `True`, for other environments the default is to log to file.

* `PROFILE`: whether to enable profiling-tooling or not. Applies to the development
  settings only. Defaults to `False`.

* `CMIS_ENABLED`: whether to enable the CMIS adapter. Defaults to `False`.

* `CMIS_MAPPER_FILE`: name of the file containing the mapping between the Django and Document Management System names
    for document properties. See the installation section for more details.
    Defaults to the absolute path of `open-zaak/config/cmis_mapper.json`.

## Specifying the environment variables

There are two strategies to specify the environment variables:

* provide them in a `.env` file
* start the Open Zaak processes (with uwsgi/gunicorn/celery) in a process
  manager that defines the environment variables

### Providing a .env file

This is the most simple setup and easiest to debug. The `.env` file must be
at the root of the project - i.e. on the same level as the `src` directory (
NOT _in_ the `src` directory).

The syntax is key-value:

```
SOME_VAR=some_value
OTHER_VAR="quoted_value"
```

### Provide the envvars via the process manager

If you use a process manager (such as supervisor/systemd), use their techniques
to define the envvars. The Open Zaak implementation will pick them up out of
the box.
