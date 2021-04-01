@ECHO OFF

SET COMPOSE_FILE_PATH=%CD%\target\classes\docker\docker-compose.yml
SET COMPOSE_PRODUCTION_FILE_PATH=%CD%\target\classes\docker\docker-compose-production.yml

IF [%M2_HOME%]==[] (
    SET MVN_EXEC=mvn
)

IF NOT [%M2_HOME%]==[] (
    SET MVN_EXEC=%M2_HOME%\bin\mvn
)

IF [%1]==[] (
    echo "Usage: %0 {build|build_start|build_start_it_supported|start|stop|purge|tail|reload_share|reload_acs|build_test|test}"
    GOTO END
)

IF %1==build (
    CALL :build
    GOTO END
)
IF %1==build_start (
    CALL :down
    CALL :build
    CALL :start
    CALL :tail
    GOTO END
)
IF %1==build_start_it_supported (
    CALL :down
    CALL :build
    CALL :prepare-test
    CALL :start
    CALL :tail
    GOTO END
)
IF %1==start (
    CALL :start
    CALL :tail
    GOTO END
)
IF %1==stop (
    CALL :down
    GOTO END
)
IF %1==purge (
    CALL:down
    CALL:purge
    GOTO END
)
IF %1==tail (
    CALL :tail
    GOTO END
)
IF %1==reload_share (
    CALL :build_share
    CALL :start_share
    CALL :tail
    GOTO END
)
IF %1==reload_acs (
    CALL :build_acs
    CALL :start_acs
    CALL :tail
    GOTO END
)
IF %1==build_test (
    CALL :down
    CALL :build
    CALL :prepare-test
    CALL :start
    CALL :test
    CALL :tail_all
    CALL :down
    GOTO END
)
IF %1==test (
    CALL :test
    GOTO END
)
IF %1==build_production (
    CALL :build_production
    GOTO END
)
echo "Usage: %0 {build|build_start|start|stop|purge|tail|reload_share|reload_acs|build_test|test|build_production}"
:END
EXIT /B %ERRORLEVEL%

:start
    docker volume create openzaak-alfresco-acs-volume
    docker volume create openzaak-alfresco-db-volume
    docker volume create openzaak-alfresco-ass-volume
    docker-compose -f "%COMPOSE_FILE_PATH%" up --build -d
EXIT /B 0
:start_share
    docker-compose -f "%COMPOSE_FILE_PATH%" up --build -d openzaak-alfresco-share
EXIT /B 0
:start_acs
    docker-compose -f "%COMPOSE_FILE_PATH%" up --build -d openzaak-alfresco-acs
EXIT /B 0
:down
    if exist "%COMPOSE_FILE_PATH%" (
        docker-compose -f "%COMPOSE_FILE_PATH%" down
    )
EXIT /B 0
:build
	call %MVN_EXEC% clean package
EXIT /B 0
:build_share
    docker-compose -f "%COMPOSE_FILE_PATH%" kill openzaak-alfresco-share
    docker-compose -f "%COMPOSE_FILE_PATH%" rm -f openzaak-alfresco-share
	call %MVN_EXEC% clean package -pl openzaak-alfresco-share,openzaak-alfresco-share-docker
EXIT /B 0
:build_acs
    docker-compose -f "%COMPOSE_FILE_PATH%" kill openzaak-alfresco-acs
    docker-compose -f "%COMPOSE_FILE_PATH%" rm -f openzaak-alfresco-acs
	call %MVN_EXEC% clean package -pl openzaak-alfresco-integration-tests,openzaak-alfresco-platform,openzaak-alfresco-platform-docker
EXIT /B 0
:tail
    docker-compose -f "%COMPOSE_FILE_PATH%" logs -f
EXIT /B 0
:tail_all
    docker-compose -f "%COMPOSE_FILE_PATH%" logs --tail="all"
EXIT /B 0
:prepare-test
    call %MVN_EXEC% verify -DskipTests=true -pl openzaak-alfresco-platform,openzaak-alfresco-integration-tests,openzaak-alfresco-platform-docker
EXIT /B 0
:test
    call %MVN_EXEC% verify -pl openzaak-alfresco-platform,openzaak-alfresco-integration-tests
EXIT /B 0
:purge
    docker volume rm -f openzaak-alfresco-acs-volume
    docker volume rm -f openzaak-alfresco-db-volume
    docker volume rm -f openzaak-alfresco-ass-volume
EXIT /B 0
:build_production
    COPY "..\config\alfresco-global.properties" ".\openzaak-alfresco-platform-docker\src\main\docker\alfresco-production-global.properties"
    CALL :build
    docker-compose -f "%COMPOSE_PRODUCTION_FILE_PATH%" build
EXIT /B 0
