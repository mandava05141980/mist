import requests,os
import json, time
from datetime import datetime, timedelta
from influxdb import InfluxDBClient

from dotenv import load_dotenv

load_dotenv()
# Initialize InfluxDB
#ocal_client = InfluxDBClient('localhost', 8086, 'local_db', 'local123', 'call_quality')
campus_client = InfluxDBClient(host=os.getenv('INFLUXDB_HOST'), port=8086, username=os.getenv('CAMPUS_DB_USER'), password=os.getenv('CAMPUS_DB_PASS'), database=os.getenv('CAMPUS_DB'), ssl=True, verify_ssl=True)
network_client = InfluxDBClient(host=os.getenv('INFLUXDB_HOST'), port=8086, username=os.getenv('NETWORK_DB_USER'), password=os.getenv('NETWORK_DB_PASS'), database=os.getenv('INFLUXDB_DB'), ssl=True, verify_ssl=True)

# Define your API credentials and endpoints
api_token = os.getenv("MIST_API_TOKEN")
base_url = "https://api.mist.com/api/v1/"

# Initialize the list to store influxdb points
influxdb_points = []

# Get Call Count and Mac Address
def get_call_metrics(site_id,start_timestamp, end_timestamp):
    #print(detail["site"])
    endpoint = f"sites/{site_id}/stats/calls/count"
    url = base_url + endpoint
    params = {
        "distinct": "mac",
        "start": start_timestamp,
        "end": end_timestamp,
        "app":"teams"
    }
    headers = {
        'Authorization': api_token,
        "Content-Type": "application/json"
        }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        #print(response.json())
        return response.json()
    else:
        print(f"get_call_metrics_function_Error: {response.status_code}")
        return None

# Get Calls Quality for MAC Address's
def get_quality_metrics(mac,site_id,start_timestamp, end_timestamp):

    endpoint = f"sites/{site_id}/stats/calls/search"
    url = base_url + endpoint
    params = {
        "mac": mac,
        "start": start_timestamp,
        "end": end_timestamp,
        "app":"teams",
        "wired":"false"
    }
    headers = {
        'Authorization': api_token,
        "Content-Type": "application/json"
        }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        #print(response.json())
        return response.json()
    else:
        print(f"get_quality_metrics_fuction_Error: {response.status_code}")
        return None

# Function for Audio Only
def audio_only(audio_quality, detail, timestamp, mac, hostname):
    human_readable_timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    point = {
        "measurement": "teams_zoom_quality_data",
        "tags": {
            "site_name": detail["site"],
            "region": detail["region"],
            "app": "Teams",
            "mac_address": mac,
            "hostname": hostname
        },
        "fields": {
            "audio_Quality": find_rating(audio_quality),
            "overall_A_Quality": find_rating(audio_quality),
            "start_time_hr": human_readable_timestamp
        }
    }
    #print(point)
    influxdb_points.append(point)

# Function for Audio & Screen share Only
def audio_screen_only(audio_quality, screen_share_quality, detail, timestamp, mac, hostname):
    human_readable_timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    point = {
        "measurement": "teams_zoom_quality_data",
        "tags": {
            "site_name": detail["site"],
            "region": detail["region"],
            "app": "Teams",
            "mac_address": mac,
            "hostname": hostname
        },
        "fields": {
            "audio_Quality": find_rating(audio_quality),
            "screen_Share_Quality": find_rating(screen_share_quality),
            "overall_AS_Quality": int((find_rating(audio_quality) + find_rating(screen_share_quality)) / 2),
            "start_time_hr": human_readable_timestamp
        }
    }
   # print(point)
    influxdb_points.append(point)

# Function for Audio & Video Only
def audio_video_only(audio_quality, video_quality, detail, timestamp, mac, hostname):
    human_readable_timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    point = {
        "measurement": "teams_zoom_quality_data",
        "tags": {
            "site_name": detail["site"],
            "region": detail["region"],
            "app": "Teams",
            "mac_address": mac,
            "hostname": hostname
        },
        "fields": {
            "audio_Quality": find_rating(audio_quality),
            "video_Quality": find_rating(video_quality),
            "overall_AV_Quality": int((find_rating(audio_quality) + find_rating(video_quality)) / 2),
            "start_time_hr": human_readable_timestamp
        }
    }
   # print(point)
    influxdb_points.append(point)

