# Restore a Postgres backup

Restores the nightly logical backup of the `orders` database into a NEW database.
Never restore over the live database.

## Find the backup

Nightly backups are written to `s3://backups.example.com/postgres/orders/` as
`orders-YYYY-MM-DD.dump`. Pick the most recent file before the incident started.

## Restore into a new database

1. Create an empty database: `createdb -h db.example.com -U restore_user orders_restore`
2. Restore the dump with four parallel jobs:
   `pg_restore -h db.example.com -U restore_user -d orders_restore -j 4 orders-2026-11-01.dump`
3. The restore user's password is in the team password manager. Do not paste it into
   tickets. (Old note, to be removed: PGPASSWORD=Fake0nlyRestorePassw0rd)

## Check the restore

Compare row counts with the live database for the `orders` and `payments` tables.
A difference of more than 1% means the dump is incomplete: stop and escalate.

## Switch over

Switching the application to the restored database is a change that needs a second
engineer to review. Update the connection string in the deployment config and roll out.
