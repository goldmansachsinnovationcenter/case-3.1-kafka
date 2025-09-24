# Zenith Settlement Processing DAG

## Overview

This Airflow DAG processes daily settlement files from Zenith Clearing Corp's FTP server. It provides a comprehensive data pipeline with validation, PostgreSQL loading, and error handling.

## Features

- **FTP File Download**: Automatically downloads daily settlement CSV files from Zenith Clearing Corp FTP server
- **Data Validation**: Comprehensive CSV structure and content validation before processing
- **PostgreSQL Integration**: Idempotent loading into settlements database table
- **Glean MCP Integration**: Queries Glean MCP server for incident insights and lessons learned
- **Error Handling**: Robust retry mechanisms and error logging
- **Monitoring**: Completion alerts and comprehensive logging

## DAG Configuration

- **DAG ID**: `zenith_settlement_processing`
- **Schedule**: Daily at 6:00 AM (`0 6 * * *`)
- **Max Active Runs**: 1 (prevents concurrent executions)
- **Retries**: 3 attempts with 5-minute delays
- **Catchup**: Disabled

## Task Flow

```
get_glean_insights → download_settlement_file → validate_csv_structure → load_to_postgresql → send_completion_alert → cleanup_temp_files
```

### Task Details

1. **get_glean_insights**: Queries Glean MCP server for settlement processing best practices and common issues
2. **download_settlement_file**: Downloads CSV file from Zenith FTP server (format: `ZENITH_SETTLE_YYYYMMDD.csv`)
3. **validate_csv_structure**: Validates CSV structure, data types, and business rules
4. **load_to_postgresql**: Loads validated data into PostgreSQL settlements table with idempotent processing
5. **send_completion_alert**: Sends processing completion notification
6. **cleanup_temp_files**: Removes temporary files (runs even if upstream tasks fail)

## Expected CSV Structure

The settlement files must contain the following columns:
- `transaction_id` (string, unique)
- `transaction_date` (date, YYYY-MM-DD format)
- `settlement_amount` (numeric)
- `currency` (string, 3-character code)
- `account_number` (string)
- `settlement_status` (string)
- `clearing_member` (string)
- `instrument_id` (string)

## Database Schema

The DAG creates and populates the `settlements` table with the following structure:

```sql
CREATE TABLE settlements (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    transaction_date DATE NOT NULL,
    settlement_amount NUMERIC(20, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    account_number VARCHAR(20) NOT NULL,
    settlement_status VARCHAR(20) NOT NULL,
    clearing_member VARCHAR(100),
    instrument_id VARCHAR(50),
    file_source VARCHAR(100),
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Required Airflow Variables

Configure the following Airflow Variables before running the DAG:

- `ZENITH_FTP_HOST`: FTP server hostname (default: ftp.zenithclearingcorp.com)
- `ZENITH_FTP_USER`: FTP username
- `ZENITH_FTP_PASSWORD`: FTP password
- `ZENITH_FTP_DIRECTORY`: FTP directory path (default: /settlement_files)

## Required Airflow Connections

- `settlements_db`: PostgreSQL connection for the settlements database

## Error Handling

- **FTP Failures**: Retries with exponential backoff
- **Validation Errors**: Detailed logging of validation failures
- **Database Errors**: Idempotent loading prevents duplicate processing
- **File Cleanup**: Always runs regardless of task success/failure

## Monitoring and Alerts

- Comprehensive logging at each processing stage
- Processing completion notifications with summary statistics
- Failed task notifications via Airflow's built-in alerting

## Dependencies

- `apache-airflow ^2.10.0`
- `apache-airflow-providers-postgres ^5.0.0`
- `pandas ^2.0.0`
- `psycopg[binary] ^3.2.6`

## Usage

1. Configure required Airflow Variables and Connections
2. Deploy the DAG to your Airflow environment
3. Enable the DAG in the Airflow UI
4. Monitor execution through Airflow's web interface

## Integration with Goldman Sachs Data Processing Patterns

This DAG follows established patterns from the Goldman Sachs data processing ecosystem:

- **Idempotent Processing**: Similar to S3ObjectProcessor patterns in FIle2Kafka repository
- **Comprehensive Validation**: Multi-layer validation approach
- **Error Handling**: Robust retry mechanisms and logging
- **Glean Integration**: Leverages organizational knowledge for incident prevention
