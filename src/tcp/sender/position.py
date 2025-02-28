from datetime import datetime, timedelta

def update_position(port, event, devices):
    if event["type"] == "position" and check_datetime_valid(port, event["data"]["datetime"]):
        data = event["data"]
        for device in devices:
            if device["uniqueid"] == data["imei"]:
                device["latitude"] = data["latitude"]
                device["longitude"] = data["longitude"]
                device["speed"] = data["speed"]
                device["course"] = data["course"]
                break
    return devices

def check_datetime_valid(port, datetime_str):
    if port == 6013:  # Sinotrack
        # Convertir la cadena de fecha y hora del vehículo a un objeto datetime
        vehicle_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        # Obtener la hora actual
        current_datetime = datetime.now()

        # Calcular el rango aceptable (una hora menos y un máximo de 5 segundos de diferencia)
        min_acceptable_datetime = current_datetime - timedelta(hours=1, seconds=5)
        max_acceptable_datetime = current_datetime + timedelta(seconds=5)

        # Imprimir los valores para depuración
        print(f"VEHICULO: {vehicle_datetime}")
        print(f"ACTUAL: {current_datetime}")
        print(f"Rango aceptable: {min_acceptable_datetime} - {max_acceptable_datetime}")

        # Verificar si la fecha y hora del vehículo está dentro del rango aceptable
        if min_acceptable_datetime <= vehicle_datetime <= max_acceptable_datetime:
            return True
        else:
            return False
    else:
        return False
