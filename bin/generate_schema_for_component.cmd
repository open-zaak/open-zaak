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

echo Generating Swagger schema for %1...
python src\manage.py generate_swagger_component^
    %SCHEMA_PATH%\swagger2.0.json^
    --overwrite^
    --format=json^
    --mock-request^
    --url https://example.com/api/v1^
    --component=%1

echo Converting Swagger to OpenAPI 3.0...
call .\node_modules\.bin\swagger2openapi %SCHEMA_PATH%\swagger2.0.json -o %SCHEMA_PATH%\openapi.yaml
REM call npm run convert
python src\manage.py patch_error_contenttypes %SCHEMA_PATH%\openapi.yaml

echo Generating resources document...
python src\manage.py generate_swagger_component^
    %SCHEMA_PATH%\resources.md^
    --overwrite^
    --mock-request^
    --url https://example.com/api/v1^
    --to-markdown-table^
    --component=%1

echo Done.
