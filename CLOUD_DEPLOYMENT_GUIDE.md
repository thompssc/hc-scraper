# HappyCow Cloud Scraper Deployment Guide

## Overview
Complete step-by-step guide to deploy the HappyCow scraper using n8n cloud, Supabase, and a cloud-hosted Python service.

## Architecture
```
Supabase (Database) ←→ n8n Cloud (Orchestration) ←→ Python Service (Scraping) ←→ Slack (Notifications)
```

## Step 1: Supabase Setup 🗄️

### 1.1 Create Tables
1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy and paste the entire content of `supabase_setup.sql`
4. Click **Run** to execute all SQL commands

### 1.2 Get Supabase Credentials
You'll need these for n8n:
- **SUPABASE_URL**: `https://your-project.supabase.co`
- **SUPABASE_SERVICE_KEY**: Found in Settings → API → service_role key

### 1.3 Populate City Queue
1. Run the population script:
   ```bash
   python populate_city_queue.py
   ```
2. Enter your Supabase URL and Service Key when prompted
3. Confirm to insert all 4,800+ cities

## Step 2: Deploy Python Scraper Service 🐍

### 2.1 Deploy to Render (Recommended)

#### Option A: Deploy from GitHub
1. Fork this repository to your GitHub
2. Go to [render.com](https://render.com)
3. Create new **Web Service**
4. Connect your GitHub repository
5. Use these settings:
   - **Build Command**: `pip install -r requirements_cloud.txt`
   - **Start Command**: `gunicorn cloud_scraper_service:app`
   - **Environment**: Python 3.11

#### Option B: Manual Deploy
1. Create new Web Service on Render
2. Upload files: `cloud_scraper_service.py` and `requirements_cloud.txt`
3. Set build and start commands as above

### 2.2 Alternative: Deploy to Railway
1. Go to [railway.app](https://railway.app)
2. Create new project from GitHub
3. Railway will auto-detect Python and deploy

### 2.3 Get Service URL
After deployment, you'll get a URL like:
- **SCRAPER_SERVICE_URL**: `https://your-service.onrender.com`

### 2.4 Test the Service
```bash
curl https://your-service.onrender.com/health
curl -X GET https://your-service.onrender.com/test
```

## Step 3: n8n Cloud Setup ⚙️

### 3.1 Create n8n Cloud Account
1. Go to [n8n.cloud](https://n8n.cloud)
2. Sign up for account (starts at $20/month)
3. Create new workflow

### 3.2 Import Workflow
1. In n8n cloud, click **Import from JSON**
2. Copy content from `n8n_cloud_workflow.json`
3. Paste and import

### 3.3 Configure Environment Variables
In n8n cloud settings, add these environment variables:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
SCRAPER_SERVICE_URL=https://your-service.onrender.com
SLACK_CHANNEL=#happycow-scraper
SLACK_CREDENTIAL_ID=your_slack_credential_id
```

### 3.4 Set Up Slack Integration
1. In n8n, go to **Credentials**
2. Add new **Slack API** credential
3. Follow OAuth setup for your Slack workspace
4. Note the credential ID for environment variables

## Step 4: Testing & Monitoring 🧪

### 4.1 Test Individual Components

#### Test Supabase Functions
```sql
-- Test getting next city
SELECT * FROM get_next_city_to_scrape();

-- Test updating status
SELECT update_city_status(
  (SELECT id FROM city_queue WHERE trigger_status = 'pending' LIMIT 1),
  'running'
);
```

#### Test Python Service
```bash
curl -X POST https://your-service.onrender.com/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.happycow.net/north_america/usa/texas/dallas/",
    "full_path": "north_america/usa/texas/dallas",
    "city": "Dallas",
    "state": "Texas"
  }'
```

### 4.2 Test Full n8n Workflow
1. In n8n cloud, manually trigger the workflow
2. Watch execution progress
3. Check Supabase for inserted data
4. Verify Slack notifications

## Step 5: Production Configuration 🚀

### 5.1 Adjust Scraping Schedule
In the n8n workflow **Schedule Trigger** node:
- **Every 10 minutes**: Fast scraping (recommended for testing)
- **Every 30 minutes**: Moderate pace
- **Every hour**: Conservative pace

### 5.2 Configure Rate Limiting
The Python service includes built-in rate limiting. Adjust if needed:
```python
# In cloud_scraper_service.py
time.sleep(3)  # 3 seconds between requests
```

### 5.3 Monitor Performance
Use the Supabase dashboard view:
```sql
SELECT * FROM scraping_dashboard;
```

This shows:
- Pending/running/completed cities
- Total restaurants scraped
- Error rates
- Performance metrics

## Step 6: Scaling & Optimization 📈

### 6.1 Parallel Processing
To scrape multiple cities simultaneously:
1. Create multiple n8n workflows
2. Use different schedules (offset by 5 minutes)
3. Supabase functions handle concurrency automatically

### 6.2 Error Handling
The system automatically:
- Retries failed cities
- Logs all errors to Supabase
- Sends Slack notifications for failures
- Skips cities after 3 failed attempts

### 6.3 Data Quality Monitoring
Monitor via Supabase:
```sql
-- Cities with errors
SELECT city, state, error_message, retry_count 
FROM city_queue 
WHERE trigger_status = 'error';

-- Recent scraping activity
SELECT * FROM scraping_logs 
ORDER BY started_at DESC 
LIMIT 20;

-- Performance stats
SELECT 
  AVG(restaurants_found) as avg_restaurants,
  AVG(duration_seconds) as avg_duration,
  COUNT(*) as total_scrapes
FROM scraping_logs 
WHERE status = 'completed' 
AND started_at > NOW() - INTERVAL '24 hours';
```

## Cost Estimation 💰

### Monthly Costs:
- **n8n Cloud**: $20-50/month (Starter plan)
- **Render/Railway**: $7-25/month (Python service)
- **Supabase**: $0-25/month (likely free tier)
- **Total**: ~$27-100/month

### Expected Performance:
- **Cities per day**: 144 (every 10 minutes)
- **Restaurants per day**: ~3,000-5,000
- **Complete USA coverage**: ~30-40 days

## Troubleshooting 🔧

### Common Issues:

#### 1. Supabase Connection Errors
- Check environment variables in n8n
- Verify service role key permissions
- Test Supabase API directly

#### 2. Python Service Timeouts
- Check Render/Railway logs
- Verify service is running
- Test health endpoint

#### 3. n8n Workflow Failures
- Check node configurations
- Verify all environment variables
- Test individual nodes

#### 4. No Cities Being Scraped
```sql
-- Check if cities are available
SELECT COUNT(*) FROM city_queue WHERE trigger_status = 'pending';

-- Reset a city for testing
UPDATE city_queue 
SET trigger_status = 'pending', retry_count = 0 
WHERE city = 'Dallas';
```

## Monitoring Dashboard 📊

Create a simple monitoring dashboard by querying:

```sql
-- Overall progress
SELECT 
  trigger_status,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM city_queue), 2) as percentage
FROM city_queue 
GROUP BY trigger_status;

-- Top performing cities
SELECT city, state, restaurants_found, duration_seconds
FROM scraping_logs
WHERE status = 'completed'
ORDER BY restaurants_found DESC
LIMIT 10;

-- Error analysis
SELECT error_message, COUNT(*) as error_count
FROM city_queue
WHERE trigger_status = 'error'
GROUP BY error_message
ORDER BY error_count DESC;
```

## Next Steps 🎯

Once the system is running:

1. **Monitor for 24 hours** to ensure stability
2. **Adjust schedule** based on performance
3. **Add more cities** (international) if desired
4. **Integrate with VeganVoyager** app
5. **Set up automated backups** of Supabase data

## Support 🆘

If you encounter issues:
1. Check service logs (Render/Railway dashboard)
2. Review n8n execution history
3. Query Supabase logs table
4. Test individual components separately

The system is designed to be resilient and self-healing, automatically retrying failed operations and providing comprehensive logging for troubleshooting. 