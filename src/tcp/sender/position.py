def update_position(event, devices):
    if event["type"] == "position":
        data = event["data"]
        for device in devices:
            if device["uniqueid"] == data["imei"]:
                device["latitude"] = data["latitude"]
                device["longitude"] = data["longitude"]
                device["speed"] = data["speed"]
                device["course"] = data["course"]
                break
    return devices
