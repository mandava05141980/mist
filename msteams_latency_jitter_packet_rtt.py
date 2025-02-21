#####Script to calculate the and get the site wise averages and avoid null values####################
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
    endpoint = f"sites/{site_id}/insights/call-user_qos"
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
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None

# Function to calculate site-wise averages
def calculate_site_averages(site_data):
    site_averages = {}

    for site_name, metrics in site_data.items():
        if metrics and 'results' in metrics:
            results = metrics['results']
            fields = {
                "wan_avg_latency": results.get('wan_avg_latency', []),
                "audio_in_avg_jitter": results.get('audio_in_avg_jitter', []),
                "audio_in_max_jitter": results.get('audio_in_max_jitter', []),
                "audio_out_avg_jitter": results.get('audio_out_avg_jitter', []),
                "audio_out_max_jitter": results.get('audio_out_max_jitter', []),
                "screenshare_in_avg_jitter": results.get('screenshare_in_avg_jitter', []),
                "screenshare_in_max_jitter": results.get('screenshare_in_max_jitter', []),
                "screenshare_out_avg_jitter": results.get('screenshare_out_avg_jitter', []),
                "screenshare_out_max_jitter": results.get('screenshare_out_max_jitter', []),
                "video_in_avg_jitter": results.get('video_in_avg_jitter', []),
                "video_in_max_jitter": results.get('video_in_max_jitter', []),
                "video_out_avg_jitter": results.get('video_out_avg_jitter', []),
                "video_out_max_jitter": results.get('video_out_max_jitter', []),
                "audio_in_avg_pkt_loss": results.get('audio_in_avg_pkt_loss', []),
                "audio_in_max_pkt_loss": results.get('audio_in_max_pkt_loss', []),
                "audio_out_avg_pkt_loss": results.get('audio_out_avg_pkt_loss', []),
                "audio_out_max_pkt_loss": results.get('audio_out_max_pkt_loss', []),
                "screenshare_in_avg_pkt_loss": results.get('screenshare_in_avg_pkt_loss', []),
                "screenshare_in_max_pkt_loss": results.get('screenshare_in_max_pkt_loss', []),
                "screenshare_out_avg_pkt_loss": results.get('screenshare_out_avg_pkt_loss', []),
                "screenshare_out_max_pkt_loss": results.get('screenshare_out_max_pkt_loss', []),
                "video_in_avg_pkt_loss": results.get('video_in_avg_pkt_loss', []),
                "video_in_max_pkt_loss": results.get('video_in_max_pkt_loss', []),
                "video_out_avg_pkt_loss": results.get('video_out_avg_pkt_loss', []),
                "video_out_max_pkt_loss": results.get('video_out_max_pkt_loss', []),
                "audio_in_avg_rtt": results.get('audio_in_avg_rtt', []),
                "audio_in_max_rtt": results.get('audio_in_max_rtt', []),
                "audio_out_avg_rtt": results.get('audio_out_avg_rtt', []),
                "audio_out_max_rtt": results.get('audio_out_max_rtt', []),
                "screenshare_in_avg_rtt": results.get('screenshare_in_avg_rtt', []),
                "screenshare_in_max_rtt": results.get('screenshare_in_max_rtt', []),
                "screenshare_out_avg_rtt": results.get('screenshare_out_avg_rtt', []),
                "screenshare_out_max_rtt": results.get('screenshare_out_max_rtt', []),
                "video_in_avg_rtt": results.get('video_in_avg_rtt', []),
                "video_in_max_rtt": results.get('video_in_max_rtt', []),
                "video_out_avg_rtt": results.get('video_out_avg_rtt', []),
                "video_out_max_rtt": results.get('video_out_max_rtt', [])
            }

            site_avg = {}
            for field, values in fields.items():
                # Filter out None values
                valid_values = [value for value in values if value is not None]
                if valid_values:
                    # Calculate the average value and round to the nearest integer
                    site_avg[field] = round(sum(valid_values) / len(valid_values))

            # Check if there are any non-null fields
            if site_avg:
                site_averages[site_name] = site_avg

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

    data_points = []  # Initialize data_points list

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

    # Prepare and append data points for each site
    for site_name, fields in site_averages.items():

        # Filter out null values from fields
        filtered_fields = {key: value for key, value in fields.items() if value is not None}

        # Check if there are any non-null fields remaining
        if any(filtered_fields.values()):
            data_point = {
                "measurement": "mist_teams_call_qos",
                "tags": {
                    "site_name": site_name,
                    "app name": "teams"
                },
                "fields": filtered_fields
            }
            data_points.append(data_point)
    # Writes to DB.!
    campus_client.write_points(data_points)
    network_client.write_points(data_points)

    print("End Time:    "+ time.ctime(time.time()) + "\n*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")

if __name__ == "__main__":
    get_devices()
