#!/usr/bin/env python3
"""
Debug JWT token expiration timing issues.
This script helps diagnose why JWT tokens are expiring immediately after refresh.
"""

import json
import base64
from datetime import datetime, timezone

def decode_jwt_payload(token):
    """Decode JWT payload to check expiration times"""
    try:
        # JWT has 3 parts: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return {"error": "Invalid JWT format"}
        
        # Decode payload (add padding if needed)
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding
            
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8'))
        
        # Convert timestamps to readable format
        now = datetime.now(timezone.utc)
        result = {
            "current_time": now.isoformat(),
            "current_timestamp": int(now.timestamp()),
        }
        
        if 'exp' in payload:
            exp_dt = datetime.fromtimestamp(payload['exp'], timezone.utc)
            result["expires_at"] = exp_dt.isoformat()
            result["expires_timestamp"] = payload['exp']
            result["expires_in_seconds"] = payload['exp'] - int(now.timestamp())
            result["is_expired"] = payload['exp'] < int(now.timestamp())
            
        if 'iat' in payload:
            iat_dt = datetime.fromtimestamp(payload['iat'], timezone.utc)
            result["issued_at"] = iat_dt.isoformat()
            result["issued_timestamp"] = payload['iat']
            
        if 'aud' in payload:
            result["audience"] = payload['aud']
            
        if 'sub' in payload:
            result["subject"] = payload['sub']
            
        return result
        
    except Exception as e:
        return {"error": f"Failed to decode JWT: {e}"}

import sys

def main():
    print("JWT Token Debugging Tool")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("This tool helps diagnose JWT token timing issues.")
        print()
        print("From your logs, tokens are 881 characters and expire immediately after refresh.")
        print("Expected behavior: JWT should be valid for ~1 hour after refresh")
        print()
        print("Usage: python debug_jwt_issue.py '<your-jwt-token>'")
        print()
        print("This will show:")
        print("- Current server time vs token expiration time")
        print("- If there's a clock synchronization issue")  
        print("- Token audience and subject validation")
        return
    
    token = sys.argv[1]
    print(f"Analyzing JWT token (length: {len(token)} characters)")
    print("=" * 50)
    
    result = decode_jwt_payload(token)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print("JWT Token Analysis:")
    print("-" * 30)
    
    # Current time info
    print(f"Current Time:     {result['current_time']}")
    print(f"Current Timestamp: {result['current_timestamp']}")
    
    # Token timing info
    if 'issued_at' in result:
        print(f"Token Issued:     {result['issued_at']}")
        print(f"Issued Timestamp: {result['issued_timestamp']}")
    
    if 'expires_at' in result:
        print(f"Token Expires:    {result['expires_at']}")
        print(f"Expires Timestamp: {result['expires_timestamp']}")
        print(f"Expires In:       {result['expires_in_seconds']} seconds")
        
        if result['is_expired']:
            print("❌ TOKEN IS EXPIRED!")
            if result['expires_in_seconds'] < -60:
                print(f"   Token expired {abs(result['expires_in_seconds'])} seconds ago")
            else:
                print("   Token expired very recently - possible clock sync issue")
        else:
            print("✅ TOKEN IS VALID")
            if result['expires_in_seconds'] < 300:  # Less than 5 minutes
                print(f"   ⚠️  Token expires soon ({result['expires_in_seconds']}s)")
    
    # Token identity info
    if 'subject' in result:
        print(f"Subject (User):   {result['subject']}")
    if 'audience' in result:
        print(f"Audience:         {result['audience']}")
    
    # Clock sync analysis
    if 'issued_at' in result and 'expires_at' in result:
        token_duration = result['expires_timestamp'] - result['issued_timestamp']
        print(f"Token Duration:   {token_duration} seconds ({token_duration/3600:.1f} hours)")
        
        # Check if token was issued in the future (clock sync issue)
        time_diff = result['issued_timestamp'] - result['current_timestamp']
        if abs(time_diff) > 60:  # More than 1 minute difference
            print(f"⚠️  CLOCK SYNC ISSUE DETECTED!")
            print(f"   Token issued {time_diff:+.0f} seconds relative to current time")
            print("   This indicates a time synchronization problem between:")
            print("   - Your Docker container")
            print("   - Supabase server")

if __name__ == "__main__":
    main()