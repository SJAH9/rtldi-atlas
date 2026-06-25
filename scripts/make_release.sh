#!/bin/bash
set -e

# RTLDI ATLAS Release Helper
# Usage: ./scripts/make_release.sh [version] [message]
# Example: ./scripts/make_release.sh v2026.8 "Refresh public atlas artifacts"

VERSION=${1:-v2026.8}
MESSAGE=${2:-"RTLDI ATLAS ${VERSION} release"}
BRANCH=$(git branch --show-current)

if [ "${BRANCH}" != "main" ]; then
  echo "Release builds must be run from main (current branch: ${BRANCH})."
  exit 1
fi

echo "=== Building latest atlas ==="
python -m src.generate_atlas_ebook

echo "=== Committing release artifacts ==="
git add README.md outputs/atlas/RTLDI_ATLAS_2026_*.pdf
git commit -m "${MESSAGE}" || echo "No new commit (or amend if needed)"

echo "=== Tagging ==="
git tag -a "${VERSION}" -m "${MESSAGE}"

echo "=== Pushing branch and tag ==="
git push origin main --tags

echo ""
echo "=== GitHub Release ==="
echo "Tag ${VERSION} pushed."
echo "Go to https://github.com/SJAH9/rtldi-atlas/releases/new?tag=${VERSION}"
echo "Title: RTLDI ATLAS 2026 ${VERSION}"
echo "Attach: outputs/atlas/RTLDI_ATLAS_2026_ebook.pdf"
echo "Paste release notes (see recent README section for content)."
echo ""
echo "Done. The tag and README update are live; finalize the release page manually or with gh CLI."
