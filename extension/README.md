# Alfresco module

Gebaseerd op het Alfresco SDK4 archetype

Deze module bevat de onderstaande onderdelen.
- Alfresco share configuratie
- Alfresco content model

Daarnaast is er ook een docker test deployment aanwezig gebaseerd op Alfresco 6.2 community. Het is ook mogelijk om dit te wijzigen naar Alfresco 6.2 enterprise, maar hier is wel een Alfresco license voor nodig bij langdurig gebruik.

Het content model en de share configuratie worden gepackaged als .jar bestand. Instructies hiervoor en voor de installatie als module staan hieronder beschreven.

## Vereiste build tools

- Java 1.8 of 11
- Maven 3.3.0 of hoger

## Lokaal draaien

Extra vereiste tools:
- Docker

1. Draai het commando `./run.sh build_start` of `./run.bat build_start`
2. Ga naar http://localhost:8180/share en wacht op een login scherm
3. Login met gebruiker: `admin` en wachtwoord: `admin`

Als het mogelijk is om op Share in te loggen kan development beginnen.

Merk op dat deze test stack bestaat uit 4 containers. Alfresco, met de CMIS connectie, draait op http://localhost:8080/alfresco. Poortnummers zijn te veranderen in pom.xml.

## Deployment op productie

Voor deployment op productie zijn er meerdere opties:
- Als docker container
- Als kubernetes cluster
- Direct op Windows/linux

### Deployment als docker container

Gebruik voor container deployment de juiste docker compose file van [Alfresco docker-compose deployment](https://github.com/Alfresco/acs-deployment/tree/master/docker-compose)

Hiervoor zijn natuurlijk wel images nodig. Deze kunnen als volgt gebouwd worden:
1. Zorg dat de `./pom.xml` de juiste image versie bevat bij `<alfresco.platform.enterprise.version>`.
2. Zorg dat de share image versie in `./pom.xml` vergelijkbaar is met de enterprise image versie. Bijvoorbeeld: share 6.0 levert mogelijk problemen op met alfresco 6.2.2.3 
3. Pas de versie in `<version>` aan naar de huidige versie van Openzaak.
3. Draai het commando `./run.sh build_production` of `./run.bat build_production`.

Hierna zijn er images beschikbaar in een lokale repository met de naam `alfresco-content-services-openzaak-alfresco` en de project versie als tag. Deze resulterende images kunnen gebruikt worden in een docker of Helm deployment.

### Deployment via Helm charts

Gebruik voor helm deployment de juiste helm charts van [Alfresco docker-compose deployment](https://github.com/Alfresco/acs-deployment/tree/master/helm/alfresco-content-services)

Ook hiervoor zijn images nodig. Bouw deze zoals beschreven bij [Deployment als docker-container](###Deployment als docker container). Maak daarna een eigen values file met de juiste images en memory settings. Start de Kubernetes cluster door middel van Helm commando's.

### Deployment direct op Windows
1. Draai het commando `./run.sh build` of `./run.bat build`
2. Pak de `.jar` uit `openzaak-alfresco-platform/target` en plaats deze in de `${ALFRESCO_INSTALLATIE}/modules/platform` folder van Alfresco
3. Pak de `.jar` uit `openzaak-alfresco-share/target` en plaats deze in de `${ALFRESCO_INSTALLATIE}/modules/share` folder van Alfresco
4. Herstart alfresco



Onderstaand de instructies vanuit Alfresco voor meer informatie

# Alfresco AIO Project - SDK 4.0

This is an All-In-One (AIO) project for Alfresco SDK 4.0.

Run with `./run.sh build_start` or `./run.bat build_start` and verify that it

 * Runs Alfresco Content Service (ACS)
 * Runs Alfresco Share
 * Runs Alfresco Search Service (ASS)
 * Runs PostgreSQL database
 * Deploys the JAR assembled modules
 
All the services of the project are now run as docker containers. The run script offers the next tasks:

 * `build_start`. Build the whole project, recreate the ACS and Share docker images, start the dockerised environment composed by ACS, Share, ASS and 
 PostgreSQL and tail the logs of all the containers.
 * `build_start_it_supported`. Build the whole project including dependencies required for IT execution, recreate the ACS and Share docker images, start the 
 dockerised environment composed by ACS, Share, ASS and PostgreSQL and tail the logs of all the containers.
 * `start`. Start the dockerised environment without building the project and tail the logs of all the containers.
 * `stop`. Stop the dockerised environment.
 * `purge`. Stop the dockerised container and delete all the persistent data (docker volumes).
 * `tail`. Tail the logs of all the containers.
 * `reload_share`. Build the Share module, recreate the Share docker image and restart the Share container.
 * `reload_acs`. Build the ACS module, recreate the ACS docker image and restart the ACS container.
 * `build_test`. Build the whole project, recreate the ACS and Share docker images, start the dockerised environment, execute the integration tests from the
 `integration-tests` module and stop the environment.
 * `test`. Execute the integration tests (the environment must be already started).

# Few things to notice

 * No parent pom
 * No WAR projects, the jars are included in the custom docker images
 * No runner project - the Alfresco environment is now managed through [Docker](https://www.docker.com/)
 * Standard JAR packaging and layout
 * Works seamlessly with Eclipse and IntelliJ IDEA
 * JRebel for hot reloading, JRebel maven plugin for generating rebel.xml [JRebel integration documentation]
 * AMP as an assembly
 * Persistent test data through restart thanks to the use of Docker volumes for ACS, ASS and database data
 * Integration tests module to execute tests against the final environment (dockerised)
 * Resources loaded from META-INF
 * Web Fragment (this includes a sample servlet configured via web fragment)

# TODO

  * Abstract assembly into a dependency so we don't have to ship the assembly in the archetype
  * Functional/remote unit tests
