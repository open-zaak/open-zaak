@echo off
SETLOCAL

REM Run this script from the root of the repository

if "%VIRTUAL_ENV%"=="" (
    echo You need to activate your virtual env before running this script
    goto :eof
)

if "%1"=="" (
    echo You need to pass the component name in the first argument
    goto :eof
)

set SUBPATH=/%1/api
set SCHEMA_PATH=src/openzaak/components/%1

echo "Generating OAS schema for $1..."
python src/manage.py spectacular_for_component^
    --file $SCHEMA_PATH/openapi.yaml^
    --component


echo Done.
