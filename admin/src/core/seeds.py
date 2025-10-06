from src.core.users import service as user_service
from src.core.sites import service as sites_service

def run():
    users = [
        {
            "email":"user1@example.com",
            "first_name":"Usuario1",        
            "last_name":"Uno",             
            "password":"12345678", 
            "role":"public"
        },
        {
            "email":"admin@example.com",
            "first_name":"Admin",
            "last_name":"Dos",
            "password":"12345678",
            "role":"admin"
        },
        {
            "email":"editor@example.com",
            "first_name":"Editor",
            "last_name":"Tres",
            "password":"12345678",
            "role":"editor"
        },
        {
            "email":"systemAdmin@example.com",
            "first_name":"SysAdmin",
            "last_name":"Cuatro",
            "password":"12345678",
            "role":"sysadmin"
        }
    ]
    
    for payload in users:
        ok, user, errors = user_service.create_user(payload)
        if not ok:
            print(f"[SEED ERROR] {payload['email']}: {errors}")
        else:
            print(f"[SEED OK] {user.email}")

    print(f"Seeds de usuarios cargada")

    # Seeds de sitios históricos 
    historic_sites = [
        {
            "name": "Cabildo de Buenos Aires",
            "short_description": "Descripcion corta...",
            "full_description": "Descripcion larga...",
            "city": "La Plata",
            "province": "Buenos Aires",
            "latitude": -34.6081,
            "longitude": -58.3725,
            "conservation_status": "Bueno",
            "inaguration_year": 1725,
            "category": "Arquitectura",
            "is_visible": True,
        },
        {
            "name": "Puente Viejo",
            "short_description": "Descripcion corta...",
            "full_description": "Descripcion completa...",
            "city": "Tandil",
            "province": "Buenos Aires",
            "latitude": -37.3212,
            "longitude": -59.1333,
            "conservation_status": "Regular",
            "inaguration_year": 1890,
            "category": "Infraestructura",
            "is_visible": True,
        },
        {
            "name": "Sitio Arqueológico Las Piedras",
            "short_description": "Descripcion corta...",
            "full_description": "Descripcion completa...",
            "city": "Cafayate",
            "province": "Salta",
            "latitude": -26.0723,
            "longitude": -65.9763,
            "conservation_status": "Malo",
            "inaguration_year": 1200,
            "category": "Sitio arqueológico",
            "is_visible": False,
        },
    ]
    # evitar duplicados si ya existe el nombre
    existing_names = {site.get("name") for site in sites_service.list_sites()} if hasattr(sites_service, "list_sites") else set()

    # payload desmpaqueta el dict payload
    for site in historic_sites:
        name = site.get("name")
        if name in existing_names:
            print(f"[SEED ERROR] {name} ya existe")
            continue
        try:
            site = sites_service.create_site(**site)
            print(f"[SEED OK] {site.name}")
        except Exception as e:
            print(f"[SEED ERROR] {name}: {e}")

    print("Seeds de sitios históricos cargadas")