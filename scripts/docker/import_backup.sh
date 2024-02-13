#!/bin/bash
cd ../..

source ./scripts/docker/set_env.sh

echo $LAST_BACKUP_PATH

export DROP_SCHEMA_FILE=scripts/drop_schema.sql

cat $DROP_SCHEMA_FILE | docker exec -i postgres psql
cat $LAST_BACKUP_PATH | docker exec -i postgres psql

echo LAST_BACKUP_PATH: $LAST_BACKUP_PATH