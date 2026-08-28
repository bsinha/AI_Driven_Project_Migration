# Target Architecture — Bounded Contexts

## Recommended contexts (POC ground truth)

| Bounded Context | Services to consolidate | Key evidence |
|-----------------|-------------------------|--------------|
| **Customer Management** | 5 customer services | Shared customer_db, 87% co-change, single team |
| **Account Management** | 3 account services | Shared lifecycle, FK chains |
| **Payments** | 4 payment + ledger | Sync transaction trace |
| **Risk & Compliance** | risk + compliance | Separate domain, event potential |
| **Notifications** | notification-service | Supporting subdomain |

## Context map (simplified)

```
Customer Management ──► Account Management ──► Payments
                              │                    │
                              │                    ▼
                              │            Risk & Compliance
                              ▼
                        Notifications (events)
```

## Data ownership (target)

- Customer Management owns all customer_db tables
- Account Management owns account_db
- Payments owns payment_db + ledger_db
- Risk & Compliance owns risk_db + compliance_db

See AI-generated ADRs in `platform/projects/*/artifacts/recommend/` after pipeline run.
