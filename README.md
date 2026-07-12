# Police Tuk-Tuk Monitoring API

| | |
|---|---|
| **Name** | Indipa Gangoda |
| **Index** | COBSCCOMP251P-028@student.nibm.lk |
| **Session** | NB6007CEM S2 |

A RESTful API built with **Node.js** and **Express** for monitoring police tuk-tuk vehicles across Sri Lanka. The API exposes reference data (provinces, districts, police stations), vehicle management, and GPS location pings reported by tracking devices fitted to each vehicle.

## What's in the Project

| File | Description |
|---|---|
| `index.js` | The Express application — all routes, auth middleware, and response mappers |
| `seed.json` | In-memory seed data: 9 provinces, 25 districts, 25 police stations, 200 vehicles, and 1,400 GPS pings |
| `package.json` | Project metadata and dependencies (Express 5) |

All data is held in memory (loaded from `seed.json`), so changes made via `POST`/`PUT`/`DELETE` are reset when the server restarts.

## Getting Started

```bash
# Install dependencies
npm install

# Start the server (defaults to port 3000, override with PORT)
npm start
```

The server listens on `http://localhost:3000` (or the port set in the `PORT` environment variable).

## Authentication

The API uses two authentication schemes:

### 1. Basic Auth (all read/management endpoints)

- **Username:** `police`
- **Password:** `nibm2024`

```bash
curl -u police:nibm2024 http://localhost:3000/vehicles
```

Missing or malformed credentials return `401 Unauthorized`; wrong credentials return `403 Forbidden`.

### 2. Device API Key (ping ingestion)

`POST /vehicles/:vehicleId/pings` is authenticated with an `X-API-Key` header instead of Basic Auth. Each vehicle has its own key in the format `key_v<zero-padded id>` (e.g. vehicle 7 → `key_v07`).

```bash
curl -X POST http://localhost:3000/vehicles/7/pings \
  -H "X-API-Key: key_v07" \
  -H "Content-Type: application/json" \
  -d '{"latitude": 6.9271, "longitude": 79.8612, "speed": 32}'
```

## API Endpoints

### Health

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check — returns status and session info |

### Provinces

| Method | Endpoint | Description |
|---|---|---|
| GET | `/provinces` | List all provinces |
| GET | `/provinces/:id` | Get a province by ID |

### Districts

| Method | Endpoint | Description |
|---|---|---|
| GET | `/districts` | List all districts (with parent province) |
| GET | `/districts/:id` | Get a district by ID |

### Stations

| Method | Endpoint | Description |
|---|---|---|
| GET | `/stations` | List all police stations (with parent district) |
| GET | `/stations/:id` | Get a station by ID |

### Vehicles

| Method | Endpoint | Description |
|---|---|---|
| GET | `/vehicles` | List all vehicles |
| POST | `/vehicles` | Register a new vehicle (`registration_number`, `device_id`, `station_id` required) — returns `201` with a `Location` header |
| GET | `/vehicles/:id` | Get a vehicle with its most recent ping (`last_ping`) |
| PUT | `/vehicles/:id` | Replace a vehicle's details |
| DELETE | `/vehicles/:id` | Delete a vehicle |

### Pings (GPS Tracking)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/vehicles/:id/pings` | Basic | List all pings for a vehicle |
| POST | `/vehicles/:vehicleId/pings` | API Key | Submit a new GPS ping (`latitude`, `longitude`, `speed` required) — returns `201` with `Location`, `ETag`, and `Last-Modified` headers |
| GET | `/vehicles/:id/pings/:pingId` | Basic | Get a single ping for a vehicle |
| GET | `/vehicles/:id/last-position` | Basic | Get a vehicle's most recent position |

## Response Codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Resource created |
| 400 | Missing required fields / duplicate vehicle ID |
| 401 | Authentication missing or malformed |
| 403 | Invalid credentials or API key |
| 404 | Resource not found |

## Example Requests

```bash
# List all provinces
curl -u police:nibm2024 http://localhost:3000/provinces

# Get vehicle 5 with its last known ping
curl -u police:nibm2024 http://localhost:3000/vehicles/5

# Register a new vehicle
curl -u police:nibm2024 -X POST http://localhost:3000/vehicles \
  -H "Content-Type: application/json" \
  -d '{"registration_number": "ABC-1234", "device_id": "dev_201", "station_id": 3}'

# Get a vehicle's last known position
curl -u police:nibm2024 http://localhost:3000/vehicles/5/last-position
```

## Tech Stack

- **Runtime:** Node.js (CommonJS)
- **Framework:** Express 5
- **Storage:** In-memory JSON seed data (`seed.json`)
