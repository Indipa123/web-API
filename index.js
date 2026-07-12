const express = require('express');
const seed = require('./seed.json');

const app = express();
const port = process.env.PORT || 3000;
const basicAuthRealm = 'Basic realm="Police API"';

const findById = (items, id) => items.find((item) => item.id === Number(id));

const sendById = (res, items, id) => {
  const item = findById(items, id);

  if (!item) {
    return res.status(404).json({ error: 'Not found' });
  }

  return res.json(item);
};

const toProvinceResponse = (province) => ({
  province_id: province.id,
  name: province.name,
});

const toDistrictResponse = (district) => ({
  district_id: district.id,
  name: district.name,
  province_id: district.province_id,
});

const toStationResponse = (station) => ({
  station_id: station.id,
  name: station.name,
  district_id: station.district_id,
});

const toVehicleResponse = (vehicle) => ({
  vehicle_id: vehicle.id,
  reg_number: vehicle.registration_number,
  device_id: vehicle.device_id,
  station_id: vehicle.station_id,
});

const toPingResponse = (ping) => ({
  ping_id: ping.id,
  vehicle_id: ping.vehicle_id,
  timestamp: ping.timestamp,
  lat: ping.latitude ?? ping.latitute,
  lng: ping.longitude,
  speed: ping.speed ?? null,
});

const toPositionResponse = (ping) => ({
  vehicle_id: ping.vehicle_id,
  timestamp: ping.timestamp,
  lat: ping.latitude ?? ping.latitute,
  lng: ping.longitude,
  speed: ping.speed ?? null,
});

const toVehicleCompositeResponse = (vehicle) => {
  const lastPing = seed.pings
    .filter((ping) => ping.vehicle_id === vehicle.id)
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))[0];

  return {
    ...toVehicleResponse(vehicle),
    last_ping: lastPing ? toPingResponse(lastPing) : null,
  };
};

const createDeviceKey = (vehicleId) => `key_v${String(vehicleId).padStart(2, '0')}`;

const deviceKeys = seed.vehicles.reduce((keys, vehicle) => {
  keys[vehicle.id] = createDeviceKey(vehicle.id);
  return keys;
}, {});

const nextId = (items) => Math.max(0, ...items.map((item) => item.id)) + 1;

const hasRequiredFields = (body, fields) => fields.every((field) => body[field] !== undefined);

const basicAuth = (req, res, next) => {
  const authHeader = req.get('Authorization');

  if (!authHeader) {
    res.set('WWW-Authenticate', basicAuthRealm);
    return res.status(401).json({ error: 'Authentication required' });
  }

  const [scheme, encodedCredentials] = authHeader.split(' ');

  if (scheme !== 'Basic' || !encodedCredentials) {
    res.set('WWW-Authenticate', basicAuthRealm);
    return res.status(401).json({ error: 'Invalid authentication header' });
  }

  let decodedCredentials;

  try {
    decodedCredentials = Buffer.from(encodedCredentials, 'base64').toString('utf8');
  } catch (_) {
    res.set('WWW-Authenticate', basicAuthRealm);
    return res.status(401).json({ error: 'Invalid authentication header' });
  }

  const separatorIndex = decodedCredentials.indexOf(':');

  if (separatorIndex === -1) {
    res.set('WWW-Authenticate', basicAuthRealm);
    return res.status(401).json({ error: 'Invalid authentication header' });
  }

  const username = decodedCredentials.slice(0, separatorIndex);
  const password = decodedCredentials.slice(separatorIndex + 1);

  if (username !== 'police' || password !== 'nibm2024') {
    return res.status(403).json({ error: 'Forbidden' });
  }

  return next();
};

const deviceApiKeyAuth = (req, res, next) => {
  const vehicle = findById(seed.vehicles, req.params.vehicleId);

  if (!vehicle) {
    return res.status(404).json({ error: 'Vehicle not found' });
  }

  const apiKey = req.get('X-API-Key');

  if (!apiKey) {
    return res.status(401).json({ error: 'API key required' });
  }

  if (apiKey !== deviceKeys[vehicle.id]) {
    return res.status(403).json({ error: 'Forbidden' });
  }

  req.vehicle = vehicle;
  return next();
};

app.use(express.json());

app.get('/', basicAuth, (req, res) => {
  res.json({
    status: 'ok',
    session: 'NB6007CEM S2',
  });
});

app.get('/provinces', basicAuth, (req, res) => {
  res.json(seed.provinces.map(toProvinceResponse));
});

app.get('/provinces/:id', basicAuth, (req, res) => {
  const province = findById(seed.provinces, req.params.id);

  if (!province) {
    return res.status(404).json({ error: 'Not found' });
  }

  return res.json(toProvinceResponse(province));
});

app.get('/districts', basicAuth, (req, res) => {
  res.json(seed.districts.map(toDistrictResponse));
});

app.get('/districts/:id', basicAuth, (req, res) => {
  const district = findById(seed.districts, req.params.id);

  if (!district) {
    return res.status(404).json({ error: 'Not found' });
  }

  return res.json(toDistrictResponse(district));
});

