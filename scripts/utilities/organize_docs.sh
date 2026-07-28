#!/bin/bash
# File Organization Script for Miguel CRM Documentation
# This script organizes all markdown files into proper folders

cd /opt/miguel

echo "🔄 Organizing Documentation Files..."

# PHASES - Implementation phases (Phase 1, 4, 5, etc.)
mkdir -p documentation/phases
mv -v PHASE1_*.md documentation/phases/ 2>/dev/null || true
mv -v PHASE4_*.md documentation/phases/ 2>/dev/null || true
mv -v PHASE5_*.md documentation/phases/ 2>/dev/null || true
mv -v README_PHASE1_COMPLETE.md documentation/phases/ 2>/dev/null || true

# FEATURES - Feature implementations (Leads, Labels, GST, Drawer, etc.)
mkdir -p documentation/features
mv -v LEADS_*.md documentation/features/ 2>/dev/null || true
mv -v LABEL_*.md documentation/features/ 2>/dev/null || true
mv -v WABIS_*.md documentation/features/ 2>/dev/null || true
mv -v DRAWER_*.md documentation/features/ 2>/dev/null || true
mv -v GST_*.md documentation/features/ 2>/dev/null || true
mv -v GSTIN_*.md documentation/features/ 2>/dev/null || true
mv -v MODAL_*.md documentation/features/ 2>/dev/null || true
mv -v OPTION*.md documentation/features/ 2>/dev/null || true
mv -v MULTI_BOT_*.md documentation/features/ 2>/dev/null || true
mv -v DESIGN_OPTIONS_ALTERNATIVES.md documentation/features/ 2>/dev/null || true

# REVIEWS - Code reviews and quality assessments
mkdir -p documentation/reviews
mv -v CODE_REVIEW_*.md documentation/reviews/ 2>/dev/null || true
mv -v COMPREHENSIVE_CODE_REVIEW.md documentation/reviews/ 2>/dev/null || true
mv -v PENDING_WORK_ROADMAP.md documentation/reviews/ 2>/dev/null || true
mv -v PROJECT_STATUS_EXECUTIVE_SUMMARY.md documentation/reviews/ 2>/dev/null || true

# GUIDES - Quick start and how-to guides
mkdir -p documentation/guides
mv -v *_QUICK_START.md documentation/guides/ 2>/dev/null || true
mv -v *_USAGE_GUIDE.md documentation/guides/ 2>/dev/null || true
mv -v *_VISUAL_REFERENCE.md documentation/guides/ 2>/dev/null || true
mv -v *_VISUAL_GUIDE.md documentation/guides/ 2>/dev/null || true

# FIXES - Bug fixes and issue resolutions
mkdir -p documentation/fixes
mv -v *_FIX_*.md documentation/fixes/ 2>/dev/null || true
mv -v *_SOLUTION.md documentation/fixes/ 2>/dev/null || true

# MODULES - Module documentation and references
mkdir -p documentation/modules
mv -v *_DOCUMENTATION_INDEX.md documentation/modules/ 2>/dev/null || true
mv -v *_TECHNICAL_REFERENCE.md documentation/modules/ 2>/dev/null || true
mv -v *_FILE_REFERENCE.md documentation/modules/ 2>/dev/null || true
mv -v *_IMPLEMENTATION_*.md documentation/modules/ 2>/dev/null || true

# Keep main README and index files at root
# (Already there or will stay there)

echo ""
echo "✅ File organization complete!"
echo ""
echo "📁 Folder Structure:"
echo "documentation/"
echo "├── phases/          - Phase 1, 4, 5 implementations"
echo "├── features/        - Feature implementations (Leads, GST, WhatsApp)"
echo "├── reviews/         - Code reviews & project status"
echo "├── guides/          - Quick start & how-to guides"
echo "├── fixes/           - Bug fixes & solutions"
echo "└── modules/         - Module reference & documentation"
echo ""
echo "📊 File Count by Folder:"
echo "Phases:   $(ls -1 documentation/phases/*.md 2>/dev/null | wc -l) files"
echo "Features: $(ls -1 documentation/features/*.md 2>/dev/null | wc -l) files"
echo "Reviews:  $(ls -1 documentation/reviews/*.md 2>/dev/null | wc -l) files"
echo "Guides:   $(ls -1 documentation/guides/*.md 2>/dev/null | wc -l) files"
echo "Fixes:    $(ls -1 documentation/fixes/*.md 2>/dev/null | wc -l) files"
echo "Modules:  $(ls -1 documentation/modules/*.md 2>/dev/null | wc -l) files"
echo ""
echo "Total organized: $(find documentation -name "*.md" | wc -l) files"
