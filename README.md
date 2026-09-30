# PBIAudit

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Poetry](https://img.shields.io/badge/Poetry-enabled-green.svg)

Ferramenta de linha de comando para inventariar workspaces, coletar uso de relatórios e auditar licenças Power BI Pro a partir das APIs do Power BI e Microsoft Graph.

> Projeto em beta. Revise os resultados antes de tomar decisões sobre licenças ou acesso.

## Recursos

- Sincroniza workspaces, licenças e eventos de visualização.
- Calcula visualizações e usuários únicos por relatório e dia.
- Identifica licenças Pro ativas, ociosas e sem atividade registrada localmente.
- Gera relatórios por usuário, departamento e HTML.

## Requisitos

- Python 3.12+
- [Poetry](https://python-poetry.org/)
- PostgreSQL
- Service principal do Microsoft Entra ID com acesso às APIs do Power BI e Microsoft Graph

Para a auditoria de licenças, conceda consentimento de administrador para `User.Read.All` e `Organization.Read.All` no Microsoft Graph. Para eventos de atividade, habilite o uso das Power BI Admin APIs pelo service principal nas configurações do tenant.

## Instalação

```bash
git clone https://github.com/Jefersonnnn/PBIAudit.git
cd PBIAudit
poetry install
cp .env.example .env
```

Edite `.env` com os valores do seu ambiente:

```dotenv
DATABASE_URL=postgresql+psycopg2://usuario:senha@host:5432/pbiaudit
AZURE_TENANT_ID=seu-tenant-id
AZURE_CLIENT_ID=seu-client-id
AZURE_CLIENT_SECRET=seu-client-secret
```

Crie as tabelas e confira os comandos disponíveis:

```bash
poetry run alembic upgrade head
poetry run pbi-governance --help
```

## Uso rápido

Execute as sincronizações antes de gerar relatórios:

```bash
poetry run pbi-governance sync-workspaces
poetry run pbi-governance sync-licenses
poetry run pbi-governance sync-activity-events 7
poetry run pbi-governance sync-usage-metrics
```

Depois, consulte ou exporte a auditoria:

```bash
poetry run pbi-governance license-report --inactive-days 30
poetry run pbi-governance department-report --inactive-days 30
poetry run pbi-governance export-report --output relatorio.html
```

| Comando | Finalidade |
| --- | --- |
| `sync-workspaces` | Atualiza o inventário de workspaces. |
| `sync-licenses` | Atualiza o snapshot de licenças Power BI Pro. |
| `sync-activity-events [dias]` | Coleta `ViewReport` e `ViewDashboard` dos últimos 1 a 28 dias. |
| `sync-usage-metrics` | Agrega visualizações diárias a partir dos eventos locais. |
| `license-report` | Exibe o uso por titular de licença. |
| `department-report` | Resume o uso por departamento. |
| `export-report` | Gera um relatório HTML independente. |
| `init-gerencias` | Cria um modelo de `gerencias.csv` para nomear as gerências no HTML. |

Os comandos de relatório e `sync-usage-metrics` usam apenas os dados já gravados no banco.

## Limitações importantes

- A Activity Events API mantém até 28 dias de histórico e exige consultas por dia UTC.
- A ausência de eventos locais significa **sem atividade registrada**; ela não comprova que a licença nunca foi usada.
- A auditoria de licenças considera apenas Power BI Pro.
- Os totais de visualização podem diferir das métricas exibidas pelo próprio Power BI.

## Desenvolvimento

```bash
poetry run pytest
poetry run ruff check .
poetry run mypy src
```

Consulte [CONTRIBUTING.md](CONTRIBUTING.md) antes de enviar uma alteração.

## Segurança

Não versione `.env`, tokens, senhas, exports de relatórios ou dados de auditoria. Use credenciais próprias para cada ambiente e restrinja o acesso ao banco de dados.

## Licença

O projeto é distribuído sob a licença MIT.
