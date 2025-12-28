<#
init-db.ps1
PowerShell script to initialize DB role, test DB and run migrations in docker-compose.
Usage (PowerShell):
  ./scripts/init-db.ps1 -PostgresContainer postgres-saas -DjangoContainer django
#>
param(
  [string]$PostgresContainer = 'postgres-saas',
  [string]$DjangoContainer = 'django'
)

Write-Host "Postgres container: $PostgresContainer"
Write-Host "Django container: $DjangoContainer"

Write-Host "==> Ensuring role 'saas_user' exists with CREATEDB"
# Create or alter role (use single-quote wrapper for psql -c)
docker exec -i $PostgresContainer psql -U postgres -c 'DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = ''saas_user'') THEN CREATE ROLE saas_user LOGIN PASSWORD ''1234567890''; ELSE ALTER ROLE saas_user WITH PASSWORD ''1234567890''; END IF; END $$;'

docker exec -i $PostgresContainer psql -U postgres -c 'ALTER ROLE saas_user CREATEDB;'

Write-Host "==> Ensuring test database exists and is owned by saas_user"
# Create DB only if missing
$createCmd = 'psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname=\'test_saas_automacoes_web\'" | grep -q 1 || psql -U postgres -c "CREATE DATABASE test_saas_automacoes_web OWNER saas_user"'
# run using bash -c inside container
docker exec -i $PostgresContainer bash -c $createCmd

Write-Host "==> Running Django migrations (inside $DjangoContainer if present)"
try {
  docker exec -i $DjangoContainer python manage.py migrate --no-input
} catch {
  Write-Host "Could not run migrations inside container '$DjangoContainer'. Ensure the container exists or run migrations manually."
  Write-Host "Manual: docker exec -it $DjangoContainer python manage.py migrate --no-input"
}

Write-Host "==> Done."
