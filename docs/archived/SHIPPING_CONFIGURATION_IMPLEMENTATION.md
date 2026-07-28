# Shipping Configuration Dashboard — Implementation Guide

**Date:** Feb 24, 2026  
**Status:** Ready for Development  
**Complexity:** Medium (4-5 weeks)

---

## 📋 Complete Implementation Roadmap

This document provides step-by-step instructions for building the **multi-tenant shipping configuration dashboard**.

---

## PHASE 1: Backend Setup (Week 1)

### Step 1.1: Create Database Models

**File:** `/opt/miguel/backend/app/models/shipping_config.py`

```python
from sqlalchemy import Column, String, Boolean, JSON, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.core.database import Base
from uuid import uuid4
from datetime import datetime
from decimal import Decimal

# =============== SHOPIFY STORES ===============

class ShopifyStore(Base):
    __tablename__ = "shopify_stores"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    # Identity
    store_name = Column(String(255), nullable=False)
    store_url = Column(String(255), unique=True, nullable=False)
    is_primary = Column(Boolean, default=False)
    
    # Credentials (encrypted in database)
    api_access_token = Column(String(500), nullable=False)
    api_client_id = Column(String(255), nullable=False)
    api_client_secret = Column(String(500), nullable=False)
    
    # Configuration
    api_version = Column(String(50), default="2024-01")
    webhook_secret = Column(String(500), nullable=True)
    webhook_topics = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)
    last_connection_test = Column(DateTime, nullable=True)
    last_sync = Column(DateTime, nullable=True)
    
    # Metadata
    custom_fields = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="shopify_stores")


# =============== DELIVERY PARTNERS ===============

class DeliveryPartner(Base):
    __tablename__ = "delivery_partners"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    # Identity
    partner_name = Column(String(255), nullable=False)
    partner_type = Column(String(50), nullable=False)  # delhivery, bluedart, dtdc, etc
    display_name = Column(String(255), nullable=False)
    
    # Credentials (encrypted)
    api_key = Column(String(500), nullable=False)
    api_secret = Column(String(500), nullable=True)
    client_name = Column(String(255), nullable=True)
    client_id = Column(String(255), nullable=True)
    
    # API Configuration
    api_base_url = Column(String(255), nullable=False)
    api_version = Column(String(50), nullable=True)
    
    # Provider-Specific
    pickup_location_code = Column(String(100), nullable=True)
    warehouse_name = Column(String(255), nullable=True)
    warehouse_address = Column(String(500), nullable=True)
    warehouse_phone = Column(String(20), nullable=True)
    
    # Shipment Types
    supported_shipment_types = Column(JSON, nullable=True)
    default_shipment_type = Column(String(50), default="surface")
    
    # Coverage
    coverage_areas = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    is_connected = Column(Boolean, default=False)
    last_connection_test = Column(DateTime, nullable=True)
    
    # Pricing
    base_charge = Column(Numeric(10, 2), nullable=True)
    weight_rate_per_kg = Column(Numeric(10, 2), nullable=True)
    
    # Metadata
    custom_fields = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="delivery_partners")


# =============== NOTIFICATION CHANNELS ===============

class NotificationChannel(Base):
    __tablename__ = "notification_channels"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    # Channel Type
    channel_type = Column(String(50), nullable=False)  # whatsapp, sms, email
    provider = Column(String(50), nullable=False)  # meta, twilio, sendgrid
    
    # Credentials (encrypted)
    api_key = Column(String(500), nullable=False)
    api_secret = Column(String(500), nullable=True)
    access_token = Column(String(500), nullable=True)
    
    # Channel Settings
    phone_number = Column(String(20), nullable=True)
    business_account_id = Column(String(255), nullable=True)
    phone_number_id = Column(String(255), nullable=True)
    sender_email = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    is_connected = Column(Boolean, default=False)
    last_connection_test = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="notification_channels")


# =============== BUSINESS RULES ===============

class ShippingBusinessRules(Base):
    __tablename__ = "shipping_business_rules"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, unique=True)
    
    # Order Value Controls
    max_order_value = Column(Numeric(15, 2), default=50000)
    max_cod_amount = Column(Numeric(15, 2), default=10000)
    
    # RTO Controls
    high_rto_threshold = Column(Numeric(5, 2), default=15.0)
    medium_rto_threshold = Column(Numeric(5, 2), default=8.0)
    
    # Customer Scoring
    auto_blacklist_rto_count = Column(String, default="5")
    auto_blacklist_ndr_count = Column(String, default="5")
    auto_blacklist_fraud_score = Column(Numeric(5, 2), default=80.0)
    blacklist_duration_days = Column(String, nullable=True)
    
    # COD Management
    require_cod_confirmation = Column(Boolean, default=True)
    cod_confirmation_timeout_minutes = Column(String, default="30")
    auto_create_reattempt_on_ndr = Column(Boolean, default=False)
    max_ndr_reattempts = Column(String, default="2")
    
    # Shipment Creation
    auto_create_on_order_created = Column(Boolean, default=True)
    auto_create_on_payment_confirmed = Column(Boolean, default=False)
    require_manual_approval = Column(Boolean, default=False)
    
    # Tracking
    tracking_sync_interval_minutes = Column(String, default="15")
    
    # Notifications
    send_delivery_confirmation = Column(Boolean, default=True)
    send_rto_alerts = Column(Boolean, default=True)
    send_ndr_alerts = Column(Boolean, default=True)
    notify_via_whatsapp = Column(Boolean, default=True)
    notify_via_sms = Column(Boolean, default=False)
    notify_via_email = Column(Boolean, default=False)
    
    # Admin Alerts
    admin_alert_on_rto = Column(Boolean, default=True)
    admin_alert_on_ndr = Column(Boolean, default=True)
    admin_alert_on_high_value_order = Column(Boolean, default=True)
    admin_emails = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="shipping_business_rules")
```

