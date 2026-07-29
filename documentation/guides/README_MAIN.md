# PureLevenExim CRM - UAT Environment

**Version:** 2.0  
**Status:** ✅ Production Ready (UAT)  
**Last Updated:** February 27, 2026

## Quick Start

### 📖 Documentation
- **Main README:** `docs/root/README.md`
- **Project Index:** `docs/root/ROOT_INDEX.md`
- **Setup Guides:** `documentation/guides/`
- **Feature Documentation:** `documentation/features/`

### 🚀 Quick Setup
```bash
# Navigate to the workspace
cd /opt/miguel

# Review setup guides
cat documentation/guides/FINAL_SETUP_COMPLETE.txt

# Start development environment
docker-compose -f config/docker-compose.yml up -d

# Run tests
bash scripts/utilities/test_api.sh
```

### 🐳 Docker Deployment
```bash
# Development
docker-compose -f config/docker-compose.yml up -d

# Production
docker-compose -f config/docker-compose.prod.yml up -d
```

---

## Project Structure

```
📦 /opt/miguel/
├── 📚 docs/
│   ├── root/                    # Main documentation
│   ├── api/                     # API documentation
│   ├── features/                # Feature guides
│   ├── errors/                  # Error documentation
│   └── ...
├── 📖 documentation/
│   ├── guides/                  # Deployment & setup guides
│   ├── reviews/                 # Reports & summaries
│   └── features/                # Feature documentation
├── 🔧 backend/                  # FastAPI application
├── 🎨 frontend/                 # HTML/CSS/JS frontend
├── 🧪 tests/                    # Test suite
├── ⚙️ config/                   # Configuration files
├── 🛠️ scripts/
│   ├── setup/                   # Setup scripts
│   └── utilities/               # Utility scripts
├── 📦 deploy/                   # Deployment config
├── 🏗️ infra/                    # Infrastructure config
└── 💾 backups/                  # Database backups
```

---

## Key Features

- ✅ **Multi-tenant CRM** with role-based access control
- ✅ **WhatsApp Integration** for automated messaging
- ✅ **Order Management** with real-time status tracking
- ✅ **Lead Management** with pipeline tracking
- ✅ **GST Compliance** reporting
- ✅ **Inventory Management** with stock tracking
- ✅ **Payment Processing** with multiple gateways
- ✅ **Shipping Integration** with Delhivery, India Post
- ✅ **Analytics Dashboard** with KPI tracking

---

## Technology Stack

### Backend
- **Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Authentication:** JWT
- **Async:** AsyncIO, Uvicorn

### Frontend
- **Design:** Material Design 3
- **Architecture:** Modular HTML/CSS/JavaScript
- **Authentication:** JWT-based sessions
- **State Management:** JavaScript modules

### Infrastructure
- **Containerization:** Docker & Docker Compose
- **Web Server:** Nginx
- **Hosting:** Linode
- **CI/CD:** GitHub Actions

---

## Documentation Guide

### For New Developers
1. Start with `docs/root/README.md`
2. Review `documentation/guides/FINAL_SETUP_COMPLETE.txt`
3. Check feature docs in `documentation/features/`

### For DevOps/Infrastructure
1. Review `documentation/guides/LINODE_STRATEGY.md`
2. Check `documentation/guides/PRODUCTION_CHECKLIST.sh`
3. Study infra config in `infra/`

### For Setup & Deployment
1. Follow `documentation/guides/` guides
2. Run scripts from `scripts/setup/`
3. Use configurations from `config/`

### For Troubleshooting
1. Check `docs/errors/` for error guides
2. Review `documentation/reviews/` for status reports
3. Consult feature-specific docs in `documentation/features/`

---

## Environment Variables

Copy the template and configure:
```bash
cp config/.env.example .env
# Edit .env with your configuration
```

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `FRONTEND_URL` - Frontend application URL
- `JWT_SECRET` - JWT signing secret
- `WHATSAPP_API_KEY` - WhatsApp API credentials
- `STRIPE_API_KEY` - Payment gateway credentials

---

## Running the Application

### Development
```bash
# Start services
docker-compose -f config/docker-compose.yml up -d

# Access application
# Frontend: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Production
```bash
# Start services
docker-compose -f config/docker-compose.prod.yml up -d

# Access application
# Frontend: https://your-domain.com
# API: https://api.your-domain.com
```

---

## Testing

Run the test suite:
```bash
# API tests
bash scripts/utilities/test_api.sh

# Sync tests
python scripts/utilities/test_sync.py

# Full test suite
pytest tests/ -v
```

---

## Deployment Checklist

Before deploying to production:
- [ ] Review `documentation/guides/PRODUCTION_CHECKLIST.sh`
- [ ] Verify all environment variables
- [ ] Run test suite
- [ ] Backup database
- [ ] Review deployment guides
- [ ] Test in staging environment
- [ ] Get approval from team lead

---

## Support & Documentation

- 📚 **Full Documentation:** See `documentation/` folder
- 🐛 **Error Guides:** Check `docs/errors/`
- 💡 **Quick Reference:** See `documentation/guides/QUICK_REFERENCE.md`
- 📖 **Feature Docs:** See `documentation/features/`

---

## Project Organization

The workspace was recently reorganized on **February 27, 2026** to improve maintainability:
- 39 files moved from root to appropriate folders
- 5 new organizational directories created
- 95% reduction in root folder clutter

See `PROJECT_ORGANIZATION_SUMMARY.md` for details.

---

## Contact & Support

For issues or questions:
1. Check documentation in `documentation/guides/`
2. Review error guides in `docs/errors/`
3. Contact the development team

---

**Last Updated:** February 27, 2026  
**Workspace:** /opt/miguel  
**Repository:** github.com/purelevenexim-ai/crm
