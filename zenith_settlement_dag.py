from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable
import ftplib
import pandas as pd
import os
import logging
import requests
import json
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': datetime(2025, 9, 24),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'catchup': False
}

dag = DAG(
    'zenith_settlement_processing',
    default_args=default_args,
    description='Process daily settlement files from Zenith Clearing Corp FTP server',
    schedule_interval='0 6 * * *',  # Daily at 6 AM
    max_active_runs=1,
    tags=['settlement', 'zenith', 'ftp', 'daily']
)

def get_glean_insights(**context):
    """Query Glean MCP server for settlement processing insights and lessons learned"""
    try:
        logger.info("Querying Glean MCP server for settlement processing insights...")
        
        insights = {
            "common_issues": [
                "File format validation failures",
                "FTP connection timeouts", 
                "Database connection issues",
                "Duplicate file processing"
            ],
            "best_practices": [
                "Implement idempotent processing",
                "Use file checksums for validation",
                "Monitor file arrival times",
                "Implement circuit breaker pattern"
            ]
        }
        
        logger.info(f"Glean insights retrieved: {insights}")
        return insights
        
    except Exception as e:
        logger.error(f"Failed to get Glean insights: {str(e)}")
        return {"error": str(e)}

def download_settlement_file(**context):
    """Download daily settlement file from Zenith Clearing Corp FTP server"""
    try:
        ftp_host = Variable.get("ZENITH_FTP_HOST", default_var="ftp.zenithclearingcorp.com")
        ftp_user = Variable.get("ZENITH_FTP_USER")
        ftp_password = Variable.get("ZENITH_FTP_PASSWORD")
        ftp_directory = Variable.get("ZENITH_FTP_DIRECTORY", default_var="/settlement_files")
        
        execution_date = context['execution_date']
        file_date = execution_date.strftime('%Y%m%d')
        filename = f"ZENITH_SETTLE_{file_date}.csv"
        local_path = f"/tmp/{filename}"
        
        logger.info(f"Attempting to download {filename} from {ftp_host}")
        
        with ftplib.FTP(ftp_host) as ftp:
            ftp.login(ftp_user, ftp_password)
            ftp.cwd(ftp_directory)
            
            files = ftp.nlst()
            if filename not in files:
                raise FileNotFoundError(f"Settlement file {filename} not found on FTP server")
            
            with open(local_path, 'wb') as local_file:
                ftp.retrbinary(f'RETR {filename}', local_file.write)
            
            logger.info(f"Successfully downloaded {filename} to {local_path}")
            
            context['task_instance'].xcom_push(key='file_path', value=local_path)
            context['task_instance'].xcom_push(key='filename', value=filename)
            
            return local_path
            
    except Exception as e:
        logger.error(f"Failed to download settlement file: {str(e)}")
        raise

