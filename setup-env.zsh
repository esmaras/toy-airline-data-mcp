#!/usr/bin/env zsh
# setup-env.zsh — Bootstrap the Python virtual environment for this project.
# Run once after cloning: source setup-env.zsh
# (Use `source` so the venv stays active in your current shell)

PROJECT_DIR="$(cd "$(dirname "${(%):-%x}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

echo "==> Project root: $PROJECT_DIR"

# 1. Create venv if it doesn't exist
if [[ ! -d "$VENV_DIR" ]]; then
  echo "==> Creating virtual environment at venv/ ..."
  python3 -m venv "$VENV_DIR"
else
  echo "==> Virtual environment already exists at venv/"
fi

# 2. Activate
source "$VENV_DIR/bin/activate"
echo "==> Activated: $(which python)"

# 3. Upgrade pip silently
pip install --upgrade pip --quiet

# 4. Install dependencies
echo "==> Installing dependencies from requirements.txt ..."
pip install -r "$PROJECT_DIR/requirements.txt"

# 5. One-time DuckDB delta extension install (cached after first run)
echo "==> Installing DuckDB delta extension (cached after first run) ..."
python - <<'EOF'
import duckdb
con = duckdb.connect()
con.execute("INSTALL delta")
con.execute("LOAD delta")
print("    DuckDB delta extension ready.")
con.close()
EOF

# 6. Verify core imports
echo "==> Verifying imports ..."
python - <<'EOF'
import deltalake, duckdb, fastapi, mcp, pandas, pyarrow
print("    All core packages imported successfully.")
EOF

# 7. Load AWS credentials if .env.dev exists
ENV_FILE="$PROJECT_DIR/.env.dev"
if [[ -f "$ENV_FILE" ]]; then
  echo "==> Loading AWS credentials from .env.dev ..."
  set -o allexport
  source "$ENV_FILE"
  set +o allexport
  echo "    AWS credentials loaded (region: $AWS_DEFAULT_REGION)"
else
  echo "==> Skipping AWS credentials (.env.dev not found)"
  echo "    Copy .env.example to .env.dev and fill in your credentials to enable AWS targets."
fi

echo ""
echo "✓ Environment ready. Your shell is now using venv/"
echo "  To activate later in a new shell:"
echo "    source setup-env.zsh"
echo ""
echo "  Next step — run a dry-run to enumerate your XLSX sheets:"
echo "    python -m ingestion.ingest --dry-run"
