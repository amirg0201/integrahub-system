# InteraHub — Sistema de Integración de Órdenes

Sistema modular de procesamiento de órdenes construido con arquitectura de eventos, microservicios y procesamiento usando RabbitMQ. Incluye API Gateway, múltiples workers especializados y gestión de datos con PostgreSQL.

## 📋 Descripción General

IntegraHub es una plataforma de orquestación **Order-to-Cash** que implementa:
- ✅ **API Gateway REST** segura con autenticación JWT
- ✅ **Message Broker** (RabbitMQ) para mensajería asíncrona
- ✅ **Base de Datos PostgreSQL** para persistencia
- ✅ **Workers especializados** para procesamiento de órdenes, notificaciones e inventario
- ✅ **Portal Frontend** interactivo para demostración
- ✅ **Servicio de Integración Legada** con ingesta de archivos CSV
- ✅ **Monitoreo visual** con Adminer

---

## 🚀 Inicio Rápido (Docker - Recomendado)

### Requisitos Previos
- Docker y Docker Compose instalados
- Puerto 8000, 8080, 5672, 15672 disponibles

### Instalación y Ejecución

```bash
# Clonar repositorio y navegar a la carpeta
cd integrahub-system

# Construir e iniciar todos los servicios
docker compose up --build

# O en segundo plano
docker compose up --build -d
```

### Verificar que Todo Está Funcionando

**API Gateway & Frontend Portal:**
- Accede a http://localhost:8000/
- Deberías ver el portal interactivo

**RabbitMQ Management UI:**
- Accede a http://localhost:15672/
- Credenciales: `user` / `password`

**Adminer (Base de Datos):**
- Accede a http://localhost:8080/
- Servidor: `postgres`
- Usuario: `admin`
- Contraseña: `secretpassword`
- Base de datos: `integrahub`

**Health Check (API):**
- Accede a http://localhost:8000/health/
- Verifica el estado de todos los componentes

---

## 🏗️ Arquitectura de Servicios

### 1. **RabbitMQ** (Message Broker)
- **Puerto AMQP:** 5672
- **Management UI:** 15672 (user/password)
- Colas implementadas:
  - `order.processing` - Procesamiento de órdenes
  - `order.processing.retry` - Reintentos
  - `order.processing.dlq` - Dead Letter Queue (errores)

### 2. **PostgreSQL** (Base de Datos)
- **Puerto:** 5432
- **Usuario:** admin
- **Contraseña:** secretpassword
- **Base de datos:** integrahub
- Almacena órdenes, usuarios y datos de transacciones

### 3. **API Gateway** (FastAPI)
- **Puerto:** 8000
- **Función:** Puerta de entrada a todos los servicios
- Endpoints principales:
  - `POST /orders/` - Crear nueva orden
  - `GET /orders/{order_id}` - Consultar orden
  - `GET /health/` - Estado del sistema
  - `GET /` - Portal Frontend

### 4. **Inventory Service Worker**
- Procesa órdenes de inventario
- Valida disponibilidad de stock
- Implementa idempotencia y DLQ
- Se conecta a RabbitMQ y PostgreSQL

### 5. **Notification Service Worker**
- Envía notificaciones a través de Slack
- Procesa eventos de órdenes completadas
- Configurable con webhook de Slack

### 6. **Legacy Service (File Watcher)**
- **Función:** Ingesta de archivos CSV legacy
- **Directorios:**
  - `/inbox` - Archivos pendientes de procesar
  - `/processed` - Archivos procesados exitosamente
  - `/error` - Archivos con errores
- Observa cambios en archivos y actualiza la BD

### 7. **Analytics Service Worker**
- Recolecta métricas y estadísticas en tiempo real
- Procesa eventos de RabbitMQ
- Almacena datos agregados en PostgreSQL

### 8. **Adminer** (Admin UI)
- **Puerto:** 8080
- Herramienta visual para gestionar PostgreSQL
- Sin necesidad de línea de comandos

---

## 💻 Desarrollo Local (Sin Docker)

Si prefieres ejecutar la API Gateway localmente:

### Requisitos
- Python 3.9+
- pip

### Instalación

