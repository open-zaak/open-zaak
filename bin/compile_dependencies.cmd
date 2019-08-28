@echo off

for /F "tokens=1" %%i in ('git rev-parse --show-toplevel') do set toplevel=%%i

cd %toplevel%

REM Base deps
pip-compile^
    --no-index^
    requirements/base.in

REM Dependencies for testing
pip-compile^
    --no-index^
    --output-file requirements/test.txt^
    requirements/base.txt^
    requirements/testing.in

REM Dev depedencies - exact same set as CI + some extra tooling
pip-compile^
    --no-index^
    --output-file requirements/dev.txt^
    requirements/test.txt^
    requirements/dev.in
