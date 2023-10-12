cd ../..
export BACKUP_FILE='app_data/backup.sql'
docker exec --env-file .env.prod -it postgres pg_dump \
--schema=public \
--format=p \
--inserts > $BACKUP_FILE