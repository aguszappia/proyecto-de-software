from flask import blueprint, request
from src.core.sites.service import list_sites, get_sites_by_location
from src.web.schemas.sites import site_schema

bp = blueprint("sites_api", __name__, url_prefix="/api/issues")

@bp.get("/")
def index():
    data = request.get_json()
    lat = data.get("latitude")
    lon = data.get("longitude")  
    radius = data.get("radius")

    sites = get_sites_by_location(lat, lon, radius)  # uso de coordenadas 
    data = site_schema.dump(sites)
    return data, 200  # conversion a json
