# Security Enhancement Deployment Checklist

## Pre-Deployment

### 1. Dependencies Installation
```bash
# Install system dependencies for python-magic
# macOS
brew install libmagic

# Ubuntu/Debian
apt-get update && apt-get install -y libmagic1

# CentOS/RHEL
yum install file-libs

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
# Add to .env file
SECURITY_ENABLE_FILE_CONTENT_VALIDATION=true
SECURITY_ENABLE_MIME_TYPE_VALIDATION=true
SECURITY_ENABLE_MALWARE_SCANNING=true
SECURITY_MAX_PDF_SIZE=52428800
SECURITY_MAX_DOC_SIZE=26214400
SECURITY_MAX_IMAGE_SIZE=10485760
SECURITY_ENABLE_RATE_LIMITING=true
SECURITY_MAX_UPLOADS_PER_MINUTE=10
SECURITY_MAX_UPLOADS_PER_HOUR=100
```

### 3. Validation Tests
```bash
# Syntax validation
python3 -m py_compile app/core/file_security.py
python3 -m py_compile app/core/security_config.py
python3 -m py_compile app/core/rate_limiter.py

# Implementation validation
python3 validate_security.py

# Run security tests
python -m pytest tests/test_file_security.py -v
```

## Deployment Steps

### 1. Backup Current System
```bash
# Backup current documents.py router
cp app/router/documents.py app/router/documents.py.backup

# Backup current requirements
cp requirements.txt requirements.txt.backup
```

### 2. Deploy Security Files
- ✅ `app/core/file_security.py`
- ✅ `app/core/security_config.py` 
- ✅ `app/core/rate_limiter.py`
- ✅ Updated `app/router/documents.py`
- ✅ Updated `requirements.txt`
- ✅ `tests/test_file_security.py`

### 3. Application Restart
```bash
# Restart the FastAPI application
# This varies by deployment method:

# Docker
docker-compose restart backend

# Systemd
systemctl restart real2ai-backend

# PM2
pm2 restart real2ai-backend

# Development
kill existing process && uvicorn app.main:app --reload
```

## Post-Deployment Verification

### 1. Health Checks
```bash
# Check application startup
curl http://localhost:8000/health

# Check security status endpoint
curl -X GET "http://localhost:8000/api/documents/security/status" \
  -H "Authorization: Bearer <valid_token>"
```

### 2. Security Function Tests

#### Valid File Upload Test
```bash
# Test with valid PDF
curl -X POST "http://localhost:8000/api/documents/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@valid_contract.pdf" \
  -F "contract_type=PURCHASE_AGREEMENT"
```

#### Malicious File Block Test
```bash
# This should be blocked
echo -e "MZ\x90\x00malicious" > test_malicious.pdf
curl -X POST "http://localhost:8000/api/documents/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@test_malicious.pdf"
```

#### Rate Limiting Test
```bash
# Send 11 rapid requests to trigger rate limit
for i in {1..11}; do
  curl -X POST "http://localhost:8000/api/documents/upload" \
    -H "Authorization: Bearer <token>" \
    -F "file=@valid_contract.pdf"
done
```

### 3. Log Verification
```bash
# Check security logs
tail -f logs/security.log

# Look for entries like:
# - "File security validation started"
# - "Security violation detected"
# - "Rate limit exceeded"
```

## Monitoring Setup

### 1. Security Alerts
Configure alerts for:
- Malware detection events
- Repeated security violations
- Rate limiting triggers
- Failed file validations

### 2. Performance Monitoring
Monitor:
- File upload response times
- Security validation performance
- Memory usage during file processing
- False positive rates

### 3. Log Aggregation
Ensure security logs are:
- Centrally collected
- Regularly analyzed
- Properly archived
- Accessible for incident response

## Rollback Plan

If issues arise, rollback procedure:

### 1. Immediate Rollback
```bash
# Restore original files
cp app/router/documents.py.backup app/router/documents.py
cp requirements.txt.backup requirements.txt

# Restart application
systemctl restart real2ai-backend
```

### 2. Disable Security Features
```bash
# Set environment variables to disable security
export SECURITY_ENABLE_FILE_CONTENT_VALIDATION=false
export SECURITY_ENABLE_MIME_TYPE_VALIDATION=false
export SECURITY_ENABLE_MALWARE_SCANNING=false

# Restart application
systemctl restart real2ai-backend
```

### 3. Gradual Re-enable
After issue resolution:
1. Enable one security feature at a time
2. Test thoroughly after each enablement
3. Monitor logs for any new issues
4. Adjust configuration as needed

## Security Baseline

After deployment, the system should:
- ✅ Block malicious executable uploads
- ✅ Validate MIME types against file content
- ✅ Sanitize dangerous filenames
- ✅ Enforce file size limits by type
- ✅ Apply rate limiting per user/IP
- ✅ Log all security events
- ✅ Generate file hashes for tracking

## Success Criteria

Deployment is successful when:
1. ✅ All existing functionality works unchanged
2. ✅ Malicious files are blocked with clear error messages
3. ✅ Valid files upload successfully
4. ✅ Rate limiting functions correctly
5. ✅ Security logs are generated
6. ✅ Performance impact is minimal (<100ms overhead)
7. ✅ No false positives for legitimate files

## Emergency Contacts

- **Security Team**: security@real2ai.com
- **DevOps Team**: devops@real2ai.com  
- **On-Call Engineer**: +1-XXX-XXX-XXXX

## Documentation Updates

After successful deployment:
1. Update API documentation with new security features
2. Create user guide for file upload requirements
3. Update troubleshooting guides
4. Document security configuration options

---

**Deployment Date**: ________________  
**Deployed By**: ________________  
**Verified By**: ________________  
**Rollback Tested**: ☐ Yes ☐ No