PYTHON := venv/bin/python
PIP    := venv/bin/pip
PYTEST := venv/bin/pytest
UVICORN := venv/bin/uvicorn

SHARING_HOST := 0.0.0.0
SHARING_PORT := 8080
MCP_PORT     := 8081

# AWS / Docker — set AWS_ACCOUNT_ID and AWS_REGION before running deploy targets
AWS_REGION     ?= us-east-1
AWS_ACCOUNT_ID ?= $(shell aws sts get-caller-identity --query Account --output text 2>/dev/null)
ECR_BASE       := $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
IMAGE_TAG      ?= latest

# ──────────────────────────────────────────────────────────────────────────────
# Help (default target)
# ──────────────────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "Southwest Toy Airline Data — available commands:"
	@echo ""
	@echo "  Setup"
	@echo "    make setup           Bootstrap venv and install all dependencies"
	@echo ""
	@echo "  Ingestion"
	@echo "    make dry-run         Enumerate XLSX sheets without writing Delta tables"
	@echo "    make ingest          Convert all XLSX → Delta tables in delta_tables/"
	@echo ""
	@echo "  Servers (both must run together)"
	@echo "    make sharing-server  Start the Delta Sharing REST server (port $(SHARING_PORT)) — terminal 1"
	@echo "    make mcp-server      Start the MCP server via stdio (for Claude Desktop) — terminal 2"
	@echo "    make mcp-server-sse  Start the MCP server via SSE HTTP (port $(MCP_PORT)) — terminal 2"
	@echo ""
	@echo "  Inspection"
	@echo "    make list-tables     List all Delta tables in delta_tables/"
	@echo "    make inspect-lounge  Preview lounge an sheet columns (before unpivot)"
	@echo "    make test            Run all tests"
	@echo ""
	@echo "  AWS Deploy"
	@echo "    Prereq: copy .env.example to .env.dev, fill in credentials, then"
	@echo "            run 'source setup-aws.zsh' in your shell before using these."
	@echo "    make deploy          Full deploy: build all images, push, tf-apply, update ECS"
	@echo "    make deploy-web      Build + push web app image only, then update ECS service"
	@echo "    make deploy-backend  Build + push sharing/mcp images only, then update ECS"
	@echo "    make ssm-put-key     Store Anthropic API key in SSM (prompts for value)"
	@echo "    make sync-tables     Upload local delta_tables/ to S3 data lake"
	@echo "    make tf-init         terraform init (run once per workspace)"
	@echo "    make tf-plan         terraform plan"
	@echo "    make tf-apply        terraform apply"
	@echo "    make logs-web        Tail web app CloudWatch logs"
	@echo "    make logs-sharing    Tail sharing server CloudWatch logs"
	@echo "    make url             Print the deployed web app URL"
	@echo ""

# ──────────────────────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────────────────────
.PHONY: setup
setup:
	@echo "==> Creating virtual environment..."
	python3 -m venv venv
	$(PIP) install --upgrade pip --quiet
	@echo "==> Installing dependencies..."
	$(PIP) install -r requirements.txt
	@echo "==> Installing DuckDB delta extension..."
	$(PYTHON) -c "import duckdb; c = duckdb.connect(); c.execute('INSTALL delta'); c.execute('LOAD delta'); print('    DuckDB delta extension ready.')"
	@echo "==> Verifying imports..."
	$(PYTHON) -c "import deltalake, duckdb, fastapi, mcp, pandas, pyarrow; print('    All core packages OK.')"
	@echo ""
	@echo "✓ Setup complete. Run 'make dry-run' to inspect your XLSX files."

# ──────────────────────────────────────────────────────────────────────────────
# Ingestion
# ──────────────────────────────────────────────────────────────────────────────
.PHONY: dry-run
dry-run:
	$(PYTHON) -m ingestion.ingest --dry-run

.PHONY: ingest
ingest:
	$(PYTHON) -m ingestion.ingest

# ──────────────────────────────────────────────────────────────────────────────
# Servers
# ──────────────────────────────────────────────────────────────────────────────
.PHONY: sharing-server
sharing-server:
	$(UVICORN) sharing.server:app \
		--host $(SHARING_HOST) \
		--port $(SHARING_PORT) \
		--reload

.PHONY: mcp-server
mcp-server:
	$(PYTHON) -m mcp_server.server --transport stdio

.PHONY: mcp-server-sse
mcp-server-sse:
	$(PYTHON) -m mcp_server.server --transport sse --port $(MCP_PORT)

# ──────────────────────────────────────────────────────────────────────────────
# Inspection
# ──────────────────────────────────────────────────────────────────────────────
.PHONY: list-tables
list-tables:
	$(PYTHON) -c "from mcp_server.tools.list_tables import run; print(run())"

.PHONY: inspect-lounge
inspect-lounge:
	$(PYTHON) -m ingestion.inspect

# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────
.PHONY: test
test:
	$(PYTEST) tests/ -v

# ──────────────────────────────────────────────────────────────────────────────
# AWS Deploy
# ──────────────────────────────────────────────────────────────────────────────
ENV ?= dev
TF_DIR := infra

.PHONY: ecr-login
ecr-login:
	aws ecr get-login-password --region $(AWS_REGION) | \
		docker login --username AWS --password-stdin $(ECR_BASE)

.PHONY: build-images
build-images:
	docker build --platform linux/amd64 -f docker/Dockerfile.sharing -t clearpath-sharing-server:$(IMAGE_TAG) .
	docker build --platform linux/amd64 -f docker/Dockerfile.mcp     -t clearpath-mcp-server:$(IMAGE_TAG) .