### Step 1.2: Create Pydantic Schemas

**File:** `/opt/miguel/backend/app/modules/shipping_config/schemas.py`

```python
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# =============== SHOPIFY STORE SCHEMAS ===============

class ShopifyStoreCreate(BaseModel):
    store_name: str
    store_url: str
    api_access_token: str
    api_client_id: str
    api_client_secret: str
    is_primary: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "store_name": "Main Store",
                "store_url": "pureleven.myshopify.com",
                "api_access_token": "shpat_...",
                "api_client_id": "0704646c...",
                "api_client_secret": "shpss_...",
                "is_primary": True
            }
        }

class ShopifyStoreUpdate(BaseModel):
    store_name: Optional[str] = None
    is_primary: Optional[bool] = None
    api_access_token: Optional[str] = None
    is_active: Optional[bool] = None

class ShopifyStoreResponse(BaseModel):
    id: str
    store_name: str
    store_url: str
    is_primary: bool
    is_active: bool
    is_connected: bool
    last_sync: Optional[datetime]
    last_connection_test: Optional[datetime]
    
    class Config:
        from_attributes = True


# =============== DELIVERY PARTNER SCHEMAS ===============

class DeliveryPartnerCreate(BaseModel):
    partner_type: str  # delhivery, bluedart, dtdc, india_post, amazon
    display_name: str
    api_key: str
    api_secret: Optional[str] = None
    client_name: Optional[str] = None
    pickup_location_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    is_primary: bool = False

class DeliveryPartnerUpdate(BaseModel):
    display_name: Optional[str] = None
    api_key: Optional[str] = None
    pickup_location_code: Optional[str] = None
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None

class DeliveryPartnerResponse(BaseModel):
    id: str
    partner_type: str
    display_name: str
    is_primary: bool
    is_active: bool
    is_connected: bool
    supported_shipment_types: Optional[List[str]]
    last_connection_test: Optional[datetime]
    
    class Config:
        from_attributes = True


# =============== NOTIFICATION CHANNEL SCHEMAS ===============

class NotificationChannelCreate(BaseModel):
    channel_type: str  # whatsapp, sms, email
    provider: str  # meta, twilio, sendgrid
    api_key: str
    api_secret: Optional[str] = None
    phone_number: Optional[str] = None
    business_account_id: Optional[str] = None
    phone_number_id: Optional[str] = None
    sender_email: Optional[str] = None
    is_primary: bool = False

class NotificationChannelResponse(BaseModel):
    id: str
    channel_type: str
    provider: str
    is_active: bool
    is_connected: bool
    phone_number: Optional[str] = None
    sender_email: Optional[str] = None
    
    class Config:
        from_attributes = True


# =============== BUSINESS RULES SCHEMAS ===============

class ShippingBusinessRulesUpdate(BaseModel):
    max_order_value: Optional[Decimal] = None
    max_cod_amount: Optional[Decimal] = None
    high_rto_threshold: Optional[Decimal] = None
    medium_rto_threshold: Optional[Decimal] = None
    require_cod_confirmation: Optional[bool] = None
    cod_confirmation_timeout_minutes: Optional[str] = None
    auto_create_on_order_created: Optional[bool] = None
    send_delivery_confirmation: Optional[bool] = None
    notify_via_whatsapp: Optional[bool] = None
    admin_emails: Optional[List[str]] = None

class ShippingBusinessRulesResponse(BaseModel):
    max_order_value: Decimal
    max_cod_amount: Decimal
    require_cod_confirmation: bool
    auto_create_on_order_created: bool
    send_delivery_confirmation: bool
    notify_via_whatsapp: bool
    
    class Config:
        from_attributes = True
```

