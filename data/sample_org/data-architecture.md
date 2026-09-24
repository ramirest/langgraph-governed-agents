# Meridian Transit Authority — Data architecture

## Systems of record

Four systems hold operational data: the fare-collection platform (vendor,
on-premise), the vehicle telemetry service (vendor, cloud), the scheduling
system (in-house, on-premise) and the incident log (a shared spreadsheet).

## Integration

Integration is point-to-point. Eleven scheduled jobs move data between the four
systems; nine of them are cron entries on a single virtual machine that is not
in the configuration-management inventory. There is no message broker and no
integration catalogue.

## Warehouse

A PostgreSQL warehouse serves reporting. It is loaded nightly. Transformations
are SQL scripts stored in a shared network folder; four of them have no author
recorded in version control because they predate the repository.

## Lineage

Lineage is not recorded anywhere. Tracing a figure in the monthly ridership
report back to a source system is done by asking the analyst who built it.
