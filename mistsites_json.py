import json
import requests

def get_api_data(api_token, url):
    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error accessing the API at {url}:", e)
        return None

def create_json_file(data, filename):
    with open(filename, 'w') as json_file:
        json.dump(data, json_file, indent=4)
    print(f"JSON file '{filename}' created successfully.")

def main():
    api_token = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    sites_url = "https://api.mist.com/api/v1/orgs/78a21ef9-89e6-458f-b8de-c9b227aaf723/sites"
    
    # Fetch data from the endpoint
    sites_data = get_api_data(api_token, sites_url)
    
    if sites_data:
        formatted_data = {}
        for site_info in sites_data:
            site_id = site_info.get("id", "")
            site_name = site_info.get("name", "")
            if site_name:
                # Extracting region from the site name
                region = site_name.split("-")[0].strip()
                formatted_data[site_id] = {
                    "site": site_name,
                    "region": region
                }
        
        #create_json_file(formatted_data, "mist_site_data.json")
        create_json_file(formatted_data, "mist_data.json")

if __name__ == "__main__":
    main()