app.get('/stations', basicAuth, (req, res) => {
  res.json(seed.stations.map(toStationResponse));
});

app.get('/stations/:id', basicAuth, (req, res) => {
  const station = findById(seed.stations, req.params.id);

  if (!station) {
    return res.status(404).json({ error: 'Not found' });
  }

  return res.json(toStationResponse(station));
});

app.get('/vehicles', basicAuth, (req, res) => {
  res.json(seed.vehicles.map(toVehicleResponse));
});

app.post('/vehicles', basicAuth, (req, res) => {
  const requiredFields = ['registration_number', 'device_id', 'station_id'];

  if (!hasRequiredFields(req.body, requiredFields)) {
    return res.status(400).json({ error: 'Missing required vehicle fields' });
  }

  const vehicle = {
    id: req.body.id === undefined ? nextId(seed.vehicles) : Number(req.body.id),
    registration_number: req.body.registration_number,
    device_id: req.body.device_id,
    station_id: Number(req.body.station_id),
  };

  if (findById(seed.vehicles, vehicle.id)) {
    return res.status(400).json({ error: 'Vehicle id already exists' });
  }

  seed.vehicles.push(vehicle);
  deviceKeys[vehicle.id] = createDeviceKey(vehicle.id);

  return res
    .status(201)
    .location(`/vehicles/${vehicle.id}`)
    .json(vehicle);
});

app.get('/vehicles/:id', basicAuth, (req, res) => {
  const vehicle = findById(seed.vehicles, req.params.id);

  if (!vehicle) {
    return res.status(404).json({ error: 'Not found' });
  }

  return res.json(toVehicleCompositeResponse(vehicle));
});

app.put('/vehicles/:id', basicAuth, (req, res) => {
  const vehicleIndex = seed.vehicles.findIndex((vehicle) => vehicle.id === Number(req.params.id));

  if (vehicleIndex === -1) {
    return res.status(404).json({ error: 'Vehicle not found' });
  }

  const requiredFields = ['registration_number', 'device_id', 'station_id'];

  if (!hasRequiredFields(req.body, requiredFields)) {
    return res.status(400).json({ error: 'Missing required vehicle fields' });
  }

  const replacement = {
    id: Number(req.params.id),
    registration_number: req.body.registration_number,
    device_id: req.body.device_id,
    station_id: Number(req.body.station_id),
  };

  seed.vehicles[vehicleIndex] = replacement;
  deviceKeys[replacement.id] = createDeviceKey(replacement.id);

  return res.json(replacement);
});

app.delete('/vehicles/:id', basicAuth, (req, res) => {
  const vehicleIndex = seed.vehicles.findIndex((vehicle) => vehicle.id === Number(req.params.id));

  if (vehicleIndex === -1) {
    return res.status(404).json({ error: 'Vehicle not found' });
  }

  const [deletedVehicle] = seed.vehicles.splice(vehicleIndex, 1);
  delete deviceKeys[deletedVehicle.id];

  return res.json(deletedVehicle);
});

app.get('/vehicles/:id/pings', basicAuth, (req, res) => {
  const vehicle = findById(seed.vehicles, req.params.id);

  if (!vehicle) {
    return res.status(404).json({ error: 'Vehicle not found' });
  }

  return res.json(
    seed.pings
      .filter((ping) => ping.vehicle_id === vehicle.id)
      .map(toPingResponse),
  );
});

app.post('/vehicles/:vehicleId/pings', deviceApiKeyAuth, (req, res) => {
  if (!hasRequiredFields(req.body, ['latitude', 'longitude', 'speed'])) {
    return res.status(400).json({ error: 'Missing required ping fields' });
  }

  const ping = {
    id: nextId(seed.pings),
    vehicle_id: req.vehicle.id,
    latitude: Number(req.body.latitude),
    longitude: Number(req.body.longitude),
    speed: Number(req.body.speed),
    timestamp: new Date().toISOString(),
  };

  seed.pings.push(ping);

  return res
    .status(201)
    .location(`/vehicles/${req.vehicle.id}/pings/${ping.id}`)
    .set('ETag', `"${ping.id}"`)
    .set('Last-Modified', new Date(ping.timestamp).toUTCString())
    .json(ping);
});

app.get('/vehicles/:id/pings/:pingId', basicAuth, (req, res) => {
  const vehicle = findById(seed.vehicles, req.params.id);

  if (!vehicle) {
    return res.status(404).json({ error: 'Vehicle not found' });
  }

  const ping = seed.pings.find(
    (item) => item.vehicle_id === vehicle.id && item.id === Number(req.params.pingId),
  );

  if (!ping) {
    return res.status(404).json({ error: 'Ping not found' });
  }

  return res.json(ping);
});

app.get('/vehicles/:id/last-position', basicAuth, (req, res) => {
  const lastPosition = seed.pings
    .filter((ping) => ping.vehicle_id === Number(req.params.id))
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))[0];

  if (!lastPosition) {
    return res.status(404).json({ error: 'Ping not found' });
  }

  return res.json(toPositionResponse(lastPosition));
});

app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});
