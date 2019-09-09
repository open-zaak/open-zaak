if [ "$DJANGO_SETTINGS_MODULE" = "openzaak.conf.docker" ];
then
  echo "You are inside docker"
  pip install locustio
  export FILE=/var/lib/postgresql/test_data/zaken_1mln.csv
else
  export FILE=test_data/zaken_1mln.csv
fi

# load fixtures - authentication data and catalogy types
python src/manage.py loaddata src/openzaak/performance_tests/fixtures/auth_fixture.json
python src/manage.py loaddata src/openzaak/performance_tests/fixtures/catalogi_fixture.json

echo "Loading data to DB"
python src/manage.py load_test_data -c -f $FILE

echo "Start performance testing"
locust -f src/openzaak/performance_tests/locustfile.py

#--csv src/openzaak/performance_tests/results/example --no-web -c 100 -r 1 -t 5m
