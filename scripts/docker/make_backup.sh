#!/bin/bash

cd ../..

source ./scripts/docker/set_env.sh

echo $NEW_BACKUP_PATH

docker exec -it postgres pg_dump \
--schema=public \
--format=p \
--inserts > $NEW_BACKUP_PATH