from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone


def format_timestamp(ts_string: str) -> str:
    """
    Convierte un timestamp de Unix (en formato string) a una fecha y hora
    formateada como "YYYY-MM-DD HH:MM:SS" en UTC.
    """
    try:
        timestamp = int(ts_string)
        # El timestamp de Unix está en UTC, lo especificamos para que sea explícito
        dt_object = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt_object.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        # En caso de que el timestamp no sea válido, retornamos None
        return None


def decode_osmand(fullstring: str) -> list:
    """
    Parsea una cadena de datos del protocolo OsmAnd de Traccar.

    La función puede manejar una o múltiples peticiones HTTP en la misma cadena.
    Extrae los parámetros de la URL, los transforma y los devuelve en una lista
    de diccionarios con un formato estandarizado.

    Args:
        fullstring (str): La cadena completa de datos recibida del dispositivo.

    Returns:
        list: Una lista de diccionarios, donde cada diccionario representa una
              posición decodificada. Retorna una lista vacía si no se pueden
              parsear datos válidos.
    """
    print(fullstring)
    positions = []

    # La cadena puede contener múltiples peticiones HTTP concatenadas.
    # El separador estándar entre cabeceras y cuerpo (vacío en este caso) es '\r\n\r\n'.
    # Usamos esto para dividir la cadena en peticiones individuales.
    requests = fullstring.strip().split("\r\n\r\n")

    for request_text in requests:
        if not request_text.strip():
            continue  # Ignorar partes vacías

        try:
            # 1. Extraer la primera línea de la petición (la que contiene los datos)
            # Ej: 'POST /?id=...&lat=... HTTP/1.1'
            first_line = request_text.split("\r\n", 1)[0]

            # 2. Extraer la parte de la URL con los parámetros
            # El path de la URL es el segundo elemento de la línea de petición
            path_with_query = first_line.split(" ")[1]

            # 3. Parsear la URL para obtener los parámetros de la query
            parsed_url = urlparse(path_with_query)
            # parse_qs devuelve un diccionario donde los valores son listas.
            # Ej: {'id': ['865224'], 'lat': ['-9.9354446']}
            query_params = parse_qs(parsed_url.query)

            # Aplanamos el diccionario para facilitar el acceso
            # Ej: {'id': '865224', 'lat': '-9.9354446'}
            data = {k: v[0] for k, v in query_params.items()}

            # 4. Construir el diccionario de salida con las transformaciones requeridas
            # Usamos .get() para evitar errores si un parámetro opcional no está presente

            imei = data.get("id")
            if not imei:
                # Si no hay ID/IMEI, el registro no es válido, pasamos al siguiente
                continue

            # El protocolo OsmAnd envía la velocidad en nudos (knots).
            # 1 nudo = 1.852 km/h
            speed_knots = float(data.get("speed", 0.0))
            speed_kmh = round(speed_knots * 1.852, 2)

            # Formatear la fecha
            formatted_dt = format_timestamp(data["timestamp"])
            if not formatted_dt:
                # Si la fecha no es válida, descartamos el registro
                continue

            position = {
                "type": "position",
                "imei": imei,
                "datetime": formatted_dt,
                "latitude": round(float(data["lat"]), 6),
                "longitude": round(float(data["lon"]), 6),
                "speed": speed_kmh,
                "course": float(
                    data.get("bearing", 0.0)
                ),  # 'bearing' es el rumbo en OsmAnd
            }

            positions.append(position)

        except (IndexError, KeyError, ValueError) as e:
            # Capturamos errores comunes si la cadena está mal formada
            # o si faltan datos clave como 'lat', 'lon' o 'timestamp'.
            print(
                f"Advertencia: Se omitió un registro mal formado o incompleto. Error: {e}"
            )
            continue

    return positions
