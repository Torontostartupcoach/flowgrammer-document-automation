# Environment inventory

Document these on a self-hosted instance. Cloud operators should read current n8n Cloud docs instead of copying numbers from this file. This pack does not quote Cloud prices or concurrency quotas.

| Variable | Why it matters here | Default called out on 2026-09-08 |
|---|---|---|
| N8N_DEFAULT_BINARY_DATA_MODE | Large PDFs in default memory mode can crash the process | `default` (memory). Alternatives: filesystem, database, s3, azure |
| EXECUTIONS_DATA_PRUNE | Whether finished executions are deleted | Operator choice |
| EXECUTIONS_DATA_MAX_AGE | Age prune for finished executions | 336 hours when prune is on |
| EXECUTIONS_DATA_PRUNE_MAX_COUNT | Count prune for finished executions | 10000 when prune is on |
| N8N_DATA_TABLES_MAX_SIZE_BYTES | Demo Data Table duplicate store | 200 MiB instance total |
| N8N_ENCRYPTION_KEY | Credential encryption; must match across queue workers | Operator-set on self-host |
| N8N_ENDPOINT_WEBHOOK_WAIT | Slack or Wait resume path on some setups | Only if you change the default wait endpoint |

`NODE_FUNCTION_ALLOW_BUILTIN` is not required for this starter. Hashing uses the official Crypto node. Do not add `require('crypto')` to Code nodes.

Do not invent additional Cloud worker or quota values. Re-read the official pages before changing production.
