# libmagic Installation Guide

This guide explains how to install `libmagic` dependencies required for the file security validation module.

## Overview

The file security validation system uses `python-magic` which requires the system library `libmagic` to detect file types and MIME types from file content.

## macOS Installation

### 1. Install system dependency
```bash
# Using Homebrew (recommended)
brew install libmagic

# Alternative: using MacPorts
sudo port install file
```

### 2. Install Python package
```bash
# If using uv (recommended for this project)
uv add python-magic

# If using pip
pip install python-magic
```

### 3. Verify installation
```bash
python -c "import magic; print('✅ python-magic working:', magic.from_buffer(b'test', mime=True))"
```

## Docker/Linux Installation

### Ubuntu/Debian
The Dockerfile already includes the necessary dependencies:
```dockerfile
RUN apt-get update && apt-get install -y \
    libmagic1 \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*
```

### Manual installation on Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install libmagic1 libmagic-dev
pip install python-magic
```

### CentOS/RHEL/Fedora
```bash
# CentOS/RHEL
sudo yum install file-devel
pip install python-magic

# Fedora
sudo dnf install file-devel
pip install python-magic
```

## Troubleshooting

### Error: "failed to find libmagic. Check your installation"

This indicates the system library is missing. Install it using your OS package manager:

- **macOS**: `brew install libmagic`
- **Ubuntu/Debian**: `sudo apt-get install libmagic1 libmagic-dev`
- **CentOS/RHEL**: `sudo yum install file-devel`
- **Fedora**: `sudo dnf install file-devel`

### Error: "No module named 'magic'"

This indicates the Python package is missing:
```bash
# If using uv
uv add python-magic

# If using pip
pip install python-magic
```

### Verification Test

Run this test to verify everything is working:
```bash
python -c "
import magic
print('✅ Magic library loaded successfully')
print('📄 Text detection:', magic.from_buffer(b'Hello World', mime=True))
print('🖼️  PNG detection:', magic.from_buffer(b'\x89PNG\r\n\x1a\n', mime=True))
"
```

Expected output:
```
✅ Magic library loaded successfully
📄 Text detection: text/plain
🖼️  PNG detection: image/png
```

## Fallback Behavior

If `libmagic` is not available, the file security validator will:
1. Skip MIME type validation
2. Log a warning about missing python-magic
3. Continue with other security checks (file extension, size, content scanning)
4. Add a warning to the validation result

This ensures the application remains functional even without optimal file type detection.

## Production Deployment

For production deployments, ensure:
1. `libmagic1` and `libmagic-dev` are installed in your container/server
2. `python-magic==0.4.27` is in your requirements.txt
3. Run the verification test after deployment
4. Monitor logs for any "python-magic not available" warnings

## Security Note

File type detection via `libmagic` provides an additional security layer by:
- Detecting file type from content, not just extension
- Preventing malicious files with misleading extensions
- Validating that uploaded files match their claimed type

However, the security validator includes multiple layers of protection and will continue to function with reduced capability if `libmagic` is unavailable.