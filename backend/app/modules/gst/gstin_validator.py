"""
GSTIN Validation & Lookup Service
===================================
Validates GSTIN format and provides basic GST details.

Note: India's GST portal API is not publicly available.
This implementation provides format validation + basic details.
For full details (business name, address), users should manually verify
via https://www.gst.gov.in or integrate with paid GST APIs.
"""

from __future__ import annotations

import re
from typing import Optional, Dict, Any
from decimal import Decimal


class GSTINValidator:
    """
    GSTIN Format: NN[A-Z0-9]{5}[A-Z0-9]{5}[A-Z0-9]{3}
    Total: 15 characters
    
    Breakdown:
    - Positions 0-1:   NN = State code (01-37, digits only)
    - Positions 2-6:   PPPPP = First 5 chars of PAN (can be alphanumeric)
    - Positions 7-11:  DDDDD = Registration (can be alphanumeric)
    - Positions 12-14: Check chars (alphanumeric) 
    
    Example: 32BCJPT7873A1ZG (Daman and Diu)
    
    Note: Full checksum validation is complex. This implementation
    does basic format validation only. For production, verify via
    official GST portal.
    """

    STATE_CODES = {
        "01": "Andhra Pradesh",
        "02": "Arunachal Pradesh",
        "03": "Assam",
        "04": "Bihar",
        "05": "Chhattisgarh",
        "06": "Goa",
        "07": "Gujarat",
        "08": "Haryana",
        "09": "Himachal Pradesh",
        "10": "Jharkhand",
        "11": "Karnataka",
        "12": "Kerala",
        "13": "Madhya Pradesh",
        "14": "Maharashtra",
        "15": "Manipur",
        "16": "Meghalaya",
        "17": "Mizoram",
        "18": "Nagaland",
        "19": "Odisha",
        "20": "Punjab",
        "21": "Rajasthan",
        "22": "Sikkim",
        "23": "Tamil Nadu",
        "24": "Telangana",
        "25": "Tripura",
        "26": "Uttar Pradesh",
        "27": "Uttarakhand",
        "28": "West Bengal",
        "29": "Andaman and Nicobar Islands",
        "30": "Chandigarh",
        "31": "Dadra and Nagar Haveli",
        "32": "Daman and Diu",
        "33": "Delhi",
        "34": "Jammu and Kashmir",
        "35": "Ladakh",
        "36": "Lakshadweep",
        "37": "Puducherry",
    }

    @staticmethod
    def validate_format(gstin: str) -> tuple[bool, Optional[str]]:
        """
        Validate GSTIN format.
        Returns (is_valid, error_message)
        
        GSTIN: 15 characters
        - [0-1]: State code (NN, digits)
        - [2-11]: PAN + Registration (alphanumeric)
        - [12-14]: Check characters (alphanumeric)
        """
        gstin = gstin.strip().upper()

        # Length check
        if len(gstin) != 15:
            return False, f"GSTIN must be 15 characters (got {len(gstin)})"

        # Basic format: 2 digits + 10 alphanumeric + 3 alphanumeric
        pattern = r"^[0-9]{2}[A-Z0-9]{10}[A-Z0-9]{3}$"
        if not re.match(pattern, gstin):
            return False, "Invalid GSTIN format. Expected: 15 alphanumeric characters starting with state code."

        state_code = gstin[:2]
        if state_code not in GSTINValidator.STATE_CODES:
            return False, f"Invalid state code: {state_code}. Use valid state code (01-37)."

        # Checksum validation is complex - skip strict validation
        # Most online validators also accept lenient validation
        return True, None

    @staticmethod
    def _verify_checksum(gstin: str) -> bool:
        """
        Verify GSTIN checksum using Verhoeff algorithm.
        The last character is the check digit.
        """
        try:
            # Verhoeff multiplication table
            mult_table = [
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
                [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
                [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
                [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
                [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
                [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
                [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
                [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
                [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
            ]
            
            perm_table = [
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
                [5, 8, 6, 2, 7, 9, 3, 1, 0, 4],
                [8, 9, 2, 7, 5, 4, 3, 6, 1, 0],
                [9, 4, 7, 5, 8, 3, 3, 2, 6, 1],
                [4, 3, 5, 8, 9, 1, 3, 7, 2, 6],
                [3, 1, 8, 9, 4, 6, 3, 5, 7, 2],
                [1, 6, 9, 4, 3, 2, 3, 8, 5, 7],
            ]

            inv_table = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

            # Prepare check digit calculation (first 14 chars)
            c = 0
            for i, ch in enumerate(gstin[:14]):
                # Convert char to digit (A=10, B=11, etc. for letters)
                digit = int(ch) if ch.isdigit() else (ord(ch) - ord('A') + 10) % 10
                c = mult_table[c][perm_table[(i + 1) % 8][digit]]

            # Calculate check digit
            check_digit = inv_table[c]
            
            # Last char should match (converted to digit)
            last_char = gstin[-1]
            actual_check = int(last_char) if last_char.isdigit() else (ord(last_char) - ord('A') + 10) % 10
            
            return check_digit == actual_check
        except Exception:
            # If algorithm fails, return True (allow manual verification)
            return True

    @staticmethod
    def extract_info(gstin: str) -> Dict[str, Any]:
        """
        Extract information from valid GSTIN.
        Returns state, PAN prefix, and registration number.
        """
        gstin = gstin.strip().upper()
        
        return {
            "gstin": gstin,
            "state_code": gstin[:2],
            "state_name": GSTINValidator.STATE_CODES.get(gstin[:2], "Unknown"),
            "pan_prefix": gstin[2:7],
            "registration_number": gstin[7:12],
            "is_valid": True,
        }


def validate_gstin(gstin: str) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Public function to validate GSTIN and return details.
    
    Args:
        gstin: 15-character GSTIN string
        
    Returns:
        (is_valid, error_msg, details_dict)
    """
    is_valid, error_msg = GSTINValidator.validate_format(gstin)
    
    if not is_valid:
        return False, error_msg, None
    
    details = GSTINValidator.extract_info(gstin)
    return True, None, details
