# LEAP Data Configuration

## Current Status: Mock Data (Offline Mode)

The LEAP application is currently running in **offline mode** with mock/synthetic data for demonstration purposes. This allows you to test all functionality without requiring external API keys or Databricks connections.

## Switching to Real Data

To use real data from EIA, NOAA, Census, and other APIs:

### 1. Configure Environment Variables

Edit your `.env` file and update these settings:

```bash
# Switch to online mode
OFFLINE_MODE=false

# Add your API keys
EIA_API_KEY=your-eia-api-key-here
NOAA_API_TOKEN=your-noaa-token-here

# Configure Databricks connection
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-personal-access-token
DATABRICKS_WAREHOUSE_ID=your-warehouse-id
DATABRICKS_CATALOG=leap
DATABRICKS_SCHEMA=silver
```

### 2. Get API Keys

#### EIA (Energy Information Administration)
- Register at: https://www.eia.gov/opendata/register.php
- Free API key for accessing Form 930 load data
- Rate limit: 5,000 requests per hour

#### NOAA (National Weather Service)
- For historical data: https://www.ncdc.noaa.gov/cdo-web/token
- For forecast data: No key required (api.weather.gov)
- Rate limits apply

### 3. Set up Databricks

1. Create a Databricks workspace
2. Set up Unity Catalog with `leap` catalog
3. Create schemas: `bronze`, `silver`, `gold`
4. Create volume: `/Volumes/leap/bronze/raw`
5. Generate a Personal Access Token

### 4. Initialize Data Pipeline

Once configured, the application will:

1. **Ingest** data from APIs into bronze tables
2. **Process** data into clean silver tables
3. **Engineer** features in gold tables
4. **Train** models using MLflow
5. **Generate** real forecasts

### 5. Data Sources Used

- **EIA Form 930**: Hourly load by balancing authority
- **NOAA NWS**: Weather forecasts and historical data
- **US Census ACS**: Population and demographic data
- **OpenStreetMap**: Points of interest for load drivers

## Mock Data Details

The current mock data includes:
- Realistic load patterns with daily/weekly seasonality
- Multiple balancing authorities (CAISO, ERCOT, PJM, MISO, NYISO)
- Scenario variations (baseline, high growth, hot weather, demand response)
- Model performance metrics
- Weather correlations

## Benefits of Each Mode

### Offline Mode (Current)
- No API keys required
- No rate limits
- Instant response
- Perfect for demos and development
- Synthetic data only

### Online Mode (Real Data)
- Real utility load data
- Actual weather patterns
- True forecasting accuracy
- Production-ready insights
- Requires API setup and keys
- Subject to rate limits

## Need Help?

Check the main README.md for detailed setup instructions or contact your Databricks administrator for workspace configuration assistance.
