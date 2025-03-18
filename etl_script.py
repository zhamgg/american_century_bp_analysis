import pandas as pd
import numpy as np
import os
import argparse
from datetime import datetime
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("boardingpass_etl.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("boardingpass_etl")

def extract_data(file_path):
    """
    Extract data from the Excel file
    
    Args:
        file_path (str): Path to the Excel file
        
    Returns:
        pandas.DataFrame: The extracted data
    """
    logger.info(f"Extracting data from {file_path}")
    
    try:
        # Read the Excel file
        df = pd.read_excel(file_path)
        logger.info(f"Successfully read {len(df)} rows from {file_path}")
        
        return df
    except Exception as e:
        logger.error(f"Error extracting data: {str(e)}")
        raise

def transform_data(df):
    """
    Transform the raw data for analysis
    
    Args:
        df (pandas.DataFrame): Raw dataframe
        
    Returns:
        pandas.DataFrame: Transformed dataframe with American Century plans
    """
    logger.info("Transforming data")
    
    try:
        # Verify required columns exist
        required_cols = ['Fund Name', 'Plan Name', 'Request Status', 'Status Detail', 
                       'Cusip', 'Advisor Firm Name', 'Recordkeeper Name', 'NSCC Firm Name']
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.warning(f"Missing columns: {missing_cols}")
        
        # Filter for American Century plans
        df_ac = df[df['Fund Name'].str.contains('American Century', case=False, na=False)]
        
        if len(df_ac) == 0:
            logger.warning("No American Century plans found. Looking for plans with 'American' or 'Century'")
            df_ac = df[df['Fund Name'].str.contains('American|Century', case=False, na=False)]
        
        logger.info(f"Filtered to {len(df_ac)} relevant plan records")
        
        if len(df_ac) == 0:
            logger.error("No relevant plans found in the dataset")
            return pd.DataFrame()
        
        # Clean up date fields
        date_cols = ['Request Date', 'Estimated Funding Date', 'Report As of Date']
        for col in date_cols:
            if col in df_ac.columns:
                df_ac[col] = pd.to_datetime(df_ac[col], errors='coerce')
                
        # Handle missing values
        for col in df_ac.columns:
            # For numeric columns, replace NaN with 0
            if df_ac[col].dtype in [np.float64, np.int64]:
                df_ac[col] = df_ac[col].fillna(0)
            # For string columns, replace NaN with empty string
            elif df_ac[col].dtype == object:
                df_ac[col] = df_ac[col].fillna('')
        
        # Standardize text fields
        text_cols = ['Request Status', 'Status Detail', 'Advisor Firm Name', 
                     'Recordkeeper Name', 'NSCC Firm Name']
        
        for col in text_cols:
            if col in df_ac.columns:
                df_ac[col] = df_ac[col].astype(str).str.strip()
        
        return df_ac
    
    except Exception as e:
        logger.error(f"Error transforming data: {str(e)}")
        raise

def calculate_metrics(df):
    """
    Calculate key metrics from the transformed data
    
    Args:
        df (pandas.DataFrame): Transformed dataframe
        
    Returns:
        dict: Dictionary of calculated metrics
    """
    logger.info("Calculating metrics")
    
    try:
        metrics = {}
        
        # Basic counts
        metrics['total_plans'] = len(df['Plan Name'].unique())
        metrics['total_requests'] = len(df)
        
        # Status distribution
        metrics['status_counts'] = df['Request Status'].value_counts().to_dict()
        metrics['status_percentages'] = (df['Request Status'].value_counts(normalize=True) * 100).round(1).to_dict()
        
        # Status detail distribution
        metrics['status_detail_counts'] = df['Status Detail'].value_counts().to_dict()
        metrics['status_detail_percentages'] = (df['Status Detail'].value_counts(normalize=True) * 100).round(1).to_dict()
        
        # Calculate completion rate
        completed = df[df['Status Detail'].str.contains('Ready to Trade', case=False, na=False)]
        metrics['completed_count'] = len(completed)
        metrics['completion_rate'] = round(len(completed) / len(df) * 100, 1) if len(df) > 0 else 0
        
        # Status by dimensions
        dimensions = ['Advisor Firm Name', 'Recordkeeper Name', 'NSCC Firm Name']
        metrics['by_dimension'] = {}
        
        for dim in dimensions:
            if dim in df.columns:
                # Group by dimension and status
                group_data = df.groupby([dim, 'Request Status']).size().unstack(fill_value=0)
                
                # Add total and sort
                group_data['Total'] = group_data.sum(axis=1)
                sorted_data = group_data.sort_values('Total', ascending=False)
                
                # Convert to dictionaries for JSON serialization
                metrics['by_dimension'][dim] = {
                    'data': sorted_data.reset_index().to_dict('records'),
                    'top_entities': sorted_data.index[:10].tolist()
                }
        
        # Add timestamp
        metrics['generated_at'] = datetime.now().isoformat()
        metrics['data_as_of'] = df['Report As of Date'].max().isoformat() if 'Report As of Date' in df.columns and not df['Report As of Date'].isna().all() else None
        
        return metrics
    
    except Exception as e:
        logger.error(f"Error calculating metrics: {str(e)}")
        raise

def load_data(df, metrics, output_dir):
    """
    Load the processed data and metrics to output files
    
    Args:
        df (pandas.DataFrame): Processed dataframe
        metrics (dict): Calculated metrics
        output_dir (str): Directory to save output files
    """
    logger.info(f"Loading data to {output_dir}")
    
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp for filenames
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save processed data as CSV
        csv_path = os.path.join(output_dir, f'american_century_data_{timestamp}.csv')
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved processed data to {csv_path}")
        
        # Save metrics as JSON
        metrics_path = os.path.join(output_dir, f'american_century_metrics_{timestamp}.json')
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"Saved metrics to {metrics_path}")
        
        # Save latest copies (overwrite)
        latest_csv_path = os.path.join(output_dir, 'american_century_data_latest.csv')
        latest_metrics_path = os.path.join(output_dir, 'american_century_metrics_latest.json')
        
        df.to_csv(latest_csv_path, index=False)
        with open(latest_metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"Updated latest files in {output_dir}")
        
        return {
            'processed_data_path': csv_path,
            'metrics_path': metrics_path,
            'latest_data_path': latest_csv_path,
            'latest_metrics_path': latest_metrics_path
        }
    
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        raise

