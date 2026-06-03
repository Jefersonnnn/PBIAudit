# API Reference (Future)

## Overview

This document outlines the planned REST API endpoints for the Power BI Governance platform.

**Current Status:** Planning phase - FastAPI implementation pending

**Note:** The API layer is currently interfaced through CLI (Typer). REST API endpoints will be added in Phase 2.

## Authentication

All endpoints will require Bearer token authentication:

```bash
Authorization: Bearer <access_token>
```

Tokens are obtained through:
1. Service Principal flow (server-to-server)
2. User token delegation (user context)

## Workspaces Endpoints

### List Workspaces

```
GET /api/v1/workspaces
```

**Query Parameters:**
- `skip` (int, default=0) - Number of workspaces to skip
- `top` (int, default=100) - Number of workspaces to return
- `filter` (string) - Filter expression

**Response:**
```json
{
    "total": 45,
    "skip": 0,
    "top": 100,
    "value": [
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "workspace_id": "f6d4541a-30d5-4251-9bc0-a9a2f7e8c5c6",
            "name": "Sales Analytics",
            "is_premium": true,
            "state": "ACTIVE",
            "created_at": "2024-01-15T10:00:00Z"
        }
    ]
}
```

### Get Workspace Details

```
GET /api/v1/workspaces/{workspace_id}
```

### Get Workspace Datasets

```
GET /api/v1/workspaces/{workspace_id}/datasets
```

### Get Workspace Reports

```
GET /api/v1/workspaces/{workspace_id}/reports
```

### Get Workspace Users

```
GET /api/v1/workspaces/{workspace_id}/users
```

## Datasets Endpoints

### List Datasets

```
GET /api/v1/datasets
```

### Get Dataset Details

```
GET /api/v1/datasets/{dataset_id}
```

### Get Dataset Refresh History

```
GET /api/v1/datasets/{dataset_id}/refreshes
```

## Reports Endpoints

### List Reports

```
GET /api/v1/reports
```

### Get Report Details

```
GET /api/v1/reports/{report_id}
```

## Users Endpoints

### List Users

```
GET /api/v1/users
```

### Get Inactive Users

```
GET /api/v1/users/inactive?days=30
```

## Usage Metrics Endpoints

### Get Usage Metrics

```
GET /api/v1/usage-metrics
```

**Query Parameters:**
- `report_id` (string) - Filter by report
- `workspace_id` (string) - Filter by workspace
- `start_date` (date) - Start date (YYYY-MM-DD)
- `end_date` (date) - End date (YYYY-MM-DD)

## Activity Events Endpoints

### Get Activity Events

```
GET /api/v1/activity-events
```

**Query Parameters:**
- `user_id` (string) - Filter by user
- `activity` (string) - Filter by activity type
- `start_time` (datetime) - Start time
- `end_time` (datetime) - End time

## Admin Endpoints

### Sync Workspaces

```
POST /api/v1/admin/sync/workspaces
```

**Response:**
```json
{
    "status": "completed",
    "workspaces_synced": 45,
    "duration_seconds": 12.5
}
```

### Sync Usage Metrics

```
POST /api/v1/admin/sync/usage-metrics
```

### Sync Activity Events

```
POST /api/v1/admin/sync/activity-events
```

**Body:**
```json
{
    "days_back": 7
}
```

### Health Check

```
GET /api/v1/admin/health
```

## Error Responses

All errors follow this format:

```json
{
    "error_code": "WORKSPACE_NOT_FOUND",
    "message": "Workspace with ID 'xyz' not found",
    "details": {
        "workspace_id": "xyz"
    }
}
```

### HTTP Status Codes

- `200 OK` - Successful request
- `201 Created` - Resource created
- `400 Bad Request` - Invalid parameters
- `401 Unauthorized` - Missing/invalid authentication
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Rate Limiting

Endpoints will implement rate limiting:

- **Default:** 1000 requests per hour per user
- **Burst:** 100 requests per minute

Response headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1234567890
```

## Pagination

Endpoints returning collections use cursor-based pagination:

```
GET /api/v1/workspaces?skip=0&top=100
```

Returns:
```json
{
    "total": 450,
    "skip": 0,
    "top": 100,
    "hasMore": true,
    "value": [...]
}
```

## Implementation Timeline

**Phase 2:**
- [ ] Core REST API framework (FastAPI)
- [ ] Authentication middleware
- [ ] Workspace endpoints
- [ ] Dataset endpoints

**Phase 3:**
- [ ] Report endpoints
- [ ] User endpoints
- [ ] Usage metrics endpoints
- [ ] Activity events endpoints
- [ ] Admin endpoints

## See Also

- [Architecture Guide](ARCHITECTURE.md)
- [CLI Reference](CLI.md)
- [Configuration Guide](CONFIG.md)
