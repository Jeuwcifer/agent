#!/bin/bash
set -e

REPO_DIR="$HOME/Repos/agent"

echo "Syncing skills to $REPO_DIR..."

cd "$REPO_DIR"

# Copy skills from ~/.agents/skills
cp -r ~/.agents/skills/* .

# Copy skills from ~/.pi/agent/skills (if needed)
if [ -d "$HOME/.pi/agent/skills" ]; then
    cp -r ~/.pi/agent/skills/* . 2>/dev/null || true
fi

# Check for changes
if [[ -z $(git status -s) ]]; then
    echo "No changes to sync."
    exit 0
fi

# Add, commit, and push
git add .
git commit -m "Auto-sync pi agent skills: $(date)"
git push

echo "Skills successfully pushed to GitHub!"
