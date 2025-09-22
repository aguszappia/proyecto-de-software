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

