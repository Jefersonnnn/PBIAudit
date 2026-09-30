# Arquitetura

O PBIAudit é uma aplicação Python com CLI Typer e PostgreSQL. A organização principal está em `src/powerbi_governance/`:

| Camada | Responsabilidade |
| --- | --- |
| `domain/` | Entidades e enumerações de negócio. |
| `application/services/` | Sincronização e regras de auditoria. |
| `infrastructure/` | Clientes Power BI/Graph, autenticação, banco e repositórios. |
| `interfaces/cli/` | Comandos disponíveis ao operador. |
| `interfaces/reports/` | Geração do relatório HTML de licenças. |

## Fluxo de dados

1. A CLI obtém dados do Power BI e Microsoft Graph.
2. Os serviços normalizam os dados e os persistem no PostgreSQL.
3. As métricas são agregadas a partir dos eventos de visualização já salvos.
4. Os relatórios leem o banco local e não solicitam tokens remotos.

As tabelas principais são `workspaces`, `users`, `license_assignments`, `activity_events` e `usage_metrics`.

## Limites

A coleta de eventos é limitada a 28 dias pela Activity Events API. Eventos sem visualização de relatório ou dashboard não são sincronizados.
