# ClearPath — AWS Architecture

## Network Boundary

**VPC** (`10.0.0.0/16`, `us-east-1`)
- 2 **public subnets** (AZ1 + AZ2) — ALB lives here
- 2 **private subnets** (AZ1 + AZ2) — all ECS tasks live here
- **Internet Gateway** — public subnets → internet
- **NAT Gateway** (single, AZ1) — private subnets → internet (outbound only, e.g. Anthropic API)
- **S3 VPC Gateway Endpoint** — private subnets → S3 without touching NAT (free, no data transfer cost)

---

## Public Layer

**ALB** (public subnets, internet-facing)
- Port 80, idle timeout 3600s
- Listener rule priority 10: `/sse`, `/messages` → MCP target group
- Default action: `/*` → Web app target group
- Security group: inbound 80/443 from `0.0.0.0/0`, outbound to ECS task SGs

---

## Compute Layer (private subnets, ECS Fargate, `clearpath-dev-cluster`)

**Web App** (512 CPU / 1024 MB)
- Next.js on port 3000
- Registered with ALB target group
- Env: `SHARING_SERVER_URL=http://sharing-server.clearpath-dev.local:8080`
- Secret: `ANTHROPIC_API_KEY` injected from SSM at startup
- Outbound: → Sharing Server (port 8080, internal) + → Anthropic API (port 443, via NAT)
- Security group: inbound 3000 from ALB SG only

**MCP Server** (512 CPU / 1024 MB)
- Python MCP server (SSE transport) on port 8081
- Registered with ALB target group
- Env: `SHARING_SERVER_URL=http://sharing-server.clearpath-dev.local:8080`
- Outbound: → Sharing Server (port 8080, internal)
- Security group: inbound 8081 from ALB SG only

**Sharing Server** (512 CPU / 1024 MB)
- FastAPI on port 8080
- **NOT registered with ALB** — internal only
- Env: `DELTA_TABLES_S3_PREFIX=s3://clearpath-dev-data-lake/delta/southwest_airline`
- Outbound: → S3 (via VPC Gateway Endpoint, no NAT)
- Security group: inbound 8080 from Web App SG + MCP Server SG only

---

## Service Discovery

**AWS Cloud Map** (`clearpath-dev.local` private DNS namespace)
- `sharing-server.clearpath-dev.local` → Sharing Server ECS task private IP
- Used by both Web App and MCP Server to find the Sharing Server

---

## Storage

**S3 Bucket** (`clearpath-dev-data-lake`)
- `delta/southwest_airline/schedules/` — 8 Delta tables
- `delta/southwest_airline/aircraft/` — 5 Delta tables
- `delta/southwest_airline/fares/` — 5 Delta tables
- `raw/xlsx/` — source XLSX files

**ECR** (3 repos)
- `clearpath-dev/sharing-server`
- `clearpath-dev/mcp-server`
- `clearpath-dev/web-app`

---

## Secrets & Config

**SSM Parameter Store**
- `/clearpath/dev/anthropic_api_key` (SecureString) — fetched by ECS execution role at task startup, injected as env var into Web App container

---

## IAM Roles

| Role | Who uses it | Permissions |
|------|-------------|-------------|
| `ecs-execution-role` | ECS agent (all tasks) | Pull ECR images, write CloudWatch logs, read SSM secrets |
| `sharing-task-role` | Sharing Server task | S3 `GetObject` + `ListBucket` on data lake bucket |
| `mcp-task-role` | MCP Server task | None (only makes HTTP calls) |
| `web-task-role` | Web App task | None (only makes HTTP calls + outbound HTTPS) |

---

## Request Flow (chat message)

```
User browser
  │  HTTP POST /api/chat
  ▼
ALB  →  Web App (Next.js, private subnet)
          │  1. Calls Anthropic API (claude-sonnet) with tool definitions
          │     ← via NAT Gateway → internet
          │
          │  2. Claude returns tool_use (e.g. list_tables)
          │
          │  3. POST http://sharing-server.clearpath-dev.local:8080/tools/list_tables
          ▼
        Sharing Server (FastAPI, private subnet)
          │  Runs DuckDB → fetches parquet from S3
          ▼
        S3 (via VPC Gateway Endpoint)
          │  Returns data
          ▼
        Sharing Server → returns result string
          │
          ▼
        Web App → sends tool_result back to Claude
          │
          │  4. Claude returns end_turn text response (streamed)
          │
          │  5. SSE stream of text deltas back to browser
          ▼
User browser (text appears token by token)
```

---

## Observability

**CloudWatch Log Groups**
- `/ecs/clearpath-dev-web-app`
- `/ecs/clearpath-dev-sharing-server`
- `/ecs/clearpath-dev-mcp-server`
- Retention: 14 days

**ECS Container Insights** — enabled on the cluster (CPU, memory, task counts)