def run_etl_pipeline(input_file, output_dir):
    """
    Run the full ETL pipeline
    
    Args:
        input_file (str): Path to input Excel file
        output_dir (str): Directory to save output files
        
    Returns:
        dict: Paths to output files
    """
    logger.info(f"Starting ETL pipeline for {input_file}")
    
    try:
        # Extract
        raw_data = extract_data(input_file)
        
        # Transform
        transformed_data = transform_data(raw_data)
        
        if len(transformed_data) == 0:
            logger.warning("No data to process after transformation")
            return None
        
        # Calculate metrics
        metrics = calculate_metrics(transformed_data)
        
        # Load
        output_paths = load_data(transformed_data, metrics, output_dir)
        
        logger.info("ETL pipeline completed successfully")
        return output_paths
    
    except Exception as e:
        logger.error(f"ETL pipeline failed: {str(e)}")
        raise

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='ETL for American Century Boardingpass data')
    parser.add_argument('--input', required=True, help='Path to the input Excel file')
    parser.add_argument('--output', default='./output', help='Directory to save output files')
    
    args = parser.parse_args()
    
    try:
        # Run the ETL pipeline
        output_paths = run_etl_pipeline(args.input, args.output)
        
        if output_paths:
            print(f"ETL completed successfully. Output files:")
            for key, path in output_paths.items():
                print(f"  {key}: {path}")
        else:
            print("ETL completed but no data was processed.")
    
    except Exception as e:
        print(f"ETL failed: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
