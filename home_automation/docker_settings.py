import os

db_name = 'home_automation'
db_user = 'postgres'
db_password = os.environ['DATABASE_ENV_POSTGRES_PASSWORD']
db_backend = 'django.db.backends.postgresql_psycopg2'
# db_backend = 'django.db.backends.mysql'
#db_host = '10.16.0.122'
db_host = os.environ["DATABASE_PORT_5432_TCP_ADDR"]
secret = os.environ["DJANGO_SECRET"]
