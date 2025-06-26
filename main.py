from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import requests
import datetime

SENTINEL_CLIENT_ID = os.environ["SENTINEL_CLIENT_ID"]
SENTINEL_CLIENT_SECRET = os.environ["SENTINEL_CLIENT_SECRET"]

app = Flask(__name__)
CORS(app)

def get_sentinel_token():
    resp = requests.post(
        "https://services.sentinel-hub.com/oauth/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": SENTINEL_CLIENT_ID,
            "client_secret": SENTINEL_CLIENT_SECRET,
        }
    )
    return resp.json()["access_token"]

def build_ndvi_evalscript():
    return """
    //VERSION=3
    function setup() {
      return {
        input: ["B8", "B4"],
        output: {
          bands: 3
        }
      };
    }

    function evaluatePixel(sample) {
      let ndvi = (sample.B8 - sample.B4) / (sample.B8 + sample.B4);
      if (ndvi < 0.0) return [165, 42, 42]; // brown
      else if (ndvi < 0.3) return [255, 255, 0]; // yellow
      else return [0, 128, 0]; // green
    }
    """

@app.route("/ndvi", methods=["POST"])
def ndvi_map():
    try:
        data = request.get_json()
        geometry = data.get("geometry")

        if not geometry or not isinstance(geometry, list) or len(geometry) < 3:
            return jsonify({"error": "No geometry received or geometry is invalid"}), 400

        coords = [[lon, lat] for lat, lon in geometry]
        bbox = [
            min(x[0] for x in coords),
            min(x[1] for x in coords),
            max(x[0] for x in coords),
            max(x[1] for x in coords)
        ]

        today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        three_months_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=90)).strftime('%Y-%m-%d')

        token = get_sentinel_token()
        evalscript = build_ndvi_evalscript()

        payload = {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
                },
                "data": [{
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": three_months_ago + "T00:00:00Z",
                            "to": today + "T23:59:59Z"
                        },
                        "maxCloudCoverage": 40
                    }
                }]
            },
            "output": {
                "width": 512,
                "height": 512,
                "responses": [{
                    "identifier": "default",
                    "format": {"type": "image/png"}
                }]
            },
            "evalscript": evalscript
        }

        response = requests.post(
            "https://services.sentinel-hub.com/api/v1/process",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json=payload
        )

        if response.status_code != 200:
            return jsonify({"error": "Error from Sentinel Hub", "details": response.text}), 500

        # Devuelve la imagen como base64 o sirve por endpoint alternativo
        image_bytes = response.content
        with open("ndvi.png", "wb") as f:
            f.write(image_bytes)

        return jsonify({"status": "NDVI image saved as ndvi.png"})

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import ee
# import os
# import json
# import datetime

# # Guarda la clave JSON desde la variable de entorno
# with open('clave.json', 'w') as f:
#     json.dump(json.loads(os.environ['EE_CREDENTIALS']), f)

# # Inicializa EE con cuenta de servicio
# service_account = 'ndvi-401@impactful-shard-464005-q7.iam.gserviceaccount.com'
# credentials = ee.ServiceAccountCredentials(service_account, 'clave.json')
# ee.Initialize(credentials)

# app = Flask(__name__)
# CORS(app)

# @app.route("/ndvi", methods=["POST"])
# def ndvi_map():
#     try:
#         data = request.get_json()
#         geometry = data.get("geometry")

#         if not geometry or not isinstance(geometry, list) or len(geometry) < 3:
#             return jsonify({"error": "No geometry received or geometry is invalid"}), 400

#         # Convertir [lat, lon] → [lon, lat]
#         coords = [[lon, lat] for lat, lon in geometry]
#         polygon = ee.Geometry.Polygon([coords])

#         # Fechas: últimos 3 meses
#         today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
#         start = ee.Date(today).advance(-3, 'month')
#         end = ee.Date(today)

#         # Colección Sentinel-2
#         collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
#                       .filterBounds(polygon)
#                       .filterDate(start, end)
#                       .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40)))

#         # Verifica si hay imágenes
#         if collection.size().getInfo() == 0:
#             return jsonify({"error": "No images found for this area and date range"}), 400

