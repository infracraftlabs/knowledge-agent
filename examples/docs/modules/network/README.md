# Terraform module: network

Creates a VPC with public and private subnets across two availability zones.

## Usage

```hcl
module "network" {
  source      = "./modules/network"
  name        = "staging"
  vpc_cidr    = "10.20.0.0/16"
  az_count    = 2
}
```

## Inputs

| Name | Type | Required | Description |
|---|---|---|---|
| name | string | yes | Prefix for every resource name |
| vpc_cidr | string | yes | CIDR block for the VPC, for example 10.20.0.0/16 |
| az_count | number | no (default 2) | Number of availability zones to use |
| enable_nat_gateway | bool | no (default true) | Create one NAT gateway per zone |

## Outputs

| Name | Description |
|---|---|
| vpc_id | ID of the VPC |
| private_subnet_ids | List of private subnet IDs |
| public_subnet_ids | List of public subnet IDs |