### Step 1.3: Create FastAPI Routes

**File:** `/opt/miguel/backend/app/modules/shipping_config/router.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.shipping_config import (
    ShopifyStore, DeliveryPartner, NotificationChannel, ShippingBusinessRules
)
from . import schemas, service
from app.models.employee import Employee

router = APIRouter(prefix="/api/config", tags=["shipping-config"])

# =============== VERIFY TENANT ADMIN ===============

async def verify_tenant_admin(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Employee:
    """Only tenant admins can access configuration"""
    if current_user.role not in ["tenant_admin", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only tenant admins can configure shipping"
        )
    return current_user


# =============== SHOPIFY STORES ===============

@router.get("/shopify-stores")
async def list_shopify_stores(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(verify_tenant_admin)
):
    """List all Shopify stores for tenant"""
    stores = db.query(ShopifyStore).filter(
        ShopifyStore.tenant_id == current_user.tenant_id
    ).all()
    
    return [schemas.ShopifyStoreResponse.from_orm(s) for s in stores]


@router.post("/shopify-stores")
async def create_shopify_store(
    store: schemas.ShopifyStoreCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(verify_tenant_admin)
):
    """Create new Shopify store configuration"""
    # Check if URL already exists
    existing = db.query(ShopifyStore).filter(
        ShopifyStore.store_url == store.store_url
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Store URL already configured"
        )
    
    # Encrypt credentials before saving
    encrypted_token = service.encrypt_credential(store.api_access_token)
    encrypted_secret = service.encrypt_credential(store.api_client_secret)
    
    new_store = ShopifyStore(
        tenant_id=current_user.tenant_id,
        store_name=store.store_name,
        store_url=store.store_url,
        api_access_token=encrypted_token,
        api_client_id=store.api_client_id,
        api_client_secret=encrypted_secret,
        is_primary=store.is_primary
    )
    
    db.add(new_store)
    db.commit()
    db.refresh(new_store)
    
    return schemas.ShopifyStoreResponse.from_orm(new_store)


@router.post("/shopify-stores/{store_id}/test-connection")
async def test_shopify_connection(
    store_id: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(verify_tenant_admin)
):
    """Test Shopify API connection"""
    store = db.query(ShopifyStore).filter(
        ShopifyStore.id == store_id,
        ShopifyStore.tenant_id == current_user.tenant_id
    ).first()
    
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    # Test connection
    try:
        result = await service.test_shopify_connection(store)
        store.is_connected = result["success"]
        store.last_connection_test = datetime.utcnow()
        db.commit()
        
        return {
            "status": "connected" if result["success"] else "failed",
            "message": result["message"]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# =============== DELIVERY PARTNERS ===============

@router.get("/delivery-partners/available")
async def list_available_partners():
    """List supported delivery partner types"""
    return [
        {"id": "delhivery", "name": "Delhivery", "logo": "delhivery.png"},
        {"id": "bluedart", "name": "Blue Dart", "logo": "bluedart.png"},
        {"id": "dtdc", "name": "DTDC", "logo": "dtdc.png"},
        {"id": "india_post", "name": "India Post", "logo": "india_post.png"},
        {"id": "amazon", "name": "Amazon Logistics", "logo": "amazon.png"},
    ]


@router.get("/delivery-partners")
async def list_delivery_partners(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(verify_tenant_admin)
):
    """List configured delivery partners for tenant"""
    partners = db.query(DeliveryPartner).filter(
        DeliveryPartner.tenant_id == current_user.tenant_id
    ).all()
    
    return [schemas.DeliveryPartnerResponse.from_orm(p) for p in partners]


@router.post("/delivery-partners")
async def create_delivery_partner(
    partner: schemas.DeliveryPartnerCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(verify_tenant_admin)
):
    """Add new delivery partner"""
    # Get partner config from available partners
    partner_config = service.get_partner_config(partner.partner_type)
    
    new_partner = DeliveryPartner(
        tenant_id=current_user.tenant_id,
        partner_name=partner.partner_type,
        partner_type=partner.partner_type,
        display_name=partner.display_name,
        api_key=service.encrypt_credential(partner.api_key),
        api_secret=service.encrypt_credential(partner.api_secret) if partner.api_secret else None,
        client_name=partner.client_name,
        api_base_url=partner_config["base_url"],
        pickup_location_code=partner.pickup_location_code,
        warehouse_name=partner.warehouse_name,
        supported_shipment_types=partner_config.get("shipment_types", ["surface"]),
        is_primary=partner.is_primary
    )
    
    db.add(new_partner)
    db.commit()
    db.refresh(new_partner)
    
    return schemas.DeliveryPartnerResponse.from_orm(new_partner)


@router.post("/delivery-partners/{partner_id}/test-connection")
async def test_delivery_partner_connection(
    partner_id: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(verify_tenant_admin)
):
    """Test delivery partner API connection"""
    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.id == partner_id,
        DeliveryPartner.tenant_id == current_user.tenant_id
    ).first()
    
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    try:
        result = await service.test_delivery_partner_connection(partner)
        partner.is_connected = result["success"]
        partner.last_connection_test = datetime.utcnow()
        db.commit()
        
        return {
            "status": "connected" if result["success"] else "failed",
            "message": result["message"]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# =============== BUSINESS RULES ===============

@router.get("/business-rules")
async def get_business_rules(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(verify_tenant_admin)
):
    """Get business rules for tenant"""
    rules = db.query(ShippingBusinessRules).filter(
        ShippingBusinessRules.tenant_id == current_user.tenant_id
    ).first()
    
    if not rules:
        # Create default rules
        rules = ShippingBusinessRules(tenant_id=current_user.tenant_id)
        db.add(rules)
        db.commit()
        db.refresh(rules)
    
    return schemas.ShippingBusinessRulesResponse.from_orm(rules)


@router.put("/business-rules")
async def update_business_rules(
    rules_update: schemas.ShippingBusinessRulesUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(verify_tenant_admin)
):
    """Update business rules for tenant"""
    rules = db.query(ShippingBusinessRules).filter(
        ShippingBusinessRules.tenant_id == current_user.tenant_id
    ).first()
    
    if not rules:
        rules = ShippingBusinessRules(tenant_id=current_user.tenant_id)
        db.add(rules)
    
    # Update fields
    update_data = rules_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rules, field, value)
    
    db.commit()
    db.refresh(rules)
    
    return schemas.ShippingBusinessRulesResponse.from_orm(rules)
```

