######Script will capture the site wise avegrage of num_calls and num_users#######
import json
import time
import os
import requests
from influxdb import InfluxDBClient
from dotenv import load_dotenv

load_dotenv()

# Initialize InfluxDB
#local_client = InfluxDBClient('localhost', 8086, 'local_db', 'local123', 'call_quality')
campus_client = InfluxDBClient(host=os.getenv('INFLUXDB_HOST'), port=8086, username=os.getenv('CAMPUS_DB_USER'), password=os.getenv('CAMPUS_DB_PASS'), database=os.getenv('CAMPUS_DB'),ssl=True,verify_ssl=True)
network_client = InfluxDBClient(host=os.getenv('INFLUXDB_HOST'), port=8086, username=os.getenv('NETWORK_DB_USER'), password=os.getenv('NETWORK_DB_PASS'), database=os.getenv('INFLUXDB_DB'),ssl=True,verify_ssl=True)


# Define your API credentials and endpoints
api_token = os.getenv("MIST_API_TOKEN")
base_url = "https://api.mist.com/api/v1/"

# Function to retrieve call metrics data
def get_call_metrics(site_id, start_timestamp, end_timestamp):
    endpoint = f"sites/{site_id}/insights/call-metrics"
    url = base_url + endpoint
    params = {
        'start': start_timestamp,
        'end': end_timestamp,
        'app': 'teams',
        'interval': 3600,
        'wired': 'false'
    }
    headers = {'Authorization': api_token}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        #print(response.json())
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None

# Function to calculate site-wise averages
def calculate_site_averages(site_data):
    site_averages = {}
    
    for site_id, metrics in site_data.items():
        total_num_calls = 0
        total_num_users = 0
        total_values = 0

        if metrics:
            if 'results' in metrics and 'num_calls' in metrics['results'] and 'num_users' in metrics['results']:
                num_calls = sum(metrics['results']['num_calls'])
                num_users = sum(metrics['results']['num_users'])
                if num_calls != 0 or num_users != 0:  # Ignore if both values are 0
                    total_num_calls += num_calls
                    total_num_users += num_users
                    total_values += 1

        if total_values > 0:
            avg_num_calls = int(total_num_calls / total_values)
            avg_num_users = int(total_num_users / total_values)

            site_averages[site_id] = {
                'avg_num_calls': avg_num_calls,
                'avg_num_users': avg_num_users
            }

    return site_averages

# Function to retrieve data for each site
def get_devices():
    # Calculate the start and end timestamps for the last week
    end_timestamp = int(time.time())
    print("Start Time:   "+ time.ctime(time.time()))
    start_timestamp = end_timestamp - (24 * 60 * 60)  # 1 day ago in seconds

    # Path of the JSON file to read the site data
    script_dir = "/home/ubuntu/metric_collector/teams-zoom-insights/"
    mist_data_file = os.path.join(script_dir, 'mist_data.json')

    # Read Mist Site Data
    with open(mist_data_file, 'r') as file:
        site_data = json.load(file)

    # Create a copy of site_data keys
    site_ids = list(site_data.keys())

    # Retrieve data for Each Site
    for site_id in site_ids:
        detail = site_data[site_id]
        # Extract site name from site_data using site_id
        site_name = detail.get('site', f'Unknown Site for Site ID {site_id}')

        # Retrieve call metrics data
        call_metrics_data = get_call_metrics(site_id, start_timestamp, end_timestamp)
        if call_metrics_data:
            site_data[site_name] = call_metrics_data

    # Calculate site-wise averages
    site_averages = calculate_site_averages(site_data)

    # Prepare and print data points for each site
    data_points = []
    for site_name, averages in site_averages.items():
        data_point = {
            "measurement": "mist_site_call_metrics",
            "tags": {
                "site_name": site_name,
                "app_name": "teams"
            },
            "fields": {
                "num_calls": averages['avg_num_calls'],
                "num_users": averages['avg_num_users']
            }
        }
        # Print required information
        data_points.append(data_point)

    # Writes to DB.!
    campus_client.write_points(data_points)
    network_client.write_points(data_points)
    print("End Time:    "+ time.ctime(time.time()) + "\n*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")

if __name__ == "__main__":
    get_devices()
