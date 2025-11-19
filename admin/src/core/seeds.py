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
        {
            "name": "Casa Rosada",
            "short_description": "Sede del Poder Ejecutivo y símbolo político del país.",
            "full_description": (
                "La Casa Rosada es uno de los edificios más representativos de Argentina. "
                "Conserva el despacho presidencial y un museo con objetos históricos. "
                "Su arquitectura y relevancia institucional la convierten en un ícono nacional."
            ),
            "city": "Buenos Aires",
            "province": "CABA",
            "latitude": -34.6081,
            "longitude": -58.3703,
            "conservation_status": "Bueno",
            "inaguration_year": 1898,
            "category": "Arquitectura",
            "is_visible": True,
        },
        {
            "name": "Cabildo de Córdoba",
            "short_description": "Centro administrativo del período colonial cordobés.",
            "full_description": (
                "El Cabildo funcionó como sede de autoridades coloniales y provinciales. "
                "Hoy es un museo que conserva documentos y piezas fundamentales de la historia regional. "
                "Su arquitectura refleja la influencia española en el trazado urbano."
            ),
            "city": "Córdoba",
            "province": "Córdoba",
            "latitude": -31.4166,
            "longitude": -64.1830,
            "conservation_status": "Bueno",
            "inaguration_year": 1610,
            "category": "Arquitectura",
            "is_visible": True,
        },
        {
            "name": "Ruinas de San Ignacio Miní",
            "short_description": "Antiguo asentamiento jesuítico-guaraní en piedra rojiza.",
            "full_description": (
                "Las ruinas forman parte del legado jesuítico guaraní declarado Patrimonio Mundial. "
                "Sus muros tallados revelan la integración cultural entre misioneros y pueblos originarios. "
                "Es uno de los sitios arqueológicos más importantes de Misiones."
            ),
            "city": "San Ignacio",
            "province": "Misiones",
            "latitude": -27.2552,
            "longitude": -55.5362,
            "conservation_status": "Regular",
            "inaguration_year": 1696,
            "category": "Sitio arqueológico",
            "is_visible": True,
        },
        {
            "name": "Manzana Jesuítica",
            "short_description": "Conjunto histórico religioso y educativo de los jesuitas.",
            "full_description": (
                "La Manzana Jesuítica incluye iglesias, residencias y la universidad más antigua del país. "
                "Es un testimonio fundamental de la obra educativa y religiosa de la Compañía de Jesús. "
                "Su conservación permite comprender la vida colonial cordobesa."
            ),
            "city": "Córdoba",
            "province": "Córdoba",
            "latitude": -31.4202,
            "longitude": -64.1887,
            "conservation_status": "Bueno",
            "inaguration_year": 1610,
            "category": "Arquitectura",
            "is_visible": True,
        },
        {
            "name": "Puente Viejo de Luján",
            "short_description": "Histórico puente colonial sobre el río Luján.",
            "full_description": (
                "El Puente Viejo fue un paso clave para el comercio y el tránsito de peregrinos hacia la basílica. "
                "Sus arcos de piedra reflejan las técnicas de ingeniería de la colonia. "
                "Hoy es un símbolo del patrimonio vial bonaerense."
            ),
            "city": "Luján",
            "province": "Buenos Aires",
            "latitude": -34.5700,
            "longitude": -59.1050,
            "conservation_status": "Regular",
            "inaguration_year": 1772,
            "category": "Infraestructura",
            "is_visible": True,
        },
        {
            "name": "Basílica de Luján",
            "short_description": "Templo neogótico dedicado a la Virgen de Luján.",
            "full_description": (
                "La basílica es uno de los centros religiosos más visitados del país. "
                "Sus vitrales, torres y su imponente diseño neogótico la convierten en una obra monumental. "
                "Es un punto clave de la devoción popular argentina."
            ),
            "city": "Luján",
            "province": "Buenos Aires",
            "latitude": -34.5695,
            "longitude": -59.1178,
            "conservation_status": "Bueno",
            "inaguration_year": 1910,
            "category": "Arquitectura",
            "is_visible": True,
        },
        {
            "name": "Parque Nacional Iguazú – Sector Histórico",
            "short_description": "Sector pionero en la exploración moderna de las cataratas.",
            "full_description": (
                "El sector histórico conserva senderos y miradores utilizados por los primeros expedicionarios. "
                "Su valor combina importancia natural con legado cultural. "
                "Es uno de los paisajes más reconocidos del país."
            ),
            "city": "Puerto Iguazú",
            "province": "Misiones",
            "latitude": -25.6953,
            "longitude": -54.4367,
            "conservation_status": "Bueno",
            "inaguration_year": 1934,
            "category": "Otro",
            "is_visible": True,
        },
        {
            "name": "Cabildo de Salta",
            "short_description": "Edificio colonial emblemático del norte argentino.",
            "full_description": (
                "El Cabildo de Salta fue un centro político y administrativo durante la colonia. "
                "Su arquitectura y sus colecciones lo convierten en un referente cultural. "
                "Hoy es uno de los museos más importantes de la región."
            ),
            "city": "Salta",
            "province": "Salta",
            "latitude": -24.7870,
            "longitude": -65.4119,
            "conservation_status": "Bueno",
            "inaguration_year": 1789,
            "category": "Arquitectura",
            "is_visible": True,
        },
        {
            "name": "Convento San Francisco",
            "short_description": "Histórico complejo religioso salteño.",
            "full_description": (
                "El Convento San Francisco destaca por su torre campanario y ornamentación colonial. "
                "Conserva piezas artísticas y archivos históricos de los franciscanos. "
                "Es uno de los edificios más reconocidos del norte argentino."
            ),
            "city": "Salta",
            "province": "Salta",
            "latitude": -24.7883,
            "longitude": -65.4104,
            "conservation_status": "Bueno",
            "inaguration_year": 1625,
            "category": "Arquitectura",
            "is_visible": True,
        },
        {
            "name": "Estancia Santa Catalina",
            "short_description": "Histórico establecimiento jesuítico rural.",
            "full_description": (
                "La Estancia Santa Catalina fue un importante centro productivo jesuita. "
                "Su casco histórico y su capilla reflejan una mezcla entre arte europeo y trabajo local. "
                "Es uno de los complejos rurales coloniales mejor conservados."
            ),
            "city": "Santa Catalina",
            "province": "Córdoba",
            "latitude": -31.0380,
            "longitude": -64.0620,
            "conservation_status": "Bueno",
            "inaguration_year": 1750,
            "category": "Arquitectura",
            "is_visible": True,
        },
        {
            "name": "Casa Histórica de Tucumán",
            "short_description": "Lugar donde se declaró la Independencia Argentina.",
            "full_description": (
                "La Casa Histórica conserva las salas donde se reunió el Congreso de 1816. "
                "Su arquitectura es un símbolo de la identidad nacional. "
                "Recibe miles de visitantes cada año interesados en la historia del país."
            ),
            "city": "San Miguel de Tucumán",
            "province": "Tucumán",
            "latitude": -26.8345,
            "longitude": -65.2038,
            "conservation_status": "Bueno",
            "inaguration_year": 1760,
            "category": "Arquitectura",
            "is_visible": True,
        },
        {
            "name": "Molino Forclaz",
            "short_description": "Molino eólico construido por inmigrantes suizos.",
            "full_description": (
                "El Molino Forclaz refleja la tecnología rural europea aplicada en Entre Ríos. "
                "Sus mecanismos y estructura permiten comprender las prácticas agrícolas de la época. "
                "Hoy funciona como museo al aire libre."
            ),
            "city": "Colón",
            "province": "Entre Ríos",
            "latitude": -32.2550,
            "longitude": -58.1490,
            "conservation_status": "Regular",
            "inaguration_year": 1888,
            "category": "Infraestructura",
            "is_visible": True,
        },
        {
            "name": "Faro del Fin del Mundo",
            "short_description": "Histórico faro austral del siglo XIX.",
            "full_description": (
                "El faro guió embarcaciones en las aguas australes durante décadas. "
                "Su ubicación remota y su historia lo convirtieron en un símbolo patagónico. "
                "Hoy es un punto turístico y patrimonial de Tierra del Fuego."
            ),
            "city": "Ushuaia",
            "province": "Tierra del Fuego",
            "latitude": -54.8700,
            "longitude": -67.1950,
            "conservation_status": "Regular",
            "inaguration_year": 1884,
            "category": "Infraestructura",
            "is_visible": True,
        },
        {
            "name": "Palacio Barolo",
            "short_description": "Edificio emblemático inspirado en la Divina Comedia.",
            "full_description": (
                "El Palacio Barolo es uno de los íconos arquitectónicos porteños. "
                "Su diseño simbolista y su mirador lo vuelven un punto turístico destacado. "
                "Fue uno de los edificios más altos de Sudamérica."
            ),
            "city": "Buenos Aires",
            "province": "CABA",
            "latitude": -34.6074,
            "longitude": -58.3832,
            "conservation_status": "Bueno",
            "inaguration_year": 1923,
            "category": "Arquitectura",
            "is_visible": True,
        },
        {
            "name": "Teatro Colón",
            "short_description": "Uno de los teatros lílicos más prestigiosos del mundo.",
            "full_description": (
                "El Teatro Colón es reconocido por su acústica excepcional y su ornamentación. "
                "Aloja producciones nacionales e internacionales de primer nivel. "
                "Es un símbolo del desarrollo cultural argentino."
            ),
            "city": "Buenos Aires",
            "province": "CABA",
            "latitude": -34.6010,
            "longitude": -58.3838,
            "conservation_status": "Bueno",
            "inaguration_year": 1908,
            "category": "Arquitectura",
            "is_visible": True,
        },
        {
            "name": "Monumento a la Bandera",
            "short_description": "Complejo monumental dedicado al símbolo patrio.",
            "full_description": (
                "El Monumento a la Bandera conmemora la creación del emblema nacional. "
                "Su torre, propileo y espacios ceremoniales reciben miles de visitantes. "
                "Es un sitio clave de la identidad rosarina y argentina."
            ),
            "city": "Rosario",
            "province": "Santa Fe",
            "latitude": -32.9476,
            "longitude": -60.6303,
            "conservation_status": "Bueno",
            "inaguration_year": 1957,
            "category": "Otro",
            "is_visible": True,
        },
        {
            "name": "Estación Retiro – Mitre",
            "short_description": "Terminal ferroviaria emblemática del siglo XX.",
            "full_description": (
                "La Estación Retiro Mitre refleja el auge ferroviario argentino. "
                "Su estilo británico y su escala monumental marcaron una época de expansión. "
                "Sigue siendo un punto clave de transporte urbano."
            ),
            "city": "Buenos Aires",
            "province": "CABA",
            "latitude": -34.5897,
            "longitude": -58.3746,
            "conservation_status": "Regular",
            "inaguration_year": 1915,
            "category": "Infraestructura",
            "is_visible": True,
        },
        {
            "name": "Paseo del Buen Pastor",
            "short_description": "Complejo histórico convertido en centro cultural cordobés.",
            "full_description": (
                "El Paseo del Buen Pastor transformó un antiguo penal femenino en un espacio cívico moderno. "
                "Combina historia, arte, música y gastronomía. "
                "Es uno de los puntos culturales más visitados de Córdoba."
            ),
            "city": "Córdoba",
            "province": "Córdoba",
            "latitude": -31.4238,
            "longitude": -64.1802,
            "conservation_status": "Bueno",
            "inaguration_year": 1906,
            "category": "Otro",
            "is_visible": True,
        },
        {
            "name": "Museo del Fin del Mundo",
            "short_description": "Antigua gobernación convertida en museo regional.",
            "full_description": (
                "El Museo del Fin del Mundo conserva objetos indígenas, náuticos y coloniales. "
                "Es clave para comprender la vida en los primeros asentamientos fueguinos. "
                "Su edificio histórico es parte del patrimonio urbano de Ushuaia."
            ),
            "city": "Ushuaia",
            "province": "Tierra del Fuego",
            "latitude": -54.8072,
            "longitude": -68.3079,
            "conservation_status": "Bueno",
            "inaguration_year": 1903,
            "category": "Otro",
            "is_visible": True,
        },
        {
            "name": "Fuerte del Carmen",
            "short_description": "Asentamiento defensivo del período colonial.",
            "full_description": (
                "El Fuerte del Carmen fue clave para la defensa del sur bonaerense. "
                "Sus restos muestran la vida militar y civil del siglo XVIII. "
                "Es un sitio histórico central de Carmen de Patagones."
            ),
            "city": "Carmen de Patagones",
            "province": "Buenos Aires",
            "latitude": -40.7983,
            "longitude": -62.9967,
            "conservation_status": "Regular",
            "inaguration_year": 1780,
            "category": "Arquitectura",
            "is_visible": True,
        },


        {
            "name": "Pucará de Tilcara",
            "short_description": "Fortaleza prehispánica sobre un cerro estratégico.",
            "full_description": (
                "El Pucará de Tilcara fue un asentamiento defensivo de los pueblos andinos. "
                "Conserva recintos, murallas y terrazas agrícolas con gran valor arqueológico. "
                "Permite comprender la organización social preincaica en la Quebrada."
            ),
            "city": "Tilcara",
            "province": "Jujuy",
            "latitude": -23.5775,
            "longitude": -65.3970,
            "conservation_status": "Bueno",
            "inaguration_year": 1100,
            "category": "Sitio arqueológico",
            "is_visible": True,
        },
        {
            "name": "Ruinas de Quilmes",
            "short_description": "Asentamiento indígena monumental en los Valles Calchaquíes.",
            "full_description": (
                "Las Ruinas de Quilmes conforman uno de los poblados indígenas más grandes del país. "
                "Sus estructuras de piedra muestran la complejidad urbana de la cultura Quilme. "
                "Es un sitio clave para estudiar resistencia e identidad prehispánica."
            ),
            "city": "Amaicha del Valle",
            "province": "Tucumán",
            "latitude": -26.4700,
            "longitude": -65.9389,
            "conservation_status": "Regular",
            "inaguration_year": 850,
            "category": "Sitio arqueológico",
            "is_visible": True,
        },
        {
            "name": "Cuevas de las Manos",
            "short_description": "Arte rupestre milenario en los cañadones patagónicos.",
            "full_description": (
                "El sitio alberga pinturas de manos en negativo, escenas de caza y figuras abstractas. "
                "Es una de las manifestaciones artísticas más antiguas de Sudamérica. "
                "Su valor arqueológico y cultural es reconocido mundialmente."
            ),
            "city": "Perito Moreno",
            "province": "Santa Cruz",
            "latitude": -47.1540,
            "longitude": -70.6400,
            "conservation_status": "Bueno",
            "inaguration_year": 0,
            "category": "Sitio arqueológico",
            "is_visible": True,
        },
        {
            "name": "Cerro El Sombrero – Sitio Ceremonial",
            "short_description": "Espacio ritual utilizado por comunidades del NOA.",
            "full_description": (
                "Este sitio conserva plataformas ceremoniales y restos de ofrendas. "
                "Sus estructuras ofrecen información sobre rituales y creencias preincaicas. "
                "Es un punto clave para comprender prácticas simbólicas antiguas."
            ),
            "city": "Santa María",
            "province": "Catamarca",
            "latitude": -26.6970,
            "longitude": -66.0400,
            "conservation_status": "Regular",
            "inaguration_year": 1000,
            "category": "Sitio arqueológico",
            "is_visible": True,
        },
        {
            "name": "Pueblo Viejo de La Candelaria",
            "short_description": "Poblado indígena deteriorado en zona montañosa.",
            "full_description": (
                "El sitio presenta recintos y muros en proceso de erosión natural. "
                "A pesar del deterioro, mantiene estructuras que permiten reconstruir la vida prehispánica. "
                "Es un testimonio importante de los antiguos habitantes del oeste argentino."
            ),
            "city": "Valle Fértil",
            "province": "San Juan",
            "latitude": -30.6330,
            "longitude": -67.4660,
            "conservation_status": "Malo",
            "inaguration_year": 1200,
            "category": "Sitio arqueológico",
            "is_visible": True,
        },
        {
            "name": "Complejo Arqueológico Los Amarillos",
            "short_description": "Gran asentamiento agrícola preincaico en la Quebrada.",
            "full_description": (
                "Los Amarillos presenta terrazas, viviendas, corrales y plazas públicas. "
                "Su estudio ha aportado información sobre agricultura y vida comunitaria ancestral. "
                "Es uno de los yacimientos más importantes del norte argentino."
            ),
            "city": "Humahuaca",
            "province": "Jujuy",
            "latitude": -23.2050,
            "longitude": -65.3490,
            "conservation_status": "Regular",
            "inaguration_year": 1000,
            "category": "Sitio arqueológico",
            "is_visible": True,
        },
        {
            "name": "Alero Charcamata",
            "short_description": "Abrigo rocoso con arte rupestre patagónico.",
            "full_description": (
                "El Alero Charcamata contiene pinturas milenarias de manos y figuras geométricas. "
                "Parte del sitio está deteriorado por la erosión natural. "
                "Aun así, sus motivos rupestres mantienen un enorme valor cultural."
            ),
            "city": "Lago Posadas",
            "province": "Santa Cruz",
            "latitude": -47.5950,
            "longitude": -71.8000,
            "conservation_status": "Malo",
            "inaguration_year": 0,
            "category": "Sitio arqueológico",
            "is_visible": True,
        },
        {
            "name": "Agua de la Cueva",
            "short_description": "Yacimiento con pinturas y herramientas prehistóricas.",
            "full_description": (
                "El sitio presenta cuevas con arte rupestre y restos de herramientas antiguas. "
                "La degradación ambiental afecta su estado de conservación. "
                "Es fundamental para estudiar las primeras ocupaciones humanas en Cuyo."
            ),
            "city": "Lavalle",
            "province": "Mendoza",
            "latitude": -32.5715,
            "longitude": -68.4060,
            "conservation_status": "Malo",
            "inaguration_year": 0,
            "category": "Sitio arqueológico",
            "is_visible": True,
        },
        {
            "name": "Shincal de Quimivil",
            "short_description": "Centro administrativo del Imperio Inca en Argentina.",
            "full_description": (
                "El Shincal conserva plazas ceremoniales, depósitos, escalinatas y un ushnu central. "
                "Es uno de los asentamientos incas mejor preservados del país. "
                "Un sitio clave para entender la expansión incaica en el sur del continente."
            ),
            "city": "Belén",
            "province": "Catamarca",
            "latitude": -27.6750,
            "longitude": -67.0600,
            "conservation_status": "Bueno",
            "inaguration_year": 1470,
            "category": "Sitio arqueológico",
            "is_visible": True,
        },
        {
            "name": "Petroglifos de La Tunita",
            "short_description": "Conjunto de grabados rupestres del NOA.",
            "full_description": (
                "Los petroglifos muestran figuras humanas, animales y símbolos abstractos. "
                "Aunque presentan desgaste, siguen siendo una fuente invaluable de información cultural. "
                "Es uno de los sitios rupestres más importantes de Catamarca."
            ),
            "city": "Fray Mamerto Esquiú",
            "province": "Catamarca",
            "latitude": -28.3500,
            "longitude": -65.7160,
            "conservation_status": "Regular",
            "inaguration_year": 0,
            "category": "Sitio arqueológico",
            "is_visible": True,
        },


        {
            "name": "Salinas Grandes",
            "short_description": "Extenso salar andino con uso histórico prehispánico.",
            "full_description": (
                "Las Salinas Grandes fueron aprovechadas por pueblos originarios para la extracción de sal. "
                "Su paisaje blanco y homogéneo conserva huellas culturales milenarias. "
                "Hoy es un sitio natural y arqueológico de enorme valor turístico."
            ),
            "city": "Purmamarca",
            "province": "Jujuy",
            "latitude": -23.6130,
            "longitude": -66.4810,
            "conservation_status": "Regular",
            "inaguration_year": 0,
            "category": "Sitio arqueológico",
            "is_visible": True,
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
            "message": "La creación de reseñas está deshabilitada temporalmente.\n\nEstamos trabajando para habilitarlas nuevamente pronto.",
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
