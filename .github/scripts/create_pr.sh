#!/usr/bin/env bash
set -euo pipefail

# Create a feature branch, commit changes and open a draft PR using `gh`.
# Requires `gh auth login` to be completed interactively before running.

git checkout -b feature/add-tenant-fixtures
git add -A
git commit -m "Add tenant_client fixture, integration test, README improvements"
git push --set-upstream origin feature/add-tenant-fixtures

# Create draft PR (if `gh` is authenticated)
gh pr create --title "Add tenant_client fixture + docs" --body "Adds tenant_client fixture, an integration test, and README instructions for creating tenants in dev." --draft || true
