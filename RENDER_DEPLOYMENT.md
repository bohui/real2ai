# Real2AI Render Deployment Guide

This guide explains how to deploy the Real2AI application to Render using the provided `render.yaml` configuration file.

## Overview

The deployment consists of the following services:

1. **Backend API** (`real2ai-backend`) - FastAPI application
2. **Frontend** (`real2ai-frontend`) - React/Vite static site
3. **Redis** (`real2ai-redis`) - Cache and message broker
4. **Celery Workers** - Background task processing:
   - General worker (`real2ai-celery-worker`)
   - OCR specialist worker (`real2ai-celery-ocr-worker`)
   - Batch processing worker (`real2ai-celery-batch-worker`)
   - Scheduled tasks worker (`real2ai-celery-beat`)

## Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Push your code to a GitHub repository
3. **API Keys**: Prepare the following API keys and secrets:
   - Supabase URL and keys
   - OpenAI API key
   - Gemini API key
   - CoreLogic API key
   - Domain API key
   - JWT secret key
   - Google Cloud credentials (if using GCP services)

## Deployment Steps

### 1. Connect Repository to Render

1. Log in to your Render dashboard
2. Click "New +" and select "Blueprint"
3. Connect your GitHub repository
4. Render will automatically detect the `render.yaml` file

### 2. Configure Environment Variables

Before deploying, you need to set up the following environment variables in Render:

#### Backend API Service Variables
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key
- `OPENAI_API_KEY` - OpenAI API key
- `GEMINI_API_KEY` - Google Gemini API key
- `CORE_LOGIC_API_KEY` - CoreLogic API key
- `DOMAIN_API_KEY` - Domain.com API key
- `JWT_SECRET_KEY` - Secret key for JWT tokens

#### Frontend Service Variables
- `VITE_SUPABASE_URL` - Your Supabase project URL
- `VITE_SUPABASE_ANON_KEY` - Supabase anonymous key

### 3. Upload Google Cloud Credentials

If you're using Google Cloud services (like Gemini), you'll need to upload your service account key:

1. In the backend service settings, go to "Environment Variables"
2. Add a file variable named `gcp_key.json`
3. Upload your Google Cloud service account JSON file

### 4. Deploy

1. Click "Create New Blueprint Instance"
2. Render will automatically create all services based on the `render.yaml` configuration
3. Monitor the deployment progress in the dashboard

## Service Configuration Details

### Backend API Service
- **Type**: Web service
- **Environment**: Python
- **Plan**: Starter (upgrade as needed)
- **Health Check**: `/health` endpoint
- **Port**: Automatically assigned by Render

### Frontend Service
- **Type**: Static site
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `./dist`
- **Environment**: Static

### Redis Service
- **Type**: Redis
- **Plan**: Starter
- **Memory Policy**: LRU (Least Recently Used)

### Celery Workers
All workers use the same Python environment and build process:
- **Build Command**: `pip install -r requirements.txt`
- **Root Directory**: `backend`
- **Environment Variables**: Shared with backend service

## Post-Deployment Configuration

### 1. Update Frontend API URL

After deployment, update the frontend's API base URL:

1. Go to the frontend service settings
2. Update `VITE_API_BASE_URL` to your backend service URL
3. Redeploy the frontend service

### 2. Verify Health Checks

Monitor the health check endpoints:
- Backend: `https://your-backend-service.onrender.com/health`
- Redis: Automatically managed by Render

### 3. Test Background Workers

Verify that Celery workers are processing tasks:
1. Check the worker service logs in Render dashboard
2. Submit a test task through the API
3. Monitor task completion in the logs

## Scaling Considerations

### Starter Plan Limits
- **Web Services**: 750 hours/month free
- **Worker Services**: 750 hours/month free
- **Redis**: 30MB storage, 30 connections

### Upgrading Plans
Consider upgrading to paid plans for:
- Higher traffic applications
- More memory-intensive OCR processing
- Larger Redis storage requirements
- Better performance and reliability

## Monitoring and Logs

### Accessing Logs
1. Go to your service in the Render dashboard
2. Click on the service name
3. Navigate to the "Logs" tab
4. Monitor real-time logs and errors

### Health Monitoring
- Backend health check: `/health` endpoint
- Worker status: Monitor Celery worker logs
- Redis connectivity: Automatic monitoring by Render

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check Python dependencies in `requirements.txt`
   - Verify Node.js dependencies in `package.json`
   - Review build logs for specific errors

2. **Environment Variable Issues**
   - Ensure all required variables are set
   - Check variable names match exactly
   - Verify API keys are valid

3. **Worker Connection Issues**
   - Verify Redis connection string
   - Check Celery broker configuration
   - Monitor worker startup logs

4. **Frontend API Connection**
   - Verify `VITE_API_BASE_URL` is correct
   - Check CORS settings in backend
   - Ensure backend service is running

### Debugging Steps

1. **Check Service Logs**
   - Review recent logs for error messages
   - Look for connection timeouts
   - Monitor resource usage

2. **Test Individual Services**
   - Test backend API endpoints directly
   - Verify Redis connectivity
   - Check worker task processing

3. **Verify Dependencies**
   - Ensure all required files are in the repository
   - Check file paths in configuration
   - Verify build commands

## Security Considerations

1. **Environment Variables**
   - Never commit sensitive keys to the repository
   - Use Render's secure environment variable storage
   - Rotate API keys regularly

2. **Service Communication**
   - Services communicate via internal Render network
   - Redis connection uses secure internal URLs
   - API endpoints should implement proper authentication

3. **File Uploads**
   - Consider using external storage (S3, etc.) for file uploads
   - Implement proper file size limits
   - Validate file types and content

## Cost Optimization

1. **Free Tier Usage**
   - Monitor usage across all services
   - Optimize worker concurrency settings
   - Consider consolidating workers if possible

2. **Resource Management**
   - Use appropriate plan sizes
   - Monitor memory and CPU usage
   - Scale down during low-traffic periods

## Support

For deployment issues:
1. Check Render's documentation
2. Review service logs for specific errors
3. Contact Render support for platform-specific issues
4. Review the application's error handling and logging

## Next Steps

After successful deployment:
1. Set up custom domains (if needed)
2. Configure SSL certificates
3. Set up monitoring and alerting
4. Implement CI/CD pipeline for automated deployments
5. Set up backup strategies for data persistence 