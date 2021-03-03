# Create superuser
cat <<EOF | python /app/src/manage.py shell
from django.contrib.auth import get_user_model

User = get_user_model()

if not User.objects.filter(username="$1").exists():
    User.objects.create_superuser("$1", "$2", "$3")
else:
    print('User "{}" exists already, not created'.format("$1"))
EOF