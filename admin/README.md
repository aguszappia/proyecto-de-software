# Proyecto Software - Grupo 28

## Configuración de la base de datos

### 1. Instalar PostgreSQL (macOS)

```bash
brew install postgresql@14
brew services start postgresql@14

# verificar que esta corriendo
brew services list  
```

### 2. Crear la base de datos y usuario

```bash
psql postgres

CREATE DATABASE grupo28;
CREATE USER postgres WITH PASSWORD 'admin';
GRANT ALL PRIVILEGES ON DATABASE grupo28 TO postgres;

\q
```
## run: poetry run flask --app src.web:create_app run --debug

# Comando para docker
    docker run -p 9000:9000 -p 9090:9090 \
    -e MINIO_ROOT_USER=AsOGiJwynq9UDIrN7tf5 \
    -e MINIO_ROOT_PASSWORD=Fy2p6U0THpWi27s9fy6ypH7RP1jSWRd4hFaarmPt \
    --name minio-dev \
    -v minio-data:/data \
    quay.io/minio/minio server /data --console-address ":9090"

## Configuración de variables de entorno para Google OAuth

Exportá estas variables antes de levantar la app. El redirect por defecto apunta al callback expuesto en `/api/auth/google/callback`.

```bash
export AUTHLIB_INSECURE_TRANSPORT=1
export GOOGLE_CLIENT_ID="tu-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="tu-secret"
export GOOGLE_REDIRECT_URI="http://localhost:5000/api/auth/google/callback"
```

Compartí las credenciales de Google solo por los canales privados del grupo (no las subas al repositorio).
