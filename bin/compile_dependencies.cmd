@echo off

for /F "tokens=1" %%i in ('git rev-parse --show-toplevel') do set toplevel=%%i

cd %toplevel%

REM Base deps
pip-compile^
    --no-index^
    requirements/base.in

REM Dev deps
pip-compile^
    --no-index^
    --output-file requirements/dev.txt^
    requirements/base.txt^
    requirements/testing.in^
    requirements/dev.in
