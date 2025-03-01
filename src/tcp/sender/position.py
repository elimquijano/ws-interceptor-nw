from datetime import datetime, timedelta


def update_position(port, event, devices):
    if event["type"] == "position" and check_datetime_valid(
        port, event["data"]["datetime"]
    ):
        data = event["data"]
        for device in devices:
            if device["uniqueid"] == data["imei"]:
                device["latitude"] = data["latitude"]
                device["longitude"] = data["longitude"]
                device["speed"] = data["speed"] if data["speed"] else 0.0
                device["course"] = data["course"] if data["course"] else 0.0
                break
        return devices
    else:
        return None


def check_datetime_valid(port, datetime_str):
    # Convertir la cadena de fecha y hora del vehículo a un objeto datetime
    vehicle_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    # Obtener la hora actual
    current_datetime = datetime.now()

    if port == 6013:  # Sinotrack
        # Calcular el rango aceptable (una hora menos y un máximo de 20 segundos de diferencia)
        min_acceptable_datetime = current_datetime - timedelta(hours=1, seconds=20)
        max_acceptable_datetime = current_datetime + timedelta(seconds=20)
    elif port == 6001:  # Coban
        # Calcular el rango aceptable (seis horas menos y un máximo de 20 segundos de diferencia)
        min_acceptable_datetime = current_datetime - timedelta(hours=6, seconds=20)
        max_acceptable_datetime = current_datetime + timedelta(seconds=20)
    elif port == 6027:  # Teltonika
        return True
    else:
        return False

    # Verificar si la fecha y hora del vehículo está dentro del rango aceptable
    if min_acceptable_datetime <= vehicle_datetime <= max_acceptable_datetime:
        return True
    else:
        return False
