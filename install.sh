#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

add_path_if_exists() {
    if [[ -d "$1" && ":$PATH:" != *":$1:"* ]]; then
        export PATH="$1:$PATH"
    fi
}

add_path_if_exists "$HOME/.local/bin"
add_path_if_exists "$HOME/.cargo/bin"

if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv..."
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        echo "Could not find curl or wget to install uv." >&2
        exit 1
    fi
    add_path_if_exists "$HOME/.local/bin"
    add_path_if_exists "$HOME/.cargo/bin"
fi

cd "$project_root"

echo "Installing Python 3.14 if needed..."
uv python install 3.14

echo "Installing Satisfactory Recipes dependencies..."
uv sync

launcher_path="$project_root/run-gui.sh"
cat > "$launcher_path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_root"

uv run sat-rec gui
EOF
chmod +x "$launcher_path"

echo
echo "Install complete."
echo "Launch the GUI with:"
echo "  $launcher_path"
