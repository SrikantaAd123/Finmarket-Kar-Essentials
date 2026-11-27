
# Deployment Guide

## 1. Overview

This document explains how to prepare and deploy the Finmarket Kart Essentials backend.

The project supports containerized deployment using Docker and Docker Compose.

The backend application uses FastAPI and Uvicorn.

## 2. Deployment Structure

The deployment-related files are organized as follows:

```text
deployment/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── monitoring/
│   └── prometheus.yml
└── nginx/
    └── nginx.conf
```

### File Responsibilities

| File | Responsibility |
| --- | --- |
| Dockerfile | Defines the backend application image |
| docker-compose.yml | Defines and manages application containers |
| prometheus.yml | Defines Prometheus monitoring configuration |
| nginx.conf | Defines Nginx reverse proxy configuration |

## 3. Prerequisites

Install and configure the following tools before deployment:

- Docker Desktop
- Docker Engine
- Docker Compose
- Git
- Python 3.14 or compatible runtime for local execution

For Windows, start Docker Desktop and ensure its Linux container engine is running.

Verify the Docker installation:

```powershell
docker version
docker compose version
```

Both commands should return version information without connection errors.

## 4. Environment Configuration

The application may require environment variables for database connectivity, authentication, payment processing, and application configuration.

Create a `.env` file in the location expected by the application and Docker Compose configuration.

Example structure:

```env
APP_ENV=development
DEBUG=false

DATABASE_URL=your_database_connection_string

ZITADEL_DOMAIN=your_zitadel_domain
ZITADEL_PROJECT_ID=your_project_id

RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
```

The variable names above are illustrative. Use the exact names referenced by the application's settings and deployment configuration.

### Security Guidelines

- Never commit `.env` files to Git.
- Do not expose database passwords or API secrets.
- Use production credentials only in the production environment.
- Restrict access to deployment configuration files.
- Rotate credentials if they are accidentally exposed.

## 5. Dockerfile Configuration

The Dockerfile defines the backend application container.

The project Dockerfile uses:

- Python 3.14 slim as the base image.
- `uv` for Python dependency management.
- `/app` as the container working directory.
- Port `8000` for the FastAPI application.
- Uvicorn to start the application.

The application entry point is:

```text
backend.main:app
```

Ensure the Docker build context contains the required project files, including:

- `pyproject.toml`
- `uv.lock`
- `backend/`

The Dockerfile and Compose build paths must correctly reference these files.

## 6. Validate Docker Compose Configuration

Navigate to the project root:

```powershell
cd "C:\Users\SrikantaAdiraju\Downloads\Finmarket Kart Essentials"
```

Validate the Compose configuration:

```powershell
docker compose -f deployment/docker/docker-compose.yml config
```

This command checks whether the Docker Compose configuration can be parsed and resolved.

Resolve any configuration errors before building the application.

## 7. Build the Docker Image

Build the application image:

```powershell
docker compose -f deployment/docker/docker-compose.yml build
```

Docker reads the Dockerfile and builds the required container images.

If the build fails:

1. Check the Dockerfile path.
2. Verify the build context.
3. Confirm that `pyproject.toml` and `uv.lock` are available in the build context.
4. Check dependency installation output.
5. Review the Docker build error message.

## 8. Start the Application

Start the configured containers in detached mode:

```powershell
docker compose -f deployment/docker/docker-compose.yml up -d
```

The `-d` option runs the containers in the background.

Check container status:

```powershell
docker compose -f deployment/docker/docker-compose.yml ps
```

## 9. View Application Logs

Display logs for the configured services:

```powershell
docker compose -f deployment/docker/docker-compose.yml logs
```

Follow logs continuously:

```powershell
docker compose -f deployment/docker/docker-compose.yml logs -f
```

To stop following logs, press:

```text
Ctrl + C
```

Inspect logs when investigating:

- Application startup failures.
- Database connection errors.
- Missing Python dependencies.
- Authentication configuration problems.
- Payment integration errors.

## 10. Access the FastAPI Application

The Dockerfile exposes port `8000`.

When the Compose configuration publishes that port to the host, the application can be accessed using the configured host port.

For a host mapping of `8000:8000`, the application URLs are:

| Resource | URL |
| --- | --- |
| API base | [http://localhost:8000](http://localhost:8000) |
| Swagger UI | [http://localhost:8000/docs](http://localhost:8000/docs) |
| ReDoc | [http://localhost:8000/redoc](http://localhost:8000/redoc) |
| OpenAPI schema | [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json) |

These URLs assume that the application is running and the Compose port mapping is configured accordingly.

## 11. Stop the Application

Stop and remove the containers created by the Compose project:

```powershell
docker compose -f deployment/docker/docker-compose.yml down
```

This command does not normally remove named volumes.

To remove associated named volumes as well, use:

```powershell
docker compose -f deployment/docker/docker-compose.yml down -v
```

**Warning:** Removing volumes can permanently delete persisted database or application data. Use this command only when that data is no longer required.

## 12. Troubleshooting

### Docker Engine Connection Error

Example:

```text
failed to connect to the docker API
```

Possible solution:

1. Start Docker Desktop.
2. Wait until the Docker Engine is running.
3. Confirm that Docker is using Linux containers.
4. Run `docker version` again.

### FastAPI Module Not Found

Example:

```text
ModuleNotFoundError: No module named 'fastapi'
```

Possible causes:

- Dependencies were not installed in the container.
- The dependency configuration is incorrect.
- The Docker build context is incorrect.
- The image was built before dependency configuration was updated.

Check the dependency declarations in `pyproject.toml` and the dependency installation step in the Dockerfile.

Rebuild the image after correcting the configuration:

```powershell
docker compose -f deployment/docker/docker-compose.yml build --no-cache
```

### Container Exits Immediately

Inspect container status:

```powershell
docker compose -f deployment/docker/docker-compose.yml ps -a
```

Inspect logs:

```powershell
docker compose -f deployment/docker/docker-compose.yml logs
```

Check the application entry point, environment variables, database connectivity, and installed dependencies.

### Port Already in Use

If port `8000` is already occupied, identify the process using it or update the host-side port mapping in the Compose configuration.

## 13. Production Deployment Recommendations

Before deploying to production:

- Set production environment variables.
- Use strong database credentials.
- Configure HTTPS.
- Restrict database network access.
- Configure appropriate CORS origins.
- Keep secrets outside source control.
- Configure persistent storage where required.
- Configure database backups.
- Monitor application health and logs.
- Avoid exposing internal services publicly.
- Use a production-ready reverse proxy configuration.

## 14. Deployment Checklist

- [ ] Docker Desktop is running.
- [ ] Docker Engine is accessible.
- [ ] Docker Compose configuration is valid.
- [ ] Environment variables are configured.
- [ ] Docker image builds successfully.
- [ ] Containers start successfully.
- [ ] Database connectivity is verified.
- [ ] FastAPI endpoints are accessible.
- [ ] Application logs show no critical errors.
- [ ] Production security settings are reviewed.

## 15. Summary

Docker and Docker Compose provide a repeatable way to package and run the Finmarket Kart Essentials backend.

The deployment workflow consists of:

1. Preparing environment configuration.
2. Validating Docker Compose.
3. Building the application image.
4. Starting the containers.
5. Verifying application availability.
6. Monitoring logs.
7. Stopping containers when required.
