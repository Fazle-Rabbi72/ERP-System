# Hosted services for demo and production (Neon + Redis)

The same code and the same `.env` variables work for three setups. Only values change.

| Setup | PostgreSQL | Redis |
|---|---|---|
| Local dev | local install, `DB_SSL_MODE=disable` | local install, `REDIS_SSL=false` |
| Cloud demo / SaaS | Neon, `DB_SSL_MODE=verify-full` | Redis Cloud, `REDIS_SSL` per dashboard |
| On-premise | server's own PostgreSQL | server's own Redis |

## Neon (PostgreSQL)
1. Create a project at neon.tech (region closest to your users; Singapore is nearest to Bangladesh if offered).
2. Create two branches: `main` (production/demo) and `dev` (daily development). Never point dev at `main`.
3. In **Connect**, copy both strings per branch:
   - **Pooled** host (contains `-pooler`) -> `DB_HOST` (runtime app).
   - **Direct** host (no `-pooler`) -> `DB_MIGRATOR_HOST` (Alembic migrations).
4. `DB_SSL_MODE=verify-full`. `DB_NAME`, `DB_ADMIN_USER`, `DB_ADMIN_PASSWORD` come from the Neon connection string (the owner role).
5. The DB bootstrap script (step F3) creates the non-owner roles `nexzen_app` and `nexzen_migrator` with the passwords from your `.env`. The app must connect as `nexzen_app`, never as the Neon owner role, otherwise Row-Level Security would be bypassed.

Why this design is safe on Neon's pooler: tenant id and statement timeout are set per transaction with `set_config(..., true)`, never per session, so nothing leaks between requests.

Free-plan facts to re-check on neon.tech before a demo (limits change): storage per project, monthly compute hours, 5-minute idle suspend (the first request after idle is slower; `pool_pre_ping` and `DB_POOL_RECYCLE_SECONDS` handle dropped connections).

## Redis
Recommendation: **Redis Cloud free plan**, not Upstash free.
- ARQ polls Redis every 0.5 s by default, about 5 million commands per month per worker. Upstash free is metered per command (about 500,000 per month), so a worker would exhaust it in days. Redis Cloud free has no command limit but is capped (about 30 MB, 100 ops/s, 30 connections).
- Rules for the free plan: keep `REDIS_MAX_CONNECTIONS` low, run one ARQ worker, and raise ARQ `poll_delay` (set in step F8).
- Copy host, port, password from the Redis Cloud dashboard. Set `REDIS_SSL=true` only if the endpoint you were given uses TLS; if it is plain, tell me, because production should then use a TLS-capable endpoint or a paid tier.
- The free plan gives one database, so dev and demo should not share it: use local Redis (Memurai) for dev.

## Production safety checks (enforced at startup)
With `APP_ENV=production` the app refuses to start when a remote database has `DB_SSL_MODE=disable`, a remote Redis has `REDIS_SSL=false` or no password, secrets are `CHANGE_ME`, or the JWT key is shorter than 32 characters.

## For real production
Free tiers are for demos. For paying customers, upgrade Neon and Redis, or move to the on-premise/own-server setup. Both need only `.env` changes.
