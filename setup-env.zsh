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

echo ""
echo "✓ Environment ready. Your shell is now using venv/"
echo "  To activate later in a new shell:"
echo "    source venv/bin/activate"
echo ""
echo "  Next step — run a dry-run to enumerate your XLSX sheets:"
echo "    python -m ingestion.ingest --dry-run"
