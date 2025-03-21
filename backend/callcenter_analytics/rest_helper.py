import requests
from typing import Dict, List

def send_get(uri, key, expected_status_codes) :
    headers = {"Ocp-Apim-Subscription-Key": key}
    response = requests.get(uri, headers=headers)
    if response.status_code not in expected_status_codes :
        raise Exception(f"The GET request to {uri} returned a status code {response.status_code} that was not in the expected status codes: {expected_status_codes}")
    else :
        try :
            response_json = response.json()
            return { "headers" : response.headers, "text" : response.text, "json" : response_json }
        except Exception :
            return { "headers" : response.headers, "text" : response.text, "json" : None }

def send_post(uri, content, key, expected_status_codes) :
    headers = {"Ocp-Apim-Subscription-Key": key}
    print("Uri for post",uri)
    print("Key in send post",key)
    response = requests.post(uri, headers=headers, json=content)
    if response.status_code not in expected_status_codes :
        raise Exception(f"The POST request to {uri} returned a status code {response.status_code} that was not in the expected status codes: {expected_status_codes}")
    else :
        try :
            response_json = response.json()
            return { "headers" : response.headers, "text" : response.text, "json" : response_json }
        except Exception :
            return { "headers" : response.headers, "text" : response.text, "json" : None }

def send_delete(uri, key, expected_status_codes) :
    headers = {"Ocp-Apim-Subscription-Key": key}
    response = requests.delete(uri, headers=headers)
    if response.status_code not in expected_status_codes :
        raise Exception(f"The DELETE request to {uri} returned a status code {response.status_code} that was not in the expected status codes: {expected_status_codes}")