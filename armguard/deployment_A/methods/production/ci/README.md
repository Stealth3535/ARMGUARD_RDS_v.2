# ARMGUARD Deployment A CI Package

This package adds staging and production deployment automation with rollback support.

## Files

- deploy_staging.sh
- deploy_production.sh
- rollback_latest.sh
- .env.staging.template
- .env.production.template
- systemd/armguard-staging.service
- systemd/gunicorn-armguard.service

## GitHub Actions Workflow

Workflow file:

- .github/workflows/deployment-a-cicd.yml

## Required Environment Protection (Approval Gates)

Configure GitHub Environments to enforce approvals before deployment:

1. In repository settings, open Environments.
2. For `production`, enable Required reviewers (at least one approver).
3. Optionally set a wait timer and restrict deployment branches.

The workflow already targets `staging` and `production` environments, so these protections are enforced automatically when configured.

## Required GitHub Secrets

### Staging

- STAGING_SSH_KEY
- STAGING_HOST
- STAGING_USER
- STAGING_DEPLOY_COMMAND
- STAGING_HEALTHCHECK_COMMAND (optional)

### Production

- PRODUCTION_SSH_KEY
- PRODUCTION_HOST
- PRODUCTION_USER
- PRODUCTION_DEPLOY_COMMAND
- PRODUCTION_HEALTHCHECK_COMMAND (optional)

## Recommended Remote Commands

Use these values for secret commands after placing scripts on server and making them executable.

### STAGING_DEPLOY_COMMAND

cd /opt/armguard && PROJECT_DIR=/opt/armguard BRANCH=main SERVICE_NAME=armguard-staging bash deployment_A/methods/production/ci/deploy_staging.sh

### PRODUCTION_DEPLOY_COMMAND

cd /opt/armguard && PROJECT_DIR=/opt/armguard BRANCH=main SERVICE_NAME=gunicorn-armguard SECONDARY_SERVICE=armguard-daphne bash deployment_A/methods/production/ci/deploy_production.sh

### STAGING_HEALTHCHECK_COMMAND (optional)

cd /opt/armguard && bash deployment_A/methods/production/health-check.sh

### PRODUCTION_HEALTHCHECK_COMMAND (optional)

cd /opt/armguard && bash deployment_A/methods/production/health-check.sh

## Server Setup Steps

1. Copy env templates:
   - cp deployment_A/methods/production/ci/.env.staging.template /opt/armguard/.env.staging
   - cp deployment_A/methods/production/ci/.env.production.template /opt/armguard/.env.production
2. Fill real values in both env files.
3. Install service templates from systemd folder if needed.
4. Mark scripts executable:
   - chmod +x deployment_A/methods/production/ci/*.sh
5. Reload systemd:
   - sudo systemctl daemon-reload

## Notes

- deploy_production.sh performs automatic rollback to the latest pre-deploy backup archive if deployment fails.
- rollback_latest.sh allows manual rollback to the latest production backup.
- Backups are stored under PROJECT_DIR/backups.
- If health-check secrets are not set, workflow health-check steps are skipped.
