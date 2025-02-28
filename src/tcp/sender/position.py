from datetime import datetime

def update_position(event, devices):
    if event["type"] == "position" and chek_datetime_valid(event["data"]["datetime"]):
        data = event["data"]
        for device in devices:
            if device["uniqueid"] == data["imei"]:
                device["latitude"] = data["latitude"]
                device["longitude"] = data["longitude"]
                device["speed"] = data["speed"]
                device["course"] = data["course"]
                break
    return devices

def chek_datetime_valid(datetime_str):
    print(f"VEHICULO: {datetime_str}")
    print(f"ACTUAL: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return True