# Credential placeholders

Create these in the n8n Credentials UI after import. Never paste values into workflow JSON.

| Placeholder name | Used when | Required for default test |
|---|---|---|
| WEBHOOK_AUTH_HEADER | Webhook intake authentication | No. Offline tests skip webhook. |
| WAIT_RESUME_AUTH | Wait On Webhook Call authentication | No. Offline tests simulate review. |
| SLACK_OAUTH | Slack Approvals production swap | No. Not in default JSON. |
| SLACK_SIGNATURE | Slack interactivity verification | No. |
| TEAMS_OAUTH | Teams Send and Wait swap | No. |
| POSTGRES_CONNECTION | Production duplicate and audit store | No. |
| REDIS_CONNECTION | Production key store or queue broker | No. |
| DESTINATION_HTTP | Enabled draft HTTP endpoint | No. Default is Code FakeERP. |
| DOCUMENT_AI_HTTP | Optional OCR or IDP adapter | No. Off in default test. |
| LLM_PROVIDER | Optional Analyze Document or Information Extractor | No. Off in default test. |

Rules:

- Empty placeholder names stay empty until you create the credential.
- Do not commit credential ids from a live instance.
- Slack Signature and Wait resume values are secrets. They are not in this pack.
- Optional OCR and LLM credentials send document bytes to a vendor. Treat that as a processor review, not a default step.
