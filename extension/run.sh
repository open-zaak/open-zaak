#!/bin/sh

export COMPOSE_FILE_PATH="${PWD}/target/classes/docker/docker-compose.yml"
export COMPOSE_PRODUCTION_FILE_PATH="${PWD}/target/classes/docker/docker-compose-production.yml"


if [ -z "${M2_HOME}" ]; then
  export MVN_EXEC="mvn"
else
  export MVN_EXEC="${M2_HOME}/bin/mvn"
fi

start() {
    docker volume create openzaak-alfresco-acs-volume
    docker volume create openzaak-alfresco-db-volume
    docker volume create openzaak-alfresco-ass-volume
    docker-compose -f "$COMPOSE_FILE_PATH" up --build -d
}

start_share() {
    docker-compose -f "$COMPOSE_FILE_PATH" up --build -d openzaak-alfresco-share
}

start_acs() {
    docker-compose -f "$COMPOSE_FILE_PATH" up --build -d openzaak-alfresco-acs
}

down() {
    if [ -f "$COMPOSE_FILE_PATH" ]; then
        docker-compose -f "$COMPOSE_FILE_PATH" down
    fi
}

purge() {
    docker volume rm -f openzaak-alfresco-acs-volume
    docker volume rm -f openzaak-alfresco-db-volume
    docker volume rm -f openzaak-alfresco-ass-volume
}

build() {
    $MVN_EXEC clean package
}

build_share() {
    docker-compose -f "$COMPOSE_FILE_PATH" kill openzaak-alfresco-share
    yes | docker-compose -f "$COMPOSE_FILE_PATH" rm -f openzaak-alfresco-share
    $MVN_EXEC clean package -pl openzaak-alfresco-share,openzaak-alfresco-share-docker
}

build_acs() {
    docker-compose -f "$COMPOSE_FILE_PATH" kill openzaak-alfresco-acs
    yes | docker-compose -f "$COMPOSE_FILE_PATH" rm -f openzaak-alfresco-acs
    $MVN_EXEC clean package -pl openzaak-alfresco-integration-tests,openzaak-alfresco-platform,openzaak-alfresco-platform-docker
}

tail() {
    docker-compose -f "$COMPOSE_FILE_PATH" logs -f
}

tail_all() {
    docker-compose -f "$COMPOSE_FILE_PATH" logs --tail="all"
}

prepare_test() {
    $MVN_EXEC verify -DskipTests=true -pl openzaak-alfresco-platform,openzaak-alfresco-integration-tests,openzaak-alfresco-platform-docker
}

test() {
    $MVN_EXEC verify -pl openzaak-alfresco-platform,openzaak-alfresco-integration-tests
}

build_production() {
    yes | cp -f "../config/alfresco-global.properties" "./openzaak-alfresco-platform-docker/src/main/docker/alfresco-production-global.properties"
    build
    docker-compose -f "$COMPOSE_PRODUCTION_FILE_PATH" build
}

case "$1" in
  build)
    build
    ;;
  build_start)
    down
    build
    start
    tail
    ;;
  build_start_it_supported)
    down
    build
    prepare_test
    start
    tail
    ;;
  start)
    start
    tail
    ;;
  stop)
    down
    ;;
  purge)
    down
    purge
    ;;
  tail)
    tail
    ;;
  reload_share)
    build_share
    start_share
    tail
    ;;
  reload_acs)
    build_acs
    start_acs
    tail
    ;;
  build_test)
    down
    build
    prepare_test
    start
    test
    tail_all
    down
    ;;
  test)
    test
    ;;
  build_production)
    build_production
    ;;
  *)
    echo "Usage: $0 {build|build_start|start|stop|purge|tail|reload_share|reload_acs|build_test|test|build_production}"
esac