---

## PHASE 2: Frontend Dashboard (Week 2)

### Step 2.1: React Component Structure

**File:** `/opt/miguel/frontend/components/ShippingConfig/ShippingConfigDashboard.jsx`

```jsx
import React, { useState, useEffect } from 'react';
import { Tabs, TabList, TabPanel, Tab } from '@reach/tabs';
import ShopifyStoresTab from './tabs/ShopifyStoresTab';
import DeliveryPartnersTab from './tabs/DeliveryPartnersTab';
import NotificationsTab from './tabs/NotificationsTab';
import BusinessRulesTab from './tabs/BusinessRulesTab';
import '@reach/tabs/styles.css';
import './ShippingConfig.css';

export default function ShippingConfigDashboard() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <div className="shipping-config-container">
      <div className="config-header">
        <h1>🚚 Shipping Configuration</h1>
        <p>Manage Shopify stores, delivery partners, and shipping rules</p>
      </div>

      <Tabs index={activeTab} onChange={setActiveTab}>
        <TabList>
          <Tab>🛒 Shopify Stores</Tab>
          <Tab>🚚 Delivery Partners</Tab>
          <Tab>💬 Notifications</Tab>
          <Tab>⚙️ Business Rules</Tab>
        </TabList>

        <TabPanel>
          <ShopifyStoresTab />
        </TabPanel>

        <TabPanel>
          <DeliveryPartnersTab />
        </TabPanel>

        <TabPanel>
          <NotificationsTab />
        </TabPanel>

        <TabPanel>
          <BusinessRulesTab />
        </TabPanel>
      </Tabs>
    </div>
  );
}
```

