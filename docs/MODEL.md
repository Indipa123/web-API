# Domain model (recorded before endpoint implementation)

Province 1 -> many Districts 1 -> many GridSubstations 1 -> many SolarInstallations 1 -> many GenerationReadings.
User has a national, provincial or district read scope. Meter ID is an installation attribute. Device authentication is a credential on that asset, not a Device entity.

Readings hold an installation foreign key, UTC timestamp, instantaneous kW, cumulative kWh and voltage. They are separate, immutable history rows. A unique (installation, timestamp) key prevents duplicate events. Latest means maximum event timestamp, not last database insert.

All asset and household data are synthetic. Substation names are illustrative, not a verified national grid inventory.

Interpretation needing comparison with the missing module guidelines: a separate infrastructure provisioning principal manages installation metadata. SLSEA users remain read-only and device credentials can only append their own readings. Installation deletion is permitted only before readings exist; history cannot be erased. The provisioning principal is configuration, not a seventh domain entity.

SQLite is a single-instance coursework choice. National-scale ingestion would require a managed database, partitions/retention, queueing, monitoring and stronger credential lifecycle controls.
