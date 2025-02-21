##Script will execute and get the data if both RSSI and SNR values are available sites########
import requests
import json
import time
import os
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

# Function to retrieve site metrics
def get_site_metrics(site_id, endpoint, start_timestamp, end_timestamp):
    url = base_url + endpoint.format(site_id, start_timestamp, end_timestamp)
    headers = {'Authorization': api_token}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None

# Function to process rssi_and_snr data
def process_rssi_and_snr(site_id, site_name, region, data):
    rssi_total = 0
    snr_total = 0
    total_clients = len(data)
    has_rssi = False
    has_snr = False

    for client_data in data:
        if 'rssi' in client_data:
            rssi = int(client_data['rssi'])
            rssi_total += rssi
            has_rssi = True
        if 'snr' in client_data:
            snr = int(client_data['snr'])
            snr_total += snr
            has_snr = True

    # Check if both RSSI and SNR data are present
    if not has_rssi or not has_snr:
        return

    # Calculate averages
    avg_rssi = int(rssi_total / total_clients)
    avg_snr = int(snr_total / total_clients)

    # Prepare data in InfluxDB Line Protocol format
    data_points = []
    data_point = {
        "measurement": "mist_site_rssi_snr",
        "tags": {
            "site_name": site_name,
            "region": region
        },
        "fields": {
            "rssi": avg_rssi,
            "snr": avg_snr
        }
    }
    data_points.append(data_point)

    # Writes to DB.!
    campus_client.write_points(data_points)
    network_client.write_points(data_points)

    # Print required information
    #for point in data_points:
        #print(json.dumps(point))

# Function to retrieve a list of devices
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

    # Retrieve data for Each Site
    for site_id, detail in site_data.items():
        # Retrieve rssi_and_snr data
        rssi_and_snr_data = get_site_metrics(site_id, 'sites/{}/stats/clients', start_timestamp, end_timestamp)
        if rssi_and_snr_data:
            process_rssi_and_snr(site_id, detail['site'], detail['region'], rssi_and_snr_data)
    print("End Time:    "+ time.ctime(time.time()) + "\n*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
if __name__ == "__main__":
    get_devices()
