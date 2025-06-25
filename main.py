# job id
from flask import Flask, request, jsonify
from flask_cors import CORS
import ee
import os
import json
import uuid
import threading
import time

# Inicializar EE con cuenta de servicio
with open('clave.json', 'w') as f:
    json.dump(json.loads(os.environ['EE_CREDENTIALS']), f)

service_account = 'ndvi-401@impactful-shard-464005-q7.iam.gserviceaccount.com'
credentials = ee.ServiceAccountCredentials(service_account, 'clave.json')
ee.Initialize(credentials)

app = Flask(__name__)
CORS(app)

# Diccionario global para guardar resultados NDVI { job_id: tile_url }
results = {}
# Diccionario para estados { job_id: "processing" | "done" | "error" }
statuses = {}

def calculate_ndvi_job(job_id, geometry):
    try:
        coords = geometry
        polygon = ee.Geometry.Polygon([coords])

        today = ee.Date(ee.Date.now())
        start = today.advance(-3, 'month')
        end = today

        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                      .filterBounds(polygon)
                      .filterDate(start, end)
                      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40)))

        count = collection.size().getInfo()
        if count == 0:
            statuses[job_id] = "error"
            results[job_id] = "No images found for this area and date range"
            return

        median = collection.median()
        ndvi = median.normalizedDifference(['B8', 'B4']).rename('NDVI')

        vis = {'min': 0, 'max': 1, 'palette': ['brown', 'yellow', 'green']}
        ndvi_visual = ndvi.clip(polygon).visualize(**vis)
        mapid = ee.data.getMapId({'image': ndvi_visual})

        tile_url = f"https://earthengine.googleapis.com/map/{mapid['mapid']}/{{z}}/{{x}}/{{y}}?token={mapid['token']}"

        results[job_id] = tile_url
        statuses[job_id] = "done"

    except Exception as e:
        statuses[job_id] = "error"
        results[job_id] = str(e)

@app.route('/ndvi', methods=['POST'])
def start_ndvi():
    try:
        data = request.get_json()
        geometry = data.get('geometry')
        if not geometry or not isinstance(geometry, list) or len(geometry) < 3:
            return jsonify({"error": "Geometry missing or invalid"}), 400

        job_id = str(uuid.uuid4())
        statuses[job_id] = "processing"

        # Lanzar hilo para cálculo NDVI asíncrono
        thread = threading.Thread(target=calculate_ndvi_job, args=(job_id, geometry))
        thread.start()

        return jsonify({"job_id": job_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ndvi/result/<job_id>', methods=['GET'])
def get_ndvi_result(job_id):
    status = statuses.get(job_id)
    if not status:
        return jsonify({"error": "Job ID no encontrado"}), 404

    if status == "processing":
        return jsonify({"status": "processing"}), 202
    elif status == "done":
        return jsonify({"status": "done", "tile_url": results[job_id]})
    else:  # error
        return jsonify({"status": "error", "message": results[job_id]}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


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

