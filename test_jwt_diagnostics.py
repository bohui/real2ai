#!/usr/bin/env python3
"""
Test JWT diagnostics functionality
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.utils.jwt_diagnostics import (
    decode_jwt_payload_detailed,
    check_system_time_sync,
)


def main():
    print("JWT Diagnostics Test")
    print("=" * 40)

    # Test system time check
    print("1. Testing system time synchronization check...")
    time_info = check_system_time_sync()
    print(f"System time info: {time_info}")
    print()

    # Test with a sample JWT (this is just for format testing)
    sample_jwt = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTY5NTAwMDAwMCwiZXhwIjoxNjk1MDA3MjAwfQ.test_signature"

    print("2. Testing JWT payload decoding...")
    analysis = decode_jwt_payload_detailed(sample_jwt)
    print("JWT Analysis (sample):")
    for key, value in analysis.items():
        print(f"  {key}: {value}")
    print()

    print("3. Ready for real JWT token testing")
    print("Usage: python test_jwt_diagnostics.py '<real-jwt-token>'")

    if len(sys.argv) > 1:
        real_token = sys.argv[1]
        print("\nAnalyzing provided JWT token...")
        real_analysis = decode_jwt_payload_detailed(real_token)
        print("Real JWT Analysis:")
        for key, value in real_analysis.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
