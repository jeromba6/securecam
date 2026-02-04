#!/bin/sh
# yq is required to parse the pr_checks.yml file
# Install yq:
#   sudo apt install -y yq

# Check if yq is installed as /usr/bin/yq or /usr/local/bin/yq
if [ ! -x /usr/bin/yq ] && [ ! -x /usr/local/bin/yq ]
then
    echo "yq could not be found, please install it to run this script."
    echo "On Debian/Ubuntu, you can install it with: sudo apt install -y yq"
    exit 1
fi

# Extract Superlinter environment variables from the GitHub Actions workflow file
yq -r '.jobs.lint.steps[] | select(.name == "Run Superlinter").env | del(.GITHUB_TOKEN) | to_entries | .[] | "" + .key + "=" + (.value | @sh)' .github/workflows/pr_checks.yml > superlint_local.env

# check for -f flag to force fixes
if [ "$1" = "-f" ]; then
    echo "Enabling automatic fixes..."
    # Set all FIX_* variables to true
    # only change lines that start with FIX_ to avoid changing other variables
    sed -i '/^FIX_/s/=false/=true/' superlint_local.env
else
    sed -i '/^FIX_/s/=true/=false/' superlint_local.env
    echo "Running without automatic fixes..."
fi

# Run superlint locally
docker run --rm \
  --env-file superlint_local.env \
  -e RUN_LOCAL=true \
  -e VALIDATE_GIT_COMMITLINT=false \
  -v "$(pwd):/tmp/lint" \
  ghcr.io/super-linter/super-linter:latest | tee superlint_local.log