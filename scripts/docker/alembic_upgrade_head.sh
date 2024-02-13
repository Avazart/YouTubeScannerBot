#!/bin/bash
cd ../..
docker exec --env-file .env.prod -it youtube_scanner_app alembic upgrade head