```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno
# En Windows:
.venv\Scripts\activate
# En Linux/Mac:
source .venv/bin/activate

# Instalar dependencias
pip install -r api-gateway/requirements.txt

# Ejecutar con hot-reload
DEV_AUTH_BYPASS=1 uvicorn api-gateway.main:app --reload --port 8000
```

**Nota:** Sin Docker, necesitarás tener RabbitMQ y PostgreSQL corriendo en tu máquina.

---

## 🧪 Tests y Validación

### Ejecutar Tests
```bash
pytest
```

### Flujo de Prueba Manual
1. Inicia todos los servicios con Docker Compose
2. Accede a http://localhost:8000/
3. Crea una orden desde el portal
4. Verifica el procesamiento en RabbitMQ Management (15672)
5. Consulta los datos en Adminer (8080)

---

## 📁 Estructura del Proyecto

```
integrahub-system/
├── api-gateway/              # FastAPI Gateway + Frontend hosting
│   ├── main.py              # Punto de entrada
│   ├── auth.py              # Autenticación JWT
│   ├── requirements.txt      # Dependencias Python
│   ├── core/                # Módulos centrales
│   │   ├── security.py      # Lógica de seguridad
│   │   └── rabbitmq.py      # Conexión a RabbitMQ
│   ├── models/              # Modelos de datos
│   │   └── orders.py        # Modelo de órdenes
│   └── routers/             # Endpoints
│       ├── health.py        # Health check
│       └── orders.py        # Operaciones de órdenes
├── workers/                 # Servicios asíncrónos
│   ├── inventory-service/   # Validación de stock
│   ├── notification-service/# Notificaciones Slack
│   ├── legacy-service/      # Ingesta CSV
│   └── analytics-service/   # Métricas y análisis
├── frontend-portal/         # Portal web (HTML/JS)
├── tests/                   # Suite de pruebas
├── docker-compose.yml       # Orquestación de servicios
├── inbox/                   # Archivos CSV a procesar
├── processed/               # Archivos procesados
├── error/                   # Archivos con error
└── docs/                    # Documentación

```

---

## 🔧 Configuración Avanzada

### Variables de Entorno
Crea un archivo `.env` en la raíz (opcional, usa valores por defecto):

```env
# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_DEFAULT_USER=user
RABBITMQ_DEFAULT_PASS=password

# PostgreSQL
DB_HOST=postgres
DB_USER=admin
DB_PASS=secretpassword
DB_NAME=integrahub

# Slack (para notificaciones)
SLACK_URL_SECRETA=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Control de Servicios

```bash
# Ver logs en tiempo real
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f api-gateway

# Detener todos los servicios
docker compose down

# Detener y eliminar volúmenes (PELIGRO: borra datos de BD)
docker compose down -v
```

---

## ✅ Checklist para Defensa

- [ ] `docker compose up --build -d` ejecuta sin errores
- [ ] Portal funciona en http://localhost:8000/
- [ ] RabbitMQ Management visible en http://localhost:15672/
- [ ] `/health` retorna estado de componentes
- [ ] DLQ y reintentos funcionales en RabbitMQ
- [ ] Base de datos accessible en http://localhost:8080/ (Adminer)
- [ ] Tests pasan con `pytest`

---

## 📞 Soporte y Troubleshooting

### Los servicios no inician
```bash
# Verifica que los puertos estén disponibles
netstat -an | findstr :8000  # Windows
lsof -i :8000               # Linux/Mac

# Reconstruye los contenedores
docker compose down -v
docker compose up --build
```

### Base de datos no conecta
```bash
# Verifica salud de PostgreSQL
docker compose ps

# Reinicia el servicio
docker compose restart postgres
```

### RabbitMQ sin conexión
```bash
# Verifica los logs
docker compose logs rabbitmq

# Reinicia RabbitMQ
docker compose restart rabbitmq
```

---

## 📚 Recursos Adicionales

- **API Docs Postman:** [IntegraHub Api.postman_collection.json](./IntegraHub%20Api.postman_collection.json)
- **Datos de Prueba:** [datosDePrueba.csv](./datosDePrueba.csv)
- **Documentación Técnica:** [/docs/](./docs/)

---

**Última actualización:** Enero 2026
