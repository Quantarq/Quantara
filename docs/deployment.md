
# Production Deployment Guide

This document outlines the standard operating procedure for deploying the Quantara application to a production environment. All commands should be executed by an authorized DevOps engineer with production access.

> **⚠️ Security Warning:** Never hardcode sensitive credentials (passwords, IP addresses, private keys) in this repository. Use a secure vault/secret manager to inject variables at runtime.

## 1. Prerequisites & Environment Setup
Before initiating a deployment, ensure the target environment meets the following specifications:
* **Server Specs:** Minimum 4 vCPUs, 8GB RAM, and 50GB NVMe storage.
* **Dependencies:** Docker (v24+), Docker Compose (v2+), and Node.js (v18+).
* **Network Setup:** Configured domain name (e.g., `api.quantara.internal`) and provisioned SSL certificates.

### 1.1 Environment Variables Checklist
The application relies on a strictly defined `.env.production` file. 
Ensure your environment contains all required secrets. 
*🔗 See [docs/environment_variables.md](./environment_variables.md) for the complete configuration reference.*

---

## 2. Deployment Steps

### Step 2.1: Pull and Build the Docker Images
Navigate to the application root on the production server and pull the latest changes, then build the images:
```bash
git checkout main
git pull origin main

# Build the containers using the production overrides
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
