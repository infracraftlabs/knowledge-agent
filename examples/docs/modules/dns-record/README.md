# Terraform module: dns-record

Creates one DNS record in an existing zone.

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| zone_name | string | yes | The zone, for example example.com |
| record_name | string | yes | The record, for example api |
| type | string | no (default "CNAME") | Record type |
| ttl | number | no (default 300) | Time to live in seconds |

## Outputs

| Name | Description |
|---|---|
| fqdn | The full name of the record |
