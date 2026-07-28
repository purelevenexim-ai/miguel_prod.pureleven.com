#!/bin/bash

# Create organized folder structure
mkdir -p docs/setup
mkdir -p docs/deployment
mkdir -p docs/api
mkdir -p docs/features
mkdir -p docs/troubleshooting

# Move setup documentation
mv PRODUCTION_SETUP*.md docs/setup/ 2>/dev/null
mv COMPLETE_SETUP*.md docs/setup/ 2>/dev/null
mv FINAL_SETUP*.md docs/setup/ 2>/dev/null
mv SETUP_COMPLETE.md docs/setup/ 2>/dev/null
mv SSH_SETUP*.md docs/setup/ 2>/dev/null
mv GITHUB_SECRETS*.md docs/setup/ 2>/dev/null
mv GITHUB_SETUP*.md docs/setup/ 2>/dev/null

# Move deployment documentation
mv DEPLOYMENT*.md docs/deployment/ 2>/dev/null
mv DEPLOYMENT*.txt docs/deployment/ 2>/dev/null
mv PRODUCTION_DEPLOYMENT*.md docs/deployment/ 2>/dev/null

# Move API documentation
mv API_QUICK*.md docs/api/ 2>/dev/null

# Move feature documentation
mv *FEATURE*.md docs/features/ 2>/dev/null
mv *EDIT*.md docs/features/ 2>/dev/null
mv SHOPIFY*.md docs/features/ 2>/dev/null
mv PARTIAL_COD*.md docs/features/ 2>/dev/null
mv PAYMENT*.md docs/features/ 2>/dev/null
mv ORDER*.md docs/features/ 2>/dev/null
mv *SYNC*.md docs/features/ 2>/dev/null
mv *LOGISTICS*.md docs/features/ 2>/dev/null

# Move troubleshooting docs
mv *DEBUGGING*.md docs/troubleshooting/ 2>/dev/null
mv *FIX*.md docs/troubleshooting/ 2>/dev/null
mv *TROUBLESHOOTING*.md docs/troubleshooting/ 2>/dev/null
mv ISSUE*.md docs/troubleshooting/ 2>/dev/null

echo "✅ Files organized successfully!"
ls -la docs/
