# load fixtures - authentication data and catalogy types
python src/manage.py loaddata src/openzaak/performance_tests/fixtures/auth_fixture.json
python src/manage.py loaddata src/openzaak/performance_tests/fixtures/catalogi_fixture.json

# load 1 mln zaken into DB
python src/manage.py load_test_data -c

# run performance tests
#locust -f src/openzaak/performance_tests/locustfile.py

#--csv src/openzaak/performance_tests/results/example --no-web -c 100 -r 1 -t 5m
# clean DB ???
