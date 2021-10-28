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

* `DB_CONN_MAX_AGE`: maximum age of a database connection, in seconds. This reduces
  overhead of connecting to the database server for every request. Defaults to `60`.

* `USE_X_FORWARDED_HOST`: whether to grab the domain/host from the `X-Forwarded-Host`
  header or not. This header is typically set by reverse proxies (such as nginx,
  traefik, Apache...). Default `False` - this is a header that can be spoofed and you
  need to ensure you control it before enabling this.

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

* `JWT_LEEWAY`: JWT validation has a time aspect, usually in the form of the `iat` and
  `nbf` claims. Clock drift between server and client can occur. This setting allows
  specifying the leeway in seconds, and defaults to `0` (no leeway). It is advised to
  not make this larger than a couple of minutes.

* `LOG_STDOUT`: whether to log to stdout or not. For Docker environments, defaults to
  `True`, for other environments the default is to log to file.

* `LOG_QUERIES`: enable (query) logging at the database backend level. Note that you
  must also sest `DEBUG=1`, which should be done very sparingly!

* `PROFILE`: whether to enable profiling-tooling or not. Applies to the development
  settings only. Defaults to `False`.

* `CMIS_ENABLED`: whether to enable the CMIS adapter. Defaults to `False`.

* `CMIS_MAPPER_FILE`: name of the file containing the mapping between the Django and Document Management System names
    for document properties. See the installation section for more details.
    Defaults to the absolute path of `open-zaak/config/cmis_mapper.json`.

* `CMIS_URL_MAPPING_ENABLED`: enable the URL shortener when using the CMIS adapter.
  Defaults to `False`.

* `EXTRA_VERIFY_CERTS`: a comma-separated list of paths to certificates to trust, empty
  by default. If you're using self-signed certificates for the services that Open Zaak
  communicates with, specify the path to those (root) certificates here, rather than
  disabling SSL certificate verification. Example:
  `EXTRA_VERIFY_CERTS=/etc/ssl/root1.crt,/etc/ssl/root2.crt`.

* `CURL_CA_BUNDLE`: if this variable is set to an empty string, it disables SSL/TLS certificate verification.
    More information about why can be found [here](https://stackoverflow.com/a/48391751/7146757). Even calls from Open
    Zaak to other services such as the [Selectie Lijst](https://selectielijst.openzaak.nl/) will be disabled, so this
    variable should be used with care to prevent unwanted side-effects.

### Initial superuser creation

A clean installation of Open Zaak comes without pre-installed or pre-configured admin
user by default.

Users of Open Zaak can opt-in to provision an initial superuser via environment
variables. The user will only be created if it doesn't exist yet.

* `OPENZAAK_SUPERUSER_USERNAME`: specify the username of the superuser to create. Setting
  this to a non-empty value will enable the creation of the superuser. Default empty.
* `OPENZAAK_SUPERUSER_EMAIL`: specify the e-mail address to configure for the superuser.
  Defaults to `admin@admin.org`. Only has an effect if `OPENZAAK_SUPERUSER_USERNAME` is set.
* `DJANGO_SUPERUSER_PASSWORD`: specify the password for the superuser. Default empty,
  which means the superuser will be created _without_ password. Only has an effect
  if `OPENZAAK_SUPERUSER_USERNAME` is set.


### Advanced application server options

Open Zaak uses [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/Options.html) under
the hood, which can be configured with a myriad of options. Most of these can be
provided as environment variables as well. The following options below are a
non-exhaustive list of options you may need with Open Zaak.

* `UWSGI_HTTP_TIMEOUT` - defaults to 60s. If Open Zaak does not complete the request
  within this timeout, then uWSGI will error out. This has been observed with certain
  CMIS implementations causing slow requests where 60s is not sufficient.

### Cross-Origin-Resource-Sharing

The following parameters control the CORS policy.

* `CORS_ALLOW_ALL_ORIGINS`: allow cross-domain access from any client. Defaults to `False`.

* `CORS_ALLOWED_ORIGINS`: explicitly list the allowed origins for cross-domain requests.
  Defaults to an empty list. Example: `http://localhost:3000,https://some-app.gemeente.nl`.

* `CORS_ALLOWED_ORIGIN_REGEXES`: same as `CORS_ALLOWED_ORIGINS`, but supports regular
  expressions.

* `CORS_EXTRA_ALLOW_HEADERS`: headers that are allowed to be sent as part of the cross-domain
  request. By default, `Authorization`, `Accept-Crs` and `Content-Crs` are already
  included. The value of this variable is added to these already included headers.
  Defaults to an empty list.

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
