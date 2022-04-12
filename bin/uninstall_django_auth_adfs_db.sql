BEGIN;
--
-- Delete model ADFSConfig
--
DROP TABLE "django_auth_adfs_db_adfsconfig" CASCADE;

DELETE FROM django_migrations WHERE app = 'django_auth_adfs_db';

COMMIT;