**File:** `/opt/miguel/frontend/components/ShippingConfig/tabs/ShopifyStoresTab.jsx`

```jsx
import React, { useState, useEffect } from 'react';
import { api } from '../../../services/api';
import ShopifyStoreForm from '../forms/ShopifyStoreForm';
import ShopifyStoreList from '../lists/ShopifyStoreList';
import './Tab.css';

export default function ShopifyStoresTab() {
  const [stores, setStores] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStores();
  }, []);

  const fetchStores = async () => {
    try {
      const response = await api.get('/api/config/shopify-stores');
      setStores(response.data);
    } catch (error) {
      console.error('Failed to fetch stores:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStoreCreated = () => {
    fetchStores();
    setShowForm(false);
  };

  if (loading) return <div className="loading">Loading stores...</div>;

  return (
    <div className="tab-content">
      <div className="tab-header">
        <h2>Shopify Stores</h2>
        <button 
          className="btn btn-primary"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? '✕ Cancel' : '+ Add New Store'}
        </button>
      </div>

      {showForm && (
        <ShopifyStoreForm onSuccess={handleStoreCreated} />
      )}

      <ShopifyStoreList stores={stores} onRefresh={fetchStores} />
    </div>
  );
}
```

**File:** `/opt/miguel/frontend/components/ShippingConfig/forms/ShopifyStoreForm.jsx`

