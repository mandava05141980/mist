import json
import time
import os
import requests
from influxdb import InfluxDBClient
from dotenv import load_dotenv

load_dotenv()

# Initialize InfluxDB
# local_client = InfluxDBClient('localhost', 8086, 'local_db', 'local123', 'call_quality')
campus_client = InfluxDBClient(host=os.getenv('INFLUXDB_HOST'), port=8086, username=os.getenv('CAMPUS_DB_USER'), password=os.getenv('CAMPUS_DB_PASS'), database=os.getenv('CAMPUS_DB'),ssl=True,verify_ssl=True)
network_client = InfluxDBClient(host=os.getenv('INFLUXDB_HOST'), port=8086, username=os.getenv('NETWORK_DB_USER'), password=os.getenv('NETWORK_DB_PASS'), database=os.getenv('INFLUXDB_DB'),ssl=True,verify_ssl=True)

# Define your API credentials and endpoints
api_token = os.getenv("MIST_API_TOKEN")
base_url = "https://api.mist.com/api/v1/"

# Function to retrieve site metrics
def get_site_metrics(site_id, start_timestamp, end_timestamp):
    endpoint = f"sites/{site_id}/insights/site/{site_id}/stats"
    url = base_url + endpoint
    params = {
        'start': start_timestamp,
        'end': end_timestamp,
        'interval': 3600,
        'metrics': 'top-app-by-num_client' 
    }
    headers = {'Authorization': api_token}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None

# Function to retrieve data for all sites
def get_all_site_data(start_timestamp, end_timestamp):
    all_site_data = {}
    # Path of the JSON file to read the site data
    script_dir = "/home/ubuntu/metric_collector/teams-zoom-insights/"
    mist_data_file = os.path.join(script_dir, 'mist_data.json')

    # Read Mist Site Data
    with open(mist_data_file, 'r') as file:
        site_data = json.load(file)

    # Retrieve data for Each Site
    for site_id, detail in site_data.items():
        # Retrieve num_clients data
        num_clients_data = get_site_metrics(site_id, start_timestamp, end_timestamp)
        if num_clients_data:
            all_site_data[site_id] = {'site_name': detail['site'], 'region':detail['region'], 'data': num_clients_data}

    return all_site_data

# Function to process num_clients data and find top 10 apps across all sites

def process_all_sites_data(all_site_data):
    data_points = []

    # Process data for each site
    for site_id, site_info in all_site_data.items():
        site_name = site_info['site_name']
        region = site_info['region']
        site_data = site_info['data']
        app_usage = {}

        if 'top-app-by-num_client' in site_data:
            for app_data in site_data['top-app-by-num_client']:
                app_name = app_data['app']
                num_clients = app_data['num_clients']  
                app_usage[app_name] = app_usage.get(app_name, 0) + num_clients

            # Sort apps by num_clients in descending order for each site
            sorted_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)

            # Get top 10 apps for each site
            top_10_apps = sorted_apps[:10]

            # Print top 10 apps data in InfluxDB Line format for each site
            for app_name, num_clients in top_10_apps:
                data_point = {
                    "measurement": "mist_topapp_clients",
                    "tags": {
                        "site_name": site_name,
                        "region": region,
                        "app": app_name
                    },
                    "fields": {
                        "num_clients": int(num_clients)
                    }
                }
                data_points.append(data_point)

    print(data_points)
    # Writes to DB for each site
    #local_client.write_points(data_points)
    campus_client.write_points(data_points)
    network_client.write_points(data_points)


# Function to retrieve data for all sites and process top 10 apps
def get_top_10_apps():
    # Calculate the start and end timestamps for the last week
    end_timestamp = int(time.time())
    print("Start Time:   "+ time.ctime(time.time()))
    start_timestamp = end_timestamp - (24 * 60 * 60)  # 1 day ago in seconds

    # Retrieve data for all sites
    all_site_data = get_all_site_data(start_timestamp, end_timestamp)

    # Process top 10 apps across all sites
    process_all_sites_data(all_site_data)

    print("End Time:    "+ time.ctime(time.time()) + "\n*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")

if __name__ == "__main__":
    get_top_10_apps()
