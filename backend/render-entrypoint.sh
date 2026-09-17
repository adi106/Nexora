#!/bin/sh
# Render's dockerCommand field does its own text substitution on $VAR-style
# tokens before handing the string to a shell, which mangles inline command
# substitution (e.g. `$(...)`) and quoting. Keeping this logic in a real
# script file, invoked by a plain path with no $ characters in render.yaml,
# lets an actual shell evaluate it instead.
set -e

export DATABASE_URL=$(echo "$DATABASE_URL" | sed -E 's#^postgres(ql)?://#postgresql+psycopg://#')
export CORS_ORIGINS="https://${FRONTEND_HOST},http://localhost:5173"

alembic upgrade head
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT"
