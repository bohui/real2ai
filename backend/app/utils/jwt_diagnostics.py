"""
JWT Token Diagnostics Utility
Provides detailed timing analysis for JWT token issues
"""

import json
import base64
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import time

logger = logging.getLogger(__name__)


def decode_jwt_payload_detailed(token: str) -> Dict[str, Any]:
    """Decode JWT payload with detailed timing analysis"""
    try:
        # Capture current time immediately
        current_time = datetime.now(timezone.utc)
        current_timestamp = int(current_time.timestamp())
        decode_time = time.time()
        
        # JWT has 3 parts: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return {"error": "Invalid JWT format", "parts_count": len(parts)}
        
        # Decode payload (add padding if needed)
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding
            
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8'))
        
        result = {
            "token_length": len(token),
            "decode_timestamp": decode_time,
            "current_time_iso": current_time.isoformat(),
            "current_timestamp": current_timestamp,
            "payload": payload,  # Full payload for analysis
        }
        
        # Detailed expiration analysis
        if 'exp' in payload:
            exp_dt = datetime.fromtimestamp(payload['exp'], timezone.utc)
            result.update({
                "expires_at_iso": exp_dt.isoformat(),
                "expires_timestamp": payload['exp'],
                "expires_in_seconds": payload['exp'] - current_timestamp,
                "is_expired": payload['exp'] < current_timestamp,
                "expiry_margin_ms": (payload['exp'] - current_timestamp) * 1000,
            })
            
        # Issued at analysis
        if 'iat' in payload:
            iat_dt = datetime.fromtimestamp(payload['iat'], timezone.utc)
            result.update({
                "issued_at_iso": iat_dt.isoformat(),
                "issued_timestamp": payload['iat'],
                "token_age_seconds": current_timestamp - payload['iat'],
            })
            
        # Clock skew analysis
        if 'iat' in payload and 'exp' in payload:
            token_lifetime = payload['exp'] - payload['iat']
            clock_skew = payload['iat'] - current_timestamp
            
            result.update({
                "token_lifetime_seconds": token_lifetime,
                "token_lifetime_hours": token_lifetime / 3600,
                "clock_skew_seconds": clock_skew,
                "clock_skew_ms": clock_skew * 1000,
                "has_clock_skew": abs(clock_skew) > 5,  # More than 5 seconds
            })
        
        # Token identity
        if 'sub' in payload:
            result["subject"] = payload['sub']
        if 'aud' in payload:
            result["audience"] = payload['aud']
        if 'iss' in payload:
            result["issuer"] = payload['iss']
            
        return result
        
    except Exception as e:
        return {
            "error": f"Failed to decode JWT: {e}",
            "token_length": len(token) if token else 0,
            "exception_type": type(e).__name__
        }


def log_jwt_timing_issue(token: str, operation: str, error: Optional[Exception] = None):
    """Log detailed JWT timing analysis for debugging"""
    try:
        analysis = decode_jwt_payload_detailed(token)
        
        log_data = {
            "operation": operation,
            "jwt_analysis": analysis,
            "system_time": datetime.now(timezone.utc).isoformat(),
            "error": str(error) if error else None,
        }
        
        # Determine severity
        if analysis.get("has_clock_skew"):
            severity = "CRITICAL"
        elif analysis.get("is_expired"):
            severity = "ERROR"
        elif analysis.get("expiry_margin_ms", 0) < 30000:  # Less than 30 seconds
            severity = "WARNING"
        else:
            severity = "INFO"
            
        logger.warning(
            f"JWT_TIMING_{severity}: {operation} - "
            f"Expires in {analysis.get('expires_in_seconds', 'unknown')}s, "
            f"Clock skew: {analysis.get('clock_skew_seconds', 'unknown')}s, "
            f"Token age: {analysis.get('token_age_seconds', 'unknown')}s"
        )
        
        # Log full details for debugging
        logger.debug(f"JWT_TIMING_DETAILS: {json.dumps(log_data, indent=2)}")
        
        return analysis
        
    except Exception as e:
        logger.error(f"JWT_TIMING_ANALYSIS_FAILED: {e}")
        return {"error": str(e)}


def check_system_time_sync():
    """Check if system time appears to be synchronized"""
    try:
        import subprocess
        import platform
        
        system_info = {
            "platform": platform.system(),
            "current_time": datetime.now(timezone.utc).isoformat(),
            "timestamp": time.time(),
        }
        
        # Try to get NTP status on Linux
        if platform.system() == "Linux":
            try:
                result = subprocess.run(['timedatectl', 'status'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    system_info["ntp_status"] = result.stdout
            except (subprocess.TimeoutExpired, FileNotFoundError):
                system_info["ntp_status"] = "timedatectl not available"
        
        logger.info(f"SYSTEM_TIME_INFO: {json.dumps(system_info, indent=2)}")
        return system_info
        
    except Exception as e:
        logger.error(f"SYSTEM_TIME_CHECK_FAILED: {e}")
        return {"error": str(e)}