#         # Calcular NDVI
#         median = collection.median()
#         ndvi = median.normalizedDifference(['B8', 'B4']).rename('NDVI')
#         ndvi_visual = ndvi.clip(polygon).visualize(**{
#             'min': 0,
#             'max': 1,
#             'palette': ['brown', 'yellow', 'green']
#         })

#         # Generar tile_url
#         mapid = ee.data.getMapId({'image': ndvi_visual})
#         print("MapID:", mapid)
#         tile_url = f"https://earthengine.googleapis.com/map/{mapid['mapid']}/{{z}}/{{x}}/{{y}}?token={mapid['token']}"

#         return jsonify({ "tile_url": tile_url })

#     except Exception as e:
#         import traceback
#         print(traceback.format_exc())
#         return jsonify({"error": str(e)}), 500

# if __name__ == "__main__":
#     port = int(os.environ.get('PORT', 5000))
#     app.run(host='0.0.0.0', port=port)


# lento
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import ee
# import os
# import json
# import datetime  # Import necesario para fecha

# # Guarda la clave JSON localmente desde variable de entorno
# with open('clave.json', 'w') as f:
#     json.dump(json.loads(os.environ['EE_CREDENTIALS']), f)

# # Inicializa Earth Engine con cuenta de servicio
# service_account = 'ndvi-401@impactful-shard-464005-q7.iam.gserviceaccount.com'
# credentials = ee.ServiceAccountCredentials(service_account, 'clave.json')
# ee.Initialize(credentials)

# app = Flask(__name__)
# CORS(app)

# @app.route("/ndvi", methods=["POST"])
# def ndvi_map():
#     try:
#         data = request.get_json()
#         geometry = data.get("geometry")

#         if not geometry or not isinstance(geometry, list) or len(geometry) < 3:
#             return jsonify({"error": "No geometry received or geometry is invalid"}), 400

#         # Convierte [lat, lon] a [lon, lat]
#         coords = [[lon, lat] for lat, lon in geometry]
#         polygon = ee.Geometry.Polygon([coords])

#         # Fechas: últimos 3 meses usando datetime para obtener fecha actual
#         today = ee.Date(datetime.datetime.utcnow().strftime('%Y-%m-%d'))
#         start = today.advance(-3, 'month')
#         end = today

#         # Colección Sentinel-2
#         collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
#                       .filterBounds(polygon)
#                       .filterDate(start, end)
#                       .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40)))

#         # Verifica si hay imágenes
#         count = collection.size().getInfo()
#         if count == 0:
#             return jsonify({"error": "No images found for this area and date range"}), 400

#         # Procesa NDVI
#         median = collection.median()
#         ndvi = median.normalizedDifference(['B8', 'B4']).rename('NDVI')

#         vis = {'min': 0, 'max': 1, 'palette': ['brown', 'yellow', 'green']}
#         ndvi_visual = ndvi.clip(polygon).visualize(**vis)
#         mapid = ee.data.getMapId({'image': ndvi_visual})

#         return jsonify({
#             "tile_url": f"https://earthengine.googleapis.com/map/{mapid['mapid']}/{{z}}/{{x}}/{{y}}?token={mapid['token']}"
#         })

#     except Exception as e:
#         import traceback
#         print(traceback.format_exc())
#         return jsonify({"error": str(e)}), 500

# if __name__ == "__main__":
#     port = int(os.environ.get('PORT', 5000))
#     app.run(host='0.0.0.0', port=port)

# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import ee
# import os
# import json

# # Guarda la clave JSON localmente desde variable de entorno
# with open('clave.json', 'w') as f:
#     json.dump(json.loads(os.environ['EE_CREDENTIALS']), f)

# # Inicializa Earth Engine con cuenta de servicio
# service_account = 'ndvi-401@impactful-shard-464005-q7.iam.gserviceaccount.com'
# credentials = ee.ServiceAccountCredentials(service_account, 'clave.json')
# ee.Initialize(credentials)

# app = Flask(__name__)
# CORS(app)

# @app.route("/ndvi", methods=["POST"])
# def ndvi_map():
#     try:
#         data = request.get_json()
#         geometry = data.get("geometry")