# Usage: make push-images ENV=dev
.PHONY: push-images
push-images: ecr-login
	$(eval SHARING_REPO := $(ECR_BASE)/clearpath-$(ENV)/sharing-server)
	$(eval MCP_REPO     := $(ECR_BASE)/clearpath-$(ENV)/mcp-server)
	docker tag clearpath-sharing-server:$(IMAGE_TAG) $(SHARING_REPO):$(IMAGE_TAG)
	docker tag clearpath-mcp-server:$(IMAGE_TAG)     $(MCP_REPO):$(IMAGE_TAG)
	docker push $(SHARING_REPO):$(IMAGE_TAG)
	docker push $(MCP_REPO):$(IMAGE_TAG)
	@echo ""
	@echo "Images pushed:"
	@echo "  $(SHARING_REPO):$(IMAGE_TAG)"
	@echo "  $(MCP_REPO):$(IMAGE_TAG)"

# Usage: make sync-tables ENV=dev BUCKET=clearpath-dev-data-lake
.PHONY: sync-tables
sync-tables:
	@test -n "$(BUCKET)" || (echo "ERROR: set BUCKET=<your-s3-bucket-name>"; exit 1)
	aws s3 sync delta_tables/ s3://$(BUCKET)/delta/southwest_airline/ \
		--exclude "*.DS_Store" \
		--delete
	@echo "Delta tables synced to s3://$(BUCKET)/delta/southwest_airline/"

.PHONY: build-web
build-web:
	docker build --platform linux/amd64 -f docker/Dockerfile.web -t clearpath-web-app:$(IMAGE_TAG) .

.PHONY: push-web
push-web: ecr-login
	$(eval WEB_REPO := $(ECR_BASE)/clearpath-$(ENV)/web-app)
	docker tag clearpath-web-app:$(IMAGE_TAG) $(WEB_REPO):$(IMAGE_TAG)
	docker push $(WEB_REPO):$(IMAGE_TAG)
	@echo "Web app pushed: $(WEB_REPO):$(IMAGE_TAG)"

.PHONY: tf-init
tf-init:
	cd $(TF_DIR) && terraform init

.PHONY: tf-plan
tf-plan:
	cd $(TF_DIR) && terraform plan

.PHONY: tf-apply
tf-apply:
	cd $(TF_DIR) && terraform apply

# ── Composite deploy targets ──────────────────────────────────────────────────

# Store Anthropic API key in SSM (run once)
.PHONY: ssm-put-key
ssm-put-key:
	@read -s -p "Anthropic API key: " KEY && echo && \
	aws ssm put-parameter \
		--name "/clearpath/$(ENV)/anthropic_api_key" \
		--value "$$KEY" \
		--type SecureString \
		--region $(AWS_REGION) \
		--overwrite && \
	echo "Key stored at /clearpath/$(ENV)/anthropic_api_key"

# Build + push web app, then force ECS to redeploy it
.PHONY: deploy-web
deploy-web: build-web push-web
	aws ecs update-service \
		--cluster clearpath-$(ENV)-cluster \
		--service clearpath-$(ENV)-web-app \
		--force-new-deployment \
		--region $(AWS_REGION) \
		--query 'service.serviceName' --output text
	@echo "Web app deploying — run 'make logs-web' to watch"

# Build + push backend images, then force ECS to redeploy them
.PHONY: deploy-backend
deploy-backend: build-images push-images
	aws ecs update-service \
		--cluster clearpath-$(ENV)-cluster \
		--service clearpath-$(ENV)-sharing-server \
		--force-new-deployment \
		--region $(AWS_REGION) \
		--query 'service.serviceName' --output text
	aws ecs update-service \
		--cluster clearpath-$(ENV)-cluster \
		--service clearpath-$(ENV)-mcp-server \
		--force-new-deployment \
		--region $(AWS_REGION) \
		--query 'service.serviceName' --output text
	@echo "Backend deploying — run 'make logs-sharing' to watch"

# Full deploy: build everything, push, apply terraform, update all ECS services
.PHONY: deploy
deploy: build-images build-web push-images push-web tf-apply
	aws ecs update-service \
		--cluster clearpath-$(ENV)-cluster \
		--service clearpath-$(ENV)-sharing-server \
		--force-new-deployment \
		--region $(AWS_REGION) \
		--query 'service.serviceName' --output text
	aws ecs update-service \
		--cluster clearpath-$(ENV)-cluster \
		--service clearpath-$(ENV)-mcp-server \
		--force-new-deployment \
		--region $(AWS_REGION) \
		--query 'service.serviceName' --output text
	aws ecs update-service \
		--cluster clearpath-$(ENV)-cluster \
		--service clearpath-$(ENV)-web-app \
		--force-new-deployment \
		--region $(AWS_REGION) \
		--query 'service.serviceName' --output text
	@echo ""
	@$(MAKE) url

# ── Observability ─────────────────────────────────────────────────────────────

.PHONY: logs-web
logs-web:
	aws logs tail /ecs/clearpath-$(ENV)-web-app \
		--follow --region $(AWS_REGION)

.PHONY: logs-sharing
logs-sharing:
	aws logs tail /ecs/clearpath-$(ENV)-sharing-server \
		--follow --region $(AWS_REGION)

.PHONY: logs-mcp
logs-mcp:
	aws logs tail /ecs/clearpath-$(ENV)-mcp-server \
		--follow --region $(AWS_REGION)

.PHONY: url
url:
	@terraform -chdir=$(TF_DIR) output -raw web_app_url 2>/dev/null || \
		echo "Run 'make tf-apply' first to get the URL"
