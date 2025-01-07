import pandas as pd
import requests
import gzip
import io

def download_and_load_epss_scores(url):
    try:
        # Download the gzipped CSV file
        response = requests.get(url)
        response.raise_for_status()  # Check for request errors

        # Decompress and read into a Pandas DataFrame
        with gzip.open(io.BytesIO(response.content), 'rt') as f:
            # Skip metadata rows (assume first row is a comment or metadata)
            df = pd.read_csv(f, skiprows=1, low_memory=False)
        
        # Standardize column names
        df.columns = df.columns.str.lower()
        return df
    except requests.RequestException as e:
        print(f"Error downloading the EPSS scores file: {e}")
        return None
    except Exception as e:
        print(f"Error processing the EPSS scores file: {e}")
        return None



def get_epss_scores_from_file(cve_ids, df):
    if df is not None:
        # Filter the DataFrame for the CVE IDs
        result = df[df['cve'].isin(cve_ids)]
        return result[['cve', 'epss']].set_index('cve').to_dict()['epss']
    else:
        return {}
