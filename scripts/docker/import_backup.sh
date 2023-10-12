cd ../..

export DROP_SCHEMA_FILE=scripts/drop_schema.sql
export BACKUP_FILE=app_data/backup.sql

cat $DROP_SCHEMA_FILE | docker exec --env-file .env.prod -i postgres psql
cat $BACKUP_FILE | docker exec --env-file .env.prod -i postgres psql