#!/bin/bash

# Script to organize scattered files in the main folder
# This will move files into appropriate directories based on their type and purpose

echo "🔧 Starting file organization process..."

# Create necessary directories if they don't exist
mkdir -p docs/root
mkdir -p documentation/guides
mkdir -p scripts/setup
mkdir -p scripts/utilities
mkdir -p config
mkdir -p .environment

# 1. Move README and main documentation to docs/root
echo "📋 Moving README and main documentation..."
mv -v README.md docs/root/ 2>/dev/null || echo "README.md already in place"
mv -v ROOT_INDEX.md docs/root/ 2>/dev/null || echo "ROOT_INDEX.md already in place"
mv -v FINAL_CHECKLIST.md docs/root/ 2>/dev/null || echo "FINAL_CHECKLIST.md already in place"

# 2. Move deployment and setup guides to documentation/guides
echo "📦 Moving deployment and setup guides..."
mv -v DEPLOYMENT_COMPLETE_AND_VERIFIED.md documentation/guides/ 2>/dev/null
mv -v DEPLOYMENT_TEST_SUMMARY.md documentation/guides/ 2>/dev/null
mv -v DEPLOYMENT_VERIFICATION_REPORT.md documentation/guides/ 2>/dev/null
mv -v FINAL_SETUP_COMPLETE.txt documentation/guides/ 2>/dev/null
mv -v GITHUB_SETUP_SUMMARY.txt documentation/guides/ 2>/dev/null
mv -v PRODUCTION_CHECKLIST.sh documentation/guides/ 2>/dev/null
mv -v STEP_BY_STEP_PAY_STATUS_TEST.md documentation/guides/ 2>/dev/null
mv -v LINODE_STRATEGY.md documentation/guides/ 2>/dev/null
mv -v SHOPIFY_DELHIVERY_NEXT_STEPS.txt documentation/guides/ 2>/dev/null
mv -v MEMORY_UPDATE_PRODUCTION_NETWORK.md documentation/guides/ 2>/dev/null

# 3. Move feature guides to documentation/guides
echo "📚 Moving feature guides..."
mv -v INDIA_POST_XLSX_UPLOAD_GUIDE.md documentation/guides/ 2>/dev/null
mv -v MANUAL_ORDERS_INDIA_POST_XLSX_GUIDE.md documentation/guides/ 2>/dev/null

# 4. Move reference documents to documentation/guides
echo "📖 Moving reference documents..."
mv -v QUICK_REFERENCE.md documentation/guides/ 2>/dev/null
mv -v QUICK_REFERENCE_2026_02_25.md documentation/guides/ 2>/dev/null
mv -v FIXES_QUICK_REFERENCE.md documentation/guides/ 2>/dev/null

# 5. Move summaries and reports to documentation/reviews
mkdir -p documentation/reviews
echo "📊 Moving summaries and reports..."
mv -v CHANGES_SUMMARY_2026_02_26.md documentation/reviews/ 2>/dev/null
mv -v CLEANUP_REPORT.md documentation/reviews/ 2>/dev/null
mv -v CODEBASE_STRUCTURE.md documentation/reviews/ 2>/dev/null
mv -v DELETION_SYSTEM_COMPLETE.md documentation/reviews/ 2>/dev/null
mv -v IMPLEMENTATION_SUMMARY.txt documentation/reviews/ 2>/dev/null
mv -v IMPLEMENTATION_VERIFICATION.txt documentation/reviews/ 2>/dev/null
mv -v ISSUES_FIXED_SUMMARY.md documentation/reviews/ 2>/dev/null
mv -v PAY_STATUS_FIX_SUMMARY.txt documentation/reviews/ 2>/dev/null
mv -v SESSION_SUMMARY_2026_02_25.md documentation/reviews/ 2>/dev/null
mv -v FILES_MANIFEST.md documentation/reviews/ 2>/dev/null
mv -v DOCUMENTATION_UPDATES_2026_02_25.md documentation/reviews/ 2>/dev/null
mv -v DOCUMENTATION_INDEX.md documentation/reviews/ 2>/dev/null
mv -v DOCUMENTATION_INDEX_PAY_STATUS.md documentation/reviews/ 2>/dev/null
mv -v REMAINING_TASKS.md documentation/reviews/ 2>/dev/null

# 6. Move utility scripts to scripts/utilities
echo "🛠️  Moving utility scripts..."
mv -v organize_docs.sh scripts/utilities/ 2>/dev/null
mv -v ORGANIZE_FILES.sh scripts/utilities/ 2>/dev/null
mv -v organize_main_folder.sh scripts/utilities/ 2>/dev/null
mv -v test_api.sh scripts/utilities/ 2>/dev/null
mv -v test_sync.py scripts/utilities/ 2>/dev/null
mv -v link_order_customer.py scripts/utilities/ 2>/dev/null

# 7. Move configuration files to config
echo "⚙️  Moving configuration files..."
mv -v docker-compose.yml config/ 2>/dev/null
mv -v docker-compose.prod.yml config/ 2>/dev/null
mv -v .env.example config/ 2>/dev/null

# 8. Move setup scripts to scripts/setup
echo "🚀 Moving setup scripts..."
mv -v scripts/complete-prod-setup.sh scripts/setup/ 2>/dev/null
mv -v scripts/complete-remaining-steps.sh scripts/setup/ 2>/dev/null

echo ""
echo "✅ File organization complete!"
echo ""
echo "📁 Folder structure:"
echo "   docs/root/              - Main README and root documentation"
echo "   documentation/guides/   - Setup and deployment guides"
echo "   documentation/reviews/  - Summaries, reports and status files"
echo "   documentation/features/ - Feature-specific documentation"
echo "   scripts/utilities/      - Utility scripts"
echo "   scripts/setup/          - Setup and configuration scripts"
echo "   config/                 - Configuration files"
echo "   backend/                - Backend code"
echo "   frontend/               - Frontend code"
echo "   tests/                  - Test files"
echo "   infra/                  - Infrastructure configuration"
echo "   deploy/                 - Deployment configuration"
echo ""