#         if not geometry or not isinstance(geometry, list) or len(geometry) < 3:
#             return jsonify({"error": "No geometry received or geometry is invalid"}), 400

#         # Convierte [lat, lon] a [lon, lat]
#         coords = [[lon, lat] for lat, lon in geometry]
#         polygon = ee.Geometry.Polygon([coords])

#         # Fechas: últimos 3 meses
#         today = ee.Date(ee.Date.now())
#         start = today.advance(-3, 'month')
#         end = today

#         # Colección Sentinel-2
#         collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
#                       .filterBounds(polygon)
#                       .filterDate(start, end)
#                       .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40)))

#         # Verifica si hay imágenes
#         count = collection.size().getInfo()
#         if count == 0:
#             return jsonify({"error": "No images found for this area and date range"}), 400

#         # Procesa NDVI
#         median = collection.median()
#         ndvi = median.normalizedDifference(['B8', 'B4']).rename('NDVI')

#         vis = {'min': 0, 'max': 1, 'palette': ['brown', 'yellow', 'green']}
#         ndvi_visual = ndvi.clip(polygon).visualize(**vis)
#         mapid = ee.data.getMapId({'image': ndvi_visual})

#         return jsonify({
#             "tile_url": f"https://earthengine.googleapis.com/map/{mapid['mapid']}/{{z}}/{{x}}/{{y}}?token={mapid['token']}"
#         })

#     except Exception as e:
#         import traceback
#         print(traceback.format_exc())
#         return jsonify({"error": str(e)}), 500

# if __name__ == "__main__":
#     port = int(os.environ.get('PORT', 5000))
#     app.run(host='0.0.0.0', port=port)

# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import ee
# import os
# import json
# import datetime

# # Guarda la clave JSON localmente desde variable de entorno
# with open('clave.json', 'w') as f:
#     json.dump(json.loads(os.environ['EE_CREDENTIALS']), f)

# # Inicializa Earth Engine con cuenta de servicio
# service_account = 'ndvi-401@impactful-shard-464005-q7.iam.gserviceaccount.com'
# credentials = ee.ServiceAccountCredentials(service_account, 'clave.json')
# ee.Initialize(credentials)

# app = Flask(__name__)
# CORS(app)

# @app.route("/ndvi", methods=["POST"])
# def ndvi_map():
#     try:
#         data = request.get_json()
#         print("Datos recibidos:", data)  # Para debug

#         if not data or "geometry" not in data:
#             return jsonify({"error": "No geometry received"}), 400

#         geometry = data["geometry"]
#         if not geometry or not isinstance(geometry, list) or len(geometry) == 0:
#             return jsonify({"error": "Geometry empty or invalid"}), 400

#         # Convierte [lat, lon] a [lon, lat]
#         coords = [[lon, lat] for lat, lon in geometry]
#         polygon = ee.Geometry.Polygon([coords])

#         # Fechas con datetime estándar
#         today = datetime.date.today()
#         start = (today.replace(day=1))  # Primer día de mes
#         end = today

#         # Filtra la colección Sentinel-2 SR Harmonized
#         collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
#                       .filterBounds(polygon)
#                       .filterDate(str(start), str(end))
#                       .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))

#         count = collection.size().getInfo()
#         if count == 0:
#             return jsonify({"error": "No images found for this area and date range"}), 400

#         median = collection.median()
#         ndvi = median.normalizedDifference(['B8', 'B4']).rename('NDVI')

#         vis = {'min': 0, 'max': 1, 'palette': ['brown', 'yellow', 'green']}
#         ndvi_visual = ndvi.clip(polygon).visualize(**vis)
#         mapid = ee.data.getMapId({'image': ndvi_visual})

#         return jsonify({
#             "tile_url": f"https://earthengine.googleapis.com/map/{mapid['mapid']}/{{z}}/{{x}}/{{y}}?token={mapid['token']}"
#         })

#     except Exception as e:
#         import traceback
#         print(traceback.format_exc())
#         return jsonify({"error": str(e)}), 500


# if __name__ == "__main__":
#     port = int(os.environ.get('PORT', 5000))
#     app.run(host='0.0.0.0', port=port)

