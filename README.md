# Ason Verification Platform — Backend

Backend orchestrator service for the Ason Verification Platform.

## Overview

This repository contains the core FastAPI backend (`main.py`) that powers the verification platform. It serves ~75 endpoints covering verification, security, compliance, dashboards, onboarding, and API documentation.

## Quick Start

```bash
pip install -r ../services/orchestrator/requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/verify/run` | Submit verification job |
| GET | `/health/deep` | Deep health check |
| GET | `/dashboard/security` | Security posture |
| GET | `/dashboard/compliance` | Compliance matrix |
| POST | `/onboard/tenant` | Provision tenant |
| GET | `/docs/openapi` | OpenAPI 3.1 spec |

## Architecture

- **Framework**: FastAPI (Python 3.11+)
- **Server**: Uvicorn (ASGI)
- **Features**: 150+
- **Compliance**: 12 frameworks, 176 controls

See the [main repository](https://github.com/mnmballa2323/ason.project) for full documentation.
