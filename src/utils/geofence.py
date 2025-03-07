import re
import math
from shapely.geometry import Point, Polygon


def parse_geofence(geofence_str):
    """Parsea una cadena de geozona en formato POLYGON o CIRCLE y retorna un objeto para realizar verificaciones."""
    if geofence_str.startswith("POLYGON"):
        # Extraer coordenadas del polígono
        coordinates_str = re.search(r"POLYGON \(\((.*)\)\)", geofence_str).group(1)
        coordinate_pairs = coordinates_str.split(", ")

        # Convertir a lista de tuplas (lon, lat)
        polygon_coords = []
        for pair in coordinate_pairs:
            lat, lon = map(float, pair.split())
            polygon_coords.append((lat, lon))

        return {"type": "polygon", "geometry": Polygon(polygon_coords)}

    elif geofence_str.startswith("CIRCLE"):
        # Extraer centro y radio del círculo
        circle_data = re.search(r"CIRCLE \((.*), (.*)\)", geofence_str)

        # Separar latitud y longitud del centro que vienen juntos
        center_coords = circle_data.group(1).split()
        center_lat = float(center_coords[0])
        center_lon = float(center_coords[1])

        radius = float(circle_data.group(2))  # en metros

        return {"type": "circle", "center": (center_lat, center_lon), "radius": radius}

    else:
        raise ValueError("Formato de geozona no reconocido. Use POLYGON o CIRCLE.")


def is_point_in_geofence(lat, lon, geofence):
    """Verifica si un punto está dentro de la geozona."""
    if geofence["type"] == "polygon":
        point = Point(lat, lon)
        return geofence["geometry"].contains(point)

    elif geofence["type"] == "circle":
        # Calcular distancia haversine entre el punto y el centro del círculo
        center_lat, center_lon = geofence["center"]
        radius = geofence["radius"]

        # Distancia haversine (considerando la Tierra como esfera)
        R = 6371000  # Radio de la Tierra en metros

        lat1, lon1 = math.radians(center_lat), math.radians(center_lon)
        lat2, lon2 = math.radians(lat), math.radians(lon)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c

        return distance <= radius


def check_geofence_event(geofence_str, prev_position, current_position):
    """
    Verifica si un vehículo entró o salió de una geozona.

    Args:
        geofence_str (str): Geozona en formato "POLYGON (...)" o "CIRCLE (...)"
        prev_position (dict): Posición anterior con claves 'latitude' y 'longitude'
        current_position (dict): Posición actual con claves 'latitude' y 'longitude'

    Returns:
        str: "GeofenceEnter", "GeofenceExit" o None (si no hubo cambio)
    """
    # Parsear la geozona
    geofence = parse_geofence(geofence_str)

    # Verificar posición anterior
    prev_inside = is_point_in_geofence(
        prev_position["latitude"], prev_position["longitude"], geofence
    )

    # Verificar posición actual
    current_inside = is_point_in_geofence(
        current_position["latitude"], current_position["longitude"], geofence
    )

    # Determinar si entró o salió
    if not prev_inside and current_inside:
        return "GeofenceEnter"
    elif prev_inside and not current_inside:
        return "GeofenceExit"
    else:
        return None  # No hubo cambio
