# EuroSA Bank — Granular Microservices (POC)

Intentionally **over-decomposed** Java/Spring Boot estate for the AI-driven migration framework POC.

## Structure

- `landscape-manifest.yaml` — 16 granular services, smells, target bounded contexts
- `granular-services/` — Generated Spring Boot modules (one per granular service)
- `../metadata/` — Synthetic traces, co-change, teams, capabilities

## Attribution

Granular landscape derived from concepts in [banking-system-microservices](https://github.com/noorkang3242-tech/banking-system-microservices), intentionally degraded with:

- Shared databases across split services
- Synchronous REST chains
- Granularity and false-cohesion smells

## Run a service locally

```bash
cd granular-services/customer-identity-service
mvn spring-boot:run
```

Requires MySQL on localhost:3306 (see root `docker-compose.yml`).

## Regenerate services

```bash
python ../scripts/generate_granular_services.py
```