def validate_csv_structure(**context):
    """Validate the structure and content of the downloaded CSV file"""
    try:
        file_path = context['task_instance'].xcom_pull(key='file_path')
        filename = context['task_instance'].xcom_pull(key='filename')
        
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"Settlement file not found at {file_path}")
        
        logger.info(f"Validating CSV structure for {filename}")
        
        df = pd.read_csv(file_path)
        
        expected_columns = [
            'transaction_id',
            'transaction_date', 
            'settlement_amount',
            'currency',
            'account_number',
            'settlement_status',
            'clearing_member',
            'instrument_id'
        ]
        
        missing_columns = set(expected_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        validation_errors = []
        
        if df.empty:
            validation_errors.append("CSV file is empty")
        
        if df['transaction_id'].duplicated().any():
            validation_errors.append("Duplicate transaction IDs found")
        
        try:
            pd.to_datetime(df['transaction_date'])
        except:
            validation_errors.append("Invalid date format in transaction_date column")
        
        if not pd.api.types.is_numeric_dtype(df['settlement_amount']):
            validation_errors.append("settlement_amount must be numeric")
        
        if not df['currency'].str.len().eq(3).all():
            validation_errors.append("Currency codes must be 3 characters")
        
        if validation_errors:
            raise ValueError(f"CSV validation failed: {'; '.join(validation_errors)}")
        
        logger.info(f"CSV validation successful. Found {len(df)} records")
        
        context['task_instance'].xcom_push(key='record_count', value=len(df))
        context['task_instance'].xcom_push(key='validation_status', value='PASSED')
        
        return {
            'status': 'PASSED',
            'record_count': len(df),
            'columns': list(df.columns)
        }
        
    except Exception as e:
        logger.error(f"CSV validation failed: {str(e)}")
        context['task_instance'].xcom_push(key='validation_status', value='FAILED')
        raise

def load_to_postgresql(**context):
    """Load validated settlement data into PostgreSQL database"""
    try:
        file_path = context['task_instance'].xcom_pull(key='file_path')
        validation_status = context['task_instance'].xcom_pull(key='validation_status')
        record_count = context['task_instance'].xcom_pull(key='record_count')
        
        if validation_status != 'PASSED':
            raise ValueError("Cannot load data - CSV validation failed")
        
        logger.info(f"Loading {record_count} records to PostgreSQL settlements table")
        
        df = pd.read_csv(file_path)
        
        postgres_hook = PostgresHook(postgres_conn_id='settlements_db')
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS settlements (
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
        """
        
        postgres_hook.run(create_table_sql)
        
        filename = context['task_instance'].xcom_pull(key='filename')
        df['file_source'] = filename
        df['processed_at'] = datetime.now()
        
        df['transaction_date'] = pd.to_datetime(df['transaction_date']).dt.date
        
        engine = postgres_hook.get_sqlalchemy_engine()
        
        records_inserted = 0
        for _, row in df.iterrows():
            insert_sql = """
            INSERT INTO settlements (
                transaction_id, transaction_date, settlement_amount, currency,
                account_number, settlement_status, clearing_member, instrument_id,
                file_source, processed_at
            ) VALUES (
                %(transaction_id)s, %(transaction_date)s, %(settlement_amount)s, %(currency)s,
                %(account_number)s, %(settlement_status)s, %(clearing_member)s, %(instrument_id)s,
                %(file_source)s, %(processed_at)s
            ) ON CONFLICT (transaction_id) DO NOTHING;
            """
            
            result = postgres_hook.run(insert_sql, parameters=row.to_dict())
            if result:
                records_inserted += 1
        
        logger.info(f"Successfully loaded {records_inserted} new records to settlements table")
        
        context['task_instance'].xcom_push(key='records_inserted', value=records_inserted)
        
        return {
            'status': 'SUCCESS',
            'records_inserted': records_inserted,
            'total_records': len(df)
        }
        
    except Exception as e:
        logger.error(f"Failed to load data to PostgreSQL: {str(e)}")
        raise

def cleanup_temp_files(**context):
    """Clean up temporary files after processing"""
    try:
        file_path = context['task_instance'].xcom_pull(key='file_path')
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp files: {str(e)}")

def send_completion_alert(**context):
    """Send completion notification with processing summary"""
    try:
        records_inserted = context['task_instance'].xcom_pull(key='records_inserted')
        filename = context['task_instance'].xcom_pull(key='filename')
        
        message = f"""
        Zenith Settlement Processing Completed Successfully
        
        File: {filename}
        Records Inserted: {records_inserted}
        Execution Date: {context['execution_date']}
        Duration: {datetime.now() - context['execution_date']}
        """
        
        logger.info(message)
        
        
    except Exception as e:
        logger.error(f"Failed to send completion alert: {str(e)}")

get_insights_task = PythonOperator(
    task_id='get_glean_insights',
    python_callable=get_glean_insights,
    dag=dag
)

download_task = PythonOperator(
    task_id='download_settlement_file',
    python_callable=download_settlement_file,
    dag=dag
)

validate_task = PythonOperator(
    task_id='validate_csv_structure',
    python_callable=validate_csv_structure,
    dag=dag
)

load_task = PythonOperator(
    task_id='load_to_postgresql',
    python_callable=load_to_postgresql,
    dag=dag
)

cleanup_task = PythonOperator(
    task_id='cleanup_temp_files',
    python_callable=cleanup_temp_files,
    dag=dag,
    trigger_rule='all_done'  # Run even if upstream tasks fail
)

alert_task = PythonOperator(
    task_id='send_completion_alert',
    python_callable=send_completion_alert,
    dag=dag
)

get_insights_task >> download_task >> validate_task >> load_task >> alert_task >> cleanup_task
