# Configuração

Copie `.env.example` para `.env` e informe, no mínimo:

```dotenv
DATABASE_URL=postgresql+psycopg2://usuario:senha@host:5432/pbiaudit
AZURE_TENANT_ID=seu-tenant-id
AZURE_CLIENT_ID=seu-client-id
AZURE_CLIENT_SECRET=seu-client-secret
```

O projeto usa PostgreSQL. Execute as migrações após configurar a conexão:

```bash
poetry run alembic upgrade head
```

## Permissões

O service principal precisa de consentimento de administrador para as permissões de aplicativo do Microsoft Graph:

- `User.Read.All`, para ler usuários e planos atribuídos;
- `Organization.Read.All`, para resolver os SKUs e planos do tenant.

Para `sync-workspaces` e `sync-activity-events`, habilite o uso das Power BI Admin APIs pelo service principal em **Power BI Admin portal → Tenant settings**.

## Opções frequentes

| Variável | Padrão | Uso |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | Nível de logs. |
| `LOG_FORMAT` | `json` | Formato `json` ou `text`. |
| `POWERBI_TIMEOUT_SECONDS` | `30` | Tempo máximo de cada chamada ao Power BI. |
| `GRAPH_TIMEOUT_SECONDS` | `30` | Tempo máximo de cada chamada ao Graph. |
| `XMLA_ENDPOINT_ENABLED` | `true` | Ativa a configuração de XMLA. |

Não versione `.env` nem compartilhe o arquivo fora do ambiente autorizado.