```jsx
import React, { useState } from 'react';
import { api } from '../../../services/api';
import './Form.css';

export default function ShopifyStoreForm({ onSuccess }) {
  const [formData, setFormData] = useState({
    store_name: '',
    store_url: '',
    api_access_token: '',
    api_client_id: '',
    api_client_secret: '',
    is_primary: false
  });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await api.post('/api/config/shopify-stores', formData);
      setFormData({
        store_name: '', store_url: '', api_access_token: '',
        api_client_id: '', api_client_secret: '', is_primary: false
      });
      onSuccess();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create store');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="config-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label>Store Name</label>
        <input
          type="text"
          name="store_name"
          value={formData.store_name}
          onChange={handleChange}
          placeholder="e.g., Pure Leven Main"
          required
        />
      </div>

      <div className="form-group">
        <label>Store URL</label>
        <input
          type="text"
          name="store_url"
          value={formData.store_url}
          onChange={handleChange}
          placeholder="e.g., purelevenexim.myshopify.com"
          required
        />
      </div>

      <div className="form-group">
        <label>API Access Token</label>
        <input
          type="password"
          name="api_access_token"
          value={formData.api_access_token}
          onChange={handleChange}
          placeholder="shpat_..."
          required
        />
      </div>

      <div className="form-group">
        <label>Client ID</label>
        <input
          type="text"
          name="api_client_id"
          value={formData.api_client_id}
          onChange={handleChange}
          required
        />
      </div>

      <div className="form-group">
        <label>Client Secret</label>
        <input
          type="password"
          name="api_client_secret"
          value={formData.api_client_secret}
          onChange={handleChange}
          placeholder="shpss_..."
          required
        />
      </div>

      <div className="form-group checkbox">
        <input
          type="checkbox"
          name="is_primary"
          id="is_primary"
          checked={formData.is_primary}
          onChange={handleChange}
        />
        <label htmlFor="is_primary">Set as primary store</label>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="form-actions">
        <button type="submit" disabled={loading} className="btn btn-primary">
          {loading ? 'Saving...' : 'Save Store'}
        </button>
      </div>
    </form>
  );
}
```

---

## PHASE 3-4: Testing & Deployment

### Step 3.1: Database Migration

**File:** `/opt/miguel/backend/alembic/versions/003_add_shipping_config_tables.py`

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create shopify_stores table
    op.create_table(
        'shopify_stores',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('store_name', sa.String(255), nullable=False),
        sa.Column('store_url', sa.String(255), nullable=False),
        sa.Column('is_primary', sa.Boolean(), default=False),
        sa.Column('api_access_token', sa.String(500), nullable=False),
        sa.Column('api_client_id', sa.String(255), nullable=False),
        sa.Column('api_client_secret', sa.String(500), nullable=False),
        sa.Column('api_version', sa.String(50), default='2024-01'),
        sa.Column('webhook_secret', sa.String(500)),
        sa.Column('webhook_topics', sa.JSON()),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_connected', sa.Boolean(), default=False),
        sa.Column('last_connection_test', sa.DateTime()),
        sa.Column('last_sync', sa.DateTime()),
        sa.Column('custom_fields', sa.JSON()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('store_url')
    )

    # Similar for other tables...

def downgrade():
    op.drop_table('shopify_stores')
    op.drop_table('delivery_partners')
    op.drop_table('notification_channels')
    op.drop_table('shipping_business_rules')
```

---

## 📋 Complete Checklist

### Backend
- [ ] Create models (shopify_stores, delivery_partners, notification_channels, shipping_business_rules)
- [ ] Create schemas (Pydantic models)
- [ ] Create routes (6+ endpoints)
- [ ] Create service layer (encryption, API testing)
- [ ] Create database migration
- [ ] Add access control (tenant_admin only)
- [ ] Write unit tests

### Frontend
- [ ] Create main dashboard component
- [ ] Create 4 tab components
- [ ] Create forms (ShopifyStoreForm, DeliveryPartnerForm, etc.)
- [ ] Create lists/tables
- [ ] Add test connection buttons
- [ ] Add error handling
- [ ] Style with CSS

### Testing
- [ ] Test Shopify connection
- [ ] Test delivery partner connection
- [ ] Test credential encryption/decryption
- [ ] Test multi-tenant isolation
- [ ] Test form validation
- [ ] End-to-end testing

### Documentation
- [ ] API documentation
- [ ] User guide for admins
- [ ] Troubleshooting guide

---

## 🚀 Benefits

✅ **Multi-tenant:** Each tenant manages own integrations  
✅ **Secure:** Encrypted credentials  
✅ **Scalable:** Easy to add new partners  
✅ **User-friendly:** Visual dashboard  
✅ **Flexible:** No hardcoding, all configurable  

Ready to build? 🔥

