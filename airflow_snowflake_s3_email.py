from airflow import DAG
from datetime import timedelta, datetime
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.contrib.operators.snowflake_operator import SnowflakeOperator
from airflow.operators.email import EmailOperator



default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 8),
    'email': ['myemail@domain.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2)
}

# Define the S3 bucket and file details
s3_prefix = 's3://airflow-snow-email-bucket/city_folder/us_city.csv'
s3_bucket = None

with DAG('snowflake_s3_with_email_notification_etl',
        default_args=default_args,
        schedule_interval = '@daily',
        catchup=False) as dag:

        is_file_in_s3_available = S3KeySensor(
        task_id='tsk_is_file_in_s3_available',
        bucket_key=s3_prefix,
        bucket_name=s3_bucket,
        aws_conn_id='aws_s3_conn',
        wildcard_match=False,  # Set this to True if you want to use wildcards in the prefix
        # timeout=60,  # Optional: Timeout for the sensor (in seconds)
        poke_interval=3,  # Optional: Time interval between S3 checks (in seconds)
        )

        create_table = SnowflakeOperator(
            task_id = "create_snowflake_table",
            snowflake_conn_id = 'conn_id_snowflake',           
            sql = '''DROP TABLE IF EXISTS city_info;
                    CREATE TABLE IF NOT EXISTS city_info(
                     city TEXT NOT NULL,
                     state TEXT NOT NULL,
                     census_2020 numeric NOT NULL,
                     land_Area_sq_mile_2020 numeric NOT NULL	
                )
                 '''
        )

        copy_csv_into_snowflake_table = SnowflakeOperator(
            task_id = "tsk_copy_csv_into_snowflake_table",
            snowflake_conn_id = 'conn_id_snowflake',
            sql = '''COPY INTO city_database.new_city_schema.city_info from @city_database.new_city_schema.snowflake_ext_stage_yml FILE_FORMAT = csv_format
                   '''
        )

        notification_by_email = EmailOperator(
        task_id="tsk_notification_by_email",
        to="tuplespectra@gmail.com",
        subject="Snowflake ETL Pipeline",
        html_content="This is just a test."
        )

        is_file_in_s3_available >> create_table >> copy_csv_into_snowflake_table >> notification_by_email