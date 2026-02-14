"""
Culver's Data Pipeline DAG

This DAG orchestrates the data collection process for Culver's restaurant information:
1. Fetches store locations and saves to stores.csv
2. Fetches detailed information for each store and saves to store_details.csv
"""

import sys
import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException


def run_get_locations():
    """Wrapper function to run get_locations with proper working directory"""
    # Add scripts to path and import dynamically
    scripts_dir = '/opt/airflow/scripts'
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    
    # Import here to avoid module-level import issues
    from get_locations import main as get_locations_main
    
    original_dir = os.getcwd()
    try:
        os.chdir('/opt/airflow')
        get_locations_main()
    finally:
        os.chdir(original_dir)


def run_get_store_details():
    """Wrapper function to run get_store_details with proper working directory"""
    # Add scripts to path and import dynamically
    scripts_dir = '/opt/airflow/scripts'
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    
    # Import here to avoid module-level import issues
    from get_store_details import main as get_store_details_main
    
    original_dir = os.getcwd()
    try:
        os.chdir('/opt/airflow')
        get_store_details_main()
    finally:
        os.chdir(original_dir)





def check_csv_exists(file_path):
    """Check if a CSV file exists and has content"""
    if not os.path.exists(file_path):
        raise AirflowException(f"File {file_path} does not exist!")
    
    # Check if file has content (more than just header)
    file_size = os.path.getsize(file_path)
    if file_size < 100:  # Less than 100 bytes means probably empty or just header
        raise AirflowException(f"File {file_path} is too small ({file_size} bytes). May be empty or incomplete.")
    
    # Count lines to verify data
    with open(file_path, 'r') as f:
        line_count = sum(1 for _ in f)
    
    if line_count < 2:  # Less than 2 lines means no data (just header)
        raise AirflowException(f"File {file_path} has no data rows (only {line_count} lines)")
    
    print(f"✓ File {file_path} exists with {line_count} lines ({file_size} bytes)")
    return True

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


# Define the DAG
with DAG(
    dag_id='culvers_data_pipeline',
    default_args=default_args,
    description='Pipeline to fetch Culvers store locations and details',
    schedule='@daily',  # Run daily at midnight
    start_date=datetime(2026, 1, 17),
    catchup=False,
    tags=['culvers', 'data-collection', 'etl'],
) as dag:

    # Task 1: Fetch store locations
    fetch_locations = PythonOperator(
        task_id='fetch_store_locations',
        python_callable=run_get_locations,
        doc_md="""
        ### Fetch Store Locations
        
        This task calls the Culver's API to fetch all store locations across the US.
        It saves the results to `data/stores.csv`.
        
        **Output:** `data/stores.csv`
        """,
    )

    # Task 2: Check if stores.csv was created successfully
    check_stores_file = PythonOperator(
        task_id='check_stores_csv_exists',
        python_callable=check_csv_exists,
        op_kwargs={'file_path': '/opt/airflow/data/stores.csv'},
        doc_md="""
        ### Verify stores.csv
        
        This task checks that the stores.csv file was created successfully
        and contains data before proceeding to fetch store details.
        """,
    )

    # Task 3: Fetch store details
    fetch_store_details = PythonOperator(
        task_id='fetch_store_details',
        python_callable=run_get_store_details,
        doc_md="""
        ### Fetch Store Details
        
        This task reads `data/stores.csv` and fetches detailed information
        for each store using parallel API calls (16 workers).
        It saves the results to `data/store_details.csv`.
        
        **Input:** `data/stores.csv`
        **Output:** `data/store_details.csv`
        """,
    )

    # Task 4: check if store_details.csv was created successfully
    check_store_details_file = PythonOperator(
        task_id='check_store_details_csv_exists',
        python_callable=check_csv_exists,
        op_kwargs={'file_path': '/opt/airflow/data/store_details.csv'},
        doc_md="""
        ### Verify store_details.csv
        
        This task checks that the store_details.csv file was created successfully
        and contains data before proceeding to fetch menu.
        """,
    )
    

    # Define task dependencies
    fetch_locations >> check_stores_file >> fetch_store_details >> check_store_details_file 