"""Shipping tariff router for file upload and management endpoints."""

from typing import List
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.auth.tenant import get_current_tenant_user
from app.models.employee import Employee
from .service import ShippingTariffService, TariffParseError


router = APIRouter(
    prefix="/api/shipping",
    tags=["shipping"],
)


@router.post("/upload-tariff", status_code=200)
async def upload_tariff(
    file: UploadFile = File(..., description="XLSX tariff file with 'tariff_raw' sheet"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """
    Upload and parse shipping tariff XLSX file.

    Expected XLSX format:
    - Sheet: "tariff_raw"
    - Columns: SKU (required), Shipping Cost (required), Product Name (optional), Courier (optional)
    - Header in row 1, data from row 2 onwards

    Returns:
    {
        "success": bool,
        "message": str,
        "inserted_count": int,
        "errors": [str],  # Validation and parsing errors
        "tariff_records": [  # Preview of inserted records
            {
                "sku_code": str,
                "shipping_cost": float,
                "product_name": str | null,
                "courier": str | null
            }
        ]
    }
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith((".xlsx", ".xls")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be Excel format (.xlsx or .xls)"
            )

        # Read file content
        file_content = await file.read()
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )

        # Parse tariff file
        tariff_records, parse_errors = ShippingTariffService.parse_tariff_xlsx(
            file_content=file_content,
            tenant_id=str(current_user.tenant_id),
            db=db
        )

        # If parsing failed, return errors
        if not tariff_records and parse_errors:
            return {
                "success": False,
                "message": "Failed to parse tariff file",
                "inserted_count": 0,
                "errors": parse_errors,
                "tariff_records": []
            }

        # Upsert records to database
        inserted_count, upsert_errors = ShippingTariffService.upsert_shipping_tariffs(
            tariff_records=tariff_records,
            tenant_id=str(current_user.tenant_id),
            db=db
        )

        backfill_summary = {
            "orders_scanned": 0,
            "orders_with_sku_match": 0,
            "orders_updated": 0,
            "orders_without_sku_match": 0,
            "returned_orders_with_rto_added": 0,
            "profit_postings_refreshed": 0,
            "posting_refresh_errors": 0,
        }
        if inserted_count > 0 and not upsert_errors:
            try:
                backfill_summary = ShippingTariffService.backfill_order_shipping_from_tariffs(
                    tenant_id=str(current_user.tenant_id),
                    db=db,
                )
            except Exception as backfill_error:
                upsert_errors.append(f"Order shipping backfill failed: {str(backfill_error)}")

        # Prepare response
        response = {
            "success": len(upsert_errors) == 0,
            "message": f"Successfully uploaded {inserted_count} tariff records",
            "inserted_count": inserted_count,
            "errors": parse_errors + upsert_errors,
            "order_shipping_backfill": backfill_summary,
            "tariff_records": [
                {
                    "sku_code": r["sku_code"],
                    "shipping_cost": float(r["shipping_cost"]),
                    "product_name": r.get("product_name"),
                    "courier": r.get("courier"),
                }
                for r in tariff_records[:50]  # Return first 50 records as preview
            ]
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing tariff file: {str(e)}"
        )


@router.post("/backfill-order-shipping")
async def backfill_order_shipping(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """Manually recompute order shipping_charge from current tariff SKUs."""
    try:
        summary = ShippingTariffService.backfill_order_shipping_from_tariffs(
            tenant_id=str(current_user.tenant_id),
            db=db,
        )
        return {
            "success": True,
            "message": "Order shipping backfill completed",
            **summary,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running shipping backfill: {str(e)}",
        )


@router.get("/tariffs")
async def list_tariffs(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """
    List all shipping tariffs for the current tenant (paginated).

    Returns:
    {
        "tariffs": [
            {
                "id": str,
                "sku_code": str,
                "shipping_cost": float,
                "rto_handling_charge": float,
                "product_name": str | null,
                "file_uploaded_at": str (ISO format),
                "created_at": str (ISO format)
            }
        ],
        "total": int,
        "limit": int,
        "offset": int
    }
    """
    try:
        tariffs, total = ShippingTariffService.get_all_tariffs(
            tenant_id=str(current_user.tenant_id),
            db=db,
            limit=limit,
            offset=offset
        )

        return {
            "tariffs": [
                {
                    "id": str(t.id),
                    "sku_code": t.sku_code,
                    "shipping_cost": float(t.shipping_cost),
                    "rto_handling_charge": float(t.rto_handling_charge),
                    "product_id": str(t.product_id) if t.product_id else None,
                    "file_uploaded_at": t.file_uploaded_at.isoformat() if t.file_uploaded_at else None,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tariffs
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tariffs: {str(e)}"
        )


@router.get("/tariff/{sku}")
async def get_tariff_by_sku(
    sku: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_tenant_user),
):
    """
    Get shipping tariff by SKU code.

    Returns:
    {
        "sku_code": str,
        "shipping_cost": float,
        "rto_handling_charge": float,
        "product_id": str | null,
        "file_uploaded_at": str (ISO format)
    }
    """
    try:
        shipping_cost = ShippingTariffService.get_shipping_cost_by_sku(
            sku=sku,
            tenant_id=str(current_user.tenant_id),
            db=db
        )

        if shipping_cost == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tariff not found for SKU: {sku}"
            )

        return {
            "sku_code": sku,
            "shipping_cost": float(shipping_cost),
            "rto_handling_charge": 50.0,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tariff: {str(e)}"
        )
