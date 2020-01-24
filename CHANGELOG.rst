Changelog
=========

1.0.0 (TDB)
-----------

First release of Open Zaak.

Requires manual intervention if you were using beta versions! See below.

Features:

* Zaken API implementation
* Documenten API implementation
* Catalogi API implementation
* Besluiten API implementation
* Autorisaties API implementation
* Support for external APIs
* Admin interface to manage Catalogi
* Admin interface to manage Applicaties and Autorisaties
* Admin interface to view data created via the APIs
* NLX ready
* Documentation
* Performant
* Maximal data integrity
* Scalable
* Kubernetes / VPS / DDS native
* Automated test suite
* Automated deployment

Manual intervention: reset migrations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We've reset the migrations for the 1.0.0 migration. Run the reset script after pulling
the new image/version::

    ./bin/reset_migrations.sh

**On Kubernetes**

Create a job to run the one-time script::

    apiVersion: batch/v1
    kind: Job
    metadata:
      name: resetmigrations
    spec:
      template:
        spec:
          containers:
          - name: resetmigrations
            image: openzaak/open-zaak:latest
            imagePullPolicy: Always
            command: ["./bin/reset_migrations.sh"]
            env:
              - name: DJANGO_SETTINGS_MODULE
                value: openzaak.conf.docker
              - name: SECRET_KEY
                valueFrom:
                  secretKeyRef:
                    name: openzaak-secrets
                    key: SECRET_KEY

              # Database settings
              - name: DB_HOST
                value: "db3.k8s.utrecht.fuga.cyso.net"
              - name: DB_NAME
                value: "openzaak"
              - name: DB_PORT
                value: "5432"
              - name: DB_USER
                value: "openzaak"
              - name: DB_PASSWORD
                valueFrom:
                  secretKeyRef:
                    name: openzaak-secrets
                    key: DB_PASSWORD
          restartPolicy: OnFailure

      backoffLimit: 4


Make sure to fill out the template variables.

Save this Job definition to ``job.yml`` and then apply it::

    kubectl apply -f /tmp/job.yml

**On Docker (appliance/vps/dds/single-server)**

Run a container as a one-time thing::

    docker run \
        -v /home/openzaak/.env:/app/.env \
        --rm \
        openzaak/open-zaak:latest \
        /app/bin/reset_migrations.sh
