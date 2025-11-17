"""Cargo datos iniciales de roles, permisos, usuarios, sitios y flags."""

from src.core.database import db
from src.core.users import UserRole
from src.core.users import service as user_service
from src.core.sites import service as sites_service
from src.core.sites.models import Historic_Site, ReviewStatus, SiteReview
from src.core.flags import service as flags_service
from src.core.permissions import service as permissions_service

def run():
    """Ejecuto todas las seeds y voy mostrando qué pasó en cada paso."""

    # Seeds de roles y permisos
    default_roles = [
        (UserRole.PUBLIC.value, "Usuario público"),
        (UserRole.EDITOR.value, "Editor"),
        (UserRole.ADMIN.value, "Administrador"),
        (UserRole.SYSADMIN.value, "System Admin"),
    ]
    for slug, name in default_roles:
        user_service.ensure_role(slug, name)

    permission_payloads = [
        {"code": "user_index", "description": "Listar usuarios", "roles": [UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "user_show", "description": "Ver detalle de usuario", "roles": [UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "user_new", "description": "Crear usuario", "roles": [UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "user_update", "description": "Actualizar usuario", "roles": [UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "user_destroy", "description": "Eliminar usuario", "roles": [UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "site_index", "description": "Gestionar listado de sitios", "roles": [UserRole.EDITOR, UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "site_new", "description": "Crear sitio histórico", "roles": [UserRole.EDITOR, UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "site_update", "description": "Editar sitio histórico", "roles": [UserRole.EDITOR, UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "site_destroy", "description": "Eliminar sitio histórico", "roles": [UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "site_export", "description": "Exportar sitios históricos", "roles": [UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "site_history_view", "description": "Ver historial de sitios", "roles": [UserRole.EDITOR, UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "proposals_validate", "description": "Validar propuestas ciudadanas", "roles": [UserRole.EDITOR, UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "reviews_moderate", "description": "Moderar reseñas", "roles": [UserRole.EDITOR, UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "featureflags_manage", "description": "Gestionar y ver feature flags", "roles": [UserRole.SYSADMIN]},
        {"code": "tags_index", "description": "Gestionar etiquetas de sitios históricos", "roles": [UserRole.EDITOR, UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "tags_new", "description": "Crear etiquetas de sitios históricos", "roles": [UserRole.EDITOR, UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "tags_edit", "description": "Cargar formulario de edición de etiquetas", "roles": [UserRole.EDITOR, UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "tags_update", "description": "Actualizar etiquetas de sitios históricos", "roles": [UserRole.EDITOR, UserRole.ADMIN, UserRole.SYSADMIN]},
        {"code": "tags_destroy", "description": "Eliminar etiquetas de sitios históricos", "roles": [UserRole.EDITOR, UserRole.ADMIN, UserRole.SYSADMIN]},
    ]

    for payload in permission_payloads:
        code = payload["code"]
        try:
            permissions_service.ensure_permission(
                code,
                description=payload.get("description"),
            )
            print(f"[SEED OK] permiso {code}")
        except Exception as exc:
            print(f"[SEED ERROR] permiso {code}: {exc}")

    for payload in permission_payloads:
        code = payload["code"]
        for role in payload.get("roles", []):
            permissions_service.assign_permission(role, code)

    print(f"Seeds de permisos cargada")

    # Seeds de usuarios iniciales
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
            "short_description": "Icono colonial que resguarda la historia política rioplatense.",
            "full_description": (
                "El Cabildo conserva actas y salas decisivas de la Revolución de Mayo. "
                "Opera como museo con piezas originales de la vida colonial. "
                "Su visita ayuda a comprender el origen institucional porteño."
            ),
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
            "short_description": "Antiguo puente de piedra que unió barrios tandilenses.",
            "full_description": (
                "El Puente Viejo cruza el arroyo Langueyú y dinamizó el comercio barrial. "
                "Sus arcos de mampostería muestran la ingeniería provincial de fin de siglo. "
                "Hoy sigue siendo un paso emblemático y mirador urbano."
            ),
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
            "short_description": "Antiguo asentamiento indígena con vestigios líticos y cerámica local.",
            "full_description": "El Sitio Arqueológico Las Piedras conserva herramientas de piedra y fragmentos cerámicos que revelan modos de vida prehispánicos. Su hallazgo permitió reconstruir rutas de intercambio y prácticas culturales de las primeras comunidades de la región.",
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

    existing_names = {site.get("name") for site in sites_service.list_sites()} if hasattr(sites_service, "list_sites") else set()

    
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

    # Seeds de reseñas de prueba
    site_by_name = {
        site.name: site
        for site in db.session.query(Historic_Site).all()
    }

    review_payloads = [
        {
            "site_name": "Cabildo de Buenos Aires",
            "user_email": "user1@example.com",
            "rating": 5,
            "comment": "Volví hace poco y sigue teniendo ese clima que me encanta.",
            "status": ReviewStatus.PENDING,
            "rejection_reason": None,
        },
        {
            "site_name": "Puente Viejo",
            "user_email": "editor@example.com",
            "rating": 4,
            "comment": "Paso seguido por acá camino al centro y siempre me da nostalgia.",
            "status": ReviewStatus.PENDING,
            "rejection_reason": None,
        },
        {
            "site_name": "Sitio Arqueológico Las Piedras",
            "user_email": "admin@example.com",
            "rating": 3,
            "comment": "La última vez estaba vallado, espero que vuelvan a abrirlo pronto.",
            "status": ReviewStatus.PENDING,
            "rejection_reason": "Mensaje repetido con otros reportes.",
        },
        {
            "site_name": "Cabildo de Buenos Aires",
            "user_email": "editor@example.com",
            "rating": 4,
            "comment": "La visita guiada fue excelente, vale la pena conocerlo.",
            "status": ReviewStatus.APPROVED,
            "rejection_reason": None,
        },
        {
            "site_name": "Cabildo de Buenos Aires",
            "user_email": "admin@example.com",
            "rating": 2,
            "comment": "Creo que podrían mejorar la señalización y la iluminación nocturna.",
            "status": ReviewStatus.APPROVED,
            "rejection_reason": None,
        },
        {
            "site_name": "Puente Viejo",
            "user_email": "user1@example.com",
            "rating": 5,
            "comment": "Perfecto para caminar al atardecer y disfrutar del paisaje.",
            "status": ReviewStatus.APPROVED,
            "rejection_reason": None,
        },
    ]

    for payload in review_payloads:
        site = site_by_name.get(payload["site_name"])
        user = user_service.find_user_by_email(payload["user_email"])
        if not site:
            print(f"[SEED ERROR] review: el sitio {payload['site_name']} no existe")
            continue
        if not user:
            print(f"[SEED ERROR] review: el usuario {payload['user_email']} no existe")
            continue

        existing = (
            db.session.query(SiteReview)
            .filter(
                SiteReview.site_id == site.id,
                SiteReview.user_id == user.id,
            )
            .first()
        )
        if existing:
            print(f"[SEED WARN] review ya existente para {payload['site_name']} y {payload['user_email']}")
            continue

        review = SiteReview(
            site_id=site.id,
            user_id=user.id,
            rating=payload["rating"],
            comment=payload["comment"],
            status=payload["status"],
            rejection_reason=payload["rejection_reason"],
        )
        db.session.add(review)
        print(f"[SEED OK] review de {payload['user_email']} en {payload['site_name']}")

    db.session.commit()

    # Seeds de Flags iniciales
    flags_defaults = [
        {
            "key": "admin_maintenance_mode",
            "name": "Modo mantenimiento administración",
            "description": "Bloquea el panel de administración salvo login.",
            "enabled": False,
            "message": "",
        },
        {
            "key": "portal_maintenance_mode",
            "name": "Modo mantenimiento portal",
            "description": "Pone el portal público en modo mantenimiento.",
            "enabled": False,
            "message": "",
        },
        {
            "key": "reviews_enabled",
            "name": "Reseñas habilitadas",
            "description": "Controla si el portal permite crear nuevas reseñas.",
            "enabled": True,
            "message": "Las reseñas están disponibles.",
        },
    ]


    for data in flags_defaults:
        flags_service.ensure_flag(
            key=data["key"],
            name=data["name"],
            description=data["description"],
            enabled=data["enabled"],
            message=data["message"],
        )
        flags_service.set_flag(
            data["key"],
            enabled=data["enabled"],
            message=data["message"],
            user_id=None,
        )
        print(f"[SEED OK] feature flag {data['key']}")



    print("Seeds de feature flags cargadas")
