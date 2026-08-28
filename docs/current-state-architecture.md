# Current State Architecture — EuroSA Bank (Granular)

## Estate summary

16 granular microservices in `sample-bank/granular-services/`, defined in `landscape-manifest.yaml`.

## Domains

### Customer (5 services — granularity smell)

| Service | Port | DB | Smells |
|---------|------|-----|--------|
| customer-identity-service | 8101 | customer_db | shared_database |
| customer-address-service | 8102 | customer_db | shared_db, sync chain |
| customer-contact-service | 8103 | customer_db | shared_db |
| customer-preference-service | 8104 | customer_db | false cohesion candidate |
| customer-status-service | 8105 | customer_db | lifecycle split |

### Account (3 services)

account-service, account-rules-service, account-lifecycle-service — shared account_db

### Payments (4 + ledger)

payment-initiation → validation → execution → status; ledger-service sync-called

### Supporting

risk-assessment-service, compliance-service (FICA/ZA), notification-service

## Known smells

1. **Granularity:** 5 customer services, 87%+ co-change (see metadata/change-coupling/)
2. **Sync chains:** 7-hop payment trace (metadata/traces/payment-flow.json)
3. **False cohesion:** customer-preference vs risk-assessment (12% co-change)

## Base reference

Original well-bounded demo: [banking-system-microservices](https://github.com/noorkang3242-tech/banking-system-microservices) (optional clone in sample-bank-tmp/)
