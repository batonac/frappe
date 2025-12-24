# Frappe Development Justfile

# Attach to flox services process-compose
attach:
    process-compose attach --unix-socket "$_FLOX_SERVICES_SOCKET"

# Show process-compose status
status:
    process-compose process list --unix-socket "$_FLOX_SERVICES_SOCKET"

# Stop all services
stop:
    process-compose process stop all --unix-socket "$_FLOX_SERVICES_SOCKET"

# Start all services
start:
    process-compose process start all --unix-socket "$_FLOX_SERVICES_SOCKET"

# Restart all services
restart:
    process-compose process restart all --unix-socket "$_FLOX_SERVICES_SOCKET"

# Stop a specific service
stop-service service:
    process-compose process stop {{service}} --unix-socket "$_FLOX_SERVICES_SOCKET"

# Start a specific service
start-service service:
    process-compose process start {{service}} --unix-socket "$_FLOX_SERVICES_SOCKET"

# Restart a specific service
restart-service service:
    process-compose process restart {{service}} --unix-socket "$_FLOX_SERVICES_SOCKET"

# View logs for a specific service
logs service:
    process-compose logs {{service}} --unix-socket "$_FLOX_SERVICES_SOCKET"
