from flask import Flask, request, jsonify
from flask_cors import CORS
import ee
import datetime
import os
import json

# Guarda la clave JSON localmente desde variable de entorno
with open('clave.json', 'w') as f:
    json.dump(json.loads(os.environ['EE_CREDENTIALS']), f)

# Inicializa Earth Engine con cuenta de servicio
service_account = 'ndvi-401@impactful-shard-464005-q7.iam.gserviceaccount.com'
credentials = ee.ServiceAccountCredentials(service_account, 'clave.json')
ee.Initialize(credentials)

app = Flask(__name__)
CORS(app)

@app.route("/ndvi", methods=["POST"])
def ndvi_map():
    try:
        data = request.get_json()
        geometry = data.get("geometry")

        if not geometry:
            return jsonify({"error": "No geometry received"}), 400

        # Convierte [lat, lon] a [lon, lat]
        coords = [[lon, lat] for lat, lon in geometry]
        polygon = ee.Geometry.Polygon([coords])

        # Fechas con datetime y conversión a ee.Date
        today = datetime.date.today()
        start_date = today.replace(day=1)  # Primer día del mes actual
        end_date = today

        ee_start = ee.Date(str(start_date))
        ee_end = ee.Date(str(end_date))

        # Filtra la colección Sentinel-2 SR Harmonized
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                      .filterBounds(polygon)
                      .filterDate(ee_start, ee_end)
                      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))

        count = collection.size().getInfo()
        if count == 0:
            return jsonify({"error": "No images found for this area and date range"}), 400

        median = collection.median()
        ndvi = median.normalizedDifference(['B8', 'B4']).rename('NDVI')

        vis = {'min': 0, 'max': 1, 'palette': ['brown', 'yellow', 'green']}
        ndvi_visual = ndvi.clip(polygon).visualize(**vis)
        mapid = ee.data.getMapId({'image': ndvi_visual})

        return jsonify({
            "tile_url": f"https://earthengine.googleapis.com/map/{mapid['mapid']}/{{z}}/{{x}}/{{y}}?token={mapid['token']}"
        })

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

#         if not geometry:
#             return jsonify({"error": "No geometry received"}), 400

#         # Convierte [lat, lon] a [lon, lat]
#         coords = [[lon, lat] for lat, lon in geometry]
#         polygon = ee.Geometry.Polygon([coords])

#         # Fechas con ee.Date
#         today = ee.Date.today()
#         start = today.advance(-1, 'month')  # Último mes
#         end = today

#         # Filtra la colección Sentinel-2 SR Harmonzied
#         collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
#                       .filterBounds(polygon)
#                       .filterDate(start, end)
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


# if __name__ == "__main__":
#     port = int(os.environ.get('PORT', 5000))
#     app.run(host='0.0.0.0', port=port)
