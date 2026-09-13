"""Public response contracts used by Swagger and generated client tooling."""
from pydantic import BaseModel

class Province(BaseModel):
    id:int
    name:str
class District(Province):
    province_id:int
class Substation(Province):
    district_id:int
class Installation(Province):
    meter_id:str
    capacity_kw:float
    substation_id:int
    version:int
class Reading(BaseModel):
    id:int
    installation_id:int
    timestamp:str
    power_kw:float
    energy_kwh:float
    voltage:float
class ProvinceCollection(BaseModel):
    items:list[Province]
    total:int
class DistrictCollection(BaseModel):
    items:list[District]
    total:int
class SubstationCollection(BaseModel):
    items:list[Substation]
    total:int
class InstallationCollection(BaseModel):
    items:list[Installation]
    total:int
class ReadingPage(BaseModel):
    items:list[Reading]
    total:int
    page:int
    page_size:int
    next:str|None
    previous:str|None
class Hierarchy(BaseModel):
    province:str
    district:str
    substation:str
class Overview(BaseModel):
    installation:Installation
    hierarchy:Hierarchy
    last_known_reading:Reading|None
class CreatedInstallation(BaseModel):
    installation:Installation
    device_token:str
class Summary(BaseModel):
    district_id:int
    local_date:str
    timezone:str
    fresh_power_kw:float
    estimated_today_energy_kwh:float
    installation_count:int
    fresh_installation_count:int
    stale_or_missing_count:int
    energy_covered_installation_count:int
    freshness_minutes:int
    energy_method:str