# Function for Audio, Video & Screen share
def audio_screen_video(audio_quality, screen_share_quality, video_quality, detail, timestamp, mac, hostname):
    human_readable_timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    point = {
        "measurement": "teams_zoom_quality_data",
        "tags": {
            "site_name": detail["site"],
            "region": detail["region"],
            "app": "Teams",
            "mac_address": mac,
            "hostname": hostname
        },
        "fields": {
            "audio_Quality": find_rating(audio_quality),
            "video_Quality": find_rating(video_quality),
            "screen_Share_Quality": find_rating(screen_share_quality),
            "overall_AVS_Quality": int((find_rating(audio_quality) + find_rating(video_quality) + find_rating(screen_share_quality)) / 3),
            "start_time_hr": human_readable_timestamp
        }
    }
#    print(point)
    influxdb_points.append(point)

# Find the Rating numbers for the rating string.
def find_rating(quality):
    if quality == "good":
        return 5
    elif quality == "fair":
        return 3
    elif quality == "poor" or quality == "bad":
        return 1
     
def main():
    end_timestamp = datetime.now().timestamp() * 1000  # Current time in milliseconds
    start_timestamp = end_timestamp - (12 * 60 * 60 * 1000)  # 12 ago ago in milliseconds
    
    # Path of the JSON file to read the site data
    script_dir = "/home/ubuntu/metric_collector/teams-zoom-insights/"
    mist_data_file = os.path.join(script_dir, 'mist_data.json')

    # Read Mist Site Data
    with open(mist_data_file, 'r') as file:
        site_data = json.load(file)
    for site_id, detail in site_data.items():
        call_metrics = get_call_metrics(site_id, start_timestamp, end_timestamp)
        for mac in call_metrics["results"]:
            quality_call_metrics = get_quality_metrics(mac['mac'],site_id,start_timestamp,end_timestamp)
            for quality in quality_call_metrics.get('results'):
                timestamp = int(quality.get('timestamp', 0) / 1000)  # Convert milliseconds to seconds
                # Condition for Audio only
                if quality.get('screen_share_quality', '') == "" and quality.get('video_quality', '') == "" and quality.get('audio_quality', '') != "":
                    audio_only(quality.get('audio_quality', ''), detail, timestamp, quality.get('mac'), quality.get('hostname'))

                # Condition for Audio and Video only
                elif quality.get('video_quality', '') != "" and quality.get('audio_quality', '') != "" and quality.get('screen_share_quality', '') == "":
                    audio_video_only(quality.get('audio_quality', ''), quality.get('video_quality', ''), detail, timestamp, quality.get('mac'), quality.get('hostname'))

                # Condition for Audio and Screen Share Only
                elif quality.get('video_quality', '') == "" and quality.get('audio_quality', '') != "" and quality.get('screen_share_quality', '') != "":
                    audio_screen_only(quality.get('audio_quality', ''), quality.get('screen_share_quality', ''), detail, timestamp, quality.get('mac'), quality.get('hostname'))

                # Condition for Audio, Video and Screen Share
                elif quality.get('video_quality', '') != "" and quality.get('audio_quality', '') != "" and quality.get('screen_share_quality', '') != "":
                    audio_screen_video(quality.get('audio_quality', ''), quality.get('video_quality', ''), quality.get('screen_share_quality', ''), detail, timestamp, quality.get('mac'), quality.get('hostname'))
                
                # Condition for None for all
                elif quality.get('audio_quality', '') == "" and quality.get('screen_share_quality', '') == "" and quality.get('video_quality', '') == "":
                    pass
    #print(influxdb_points)
    print(len(influxdb_points))
    for point in influxdb_points:
        pass
        #local_client.write_points([point])
        campus_client.write_points([point])
        network_client.write_points([point])
if __name__ == "__main__":
    print("Start Time:   "+ time.ctime(time.time()))
    main()
    print("End Time:    "+ time.ctime(time.time()) + "\n*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
