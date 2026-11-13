# Demo output (real run)

- Date: 2026-11-14
- Model: qwen3:8b (local, Ollama), temperature 0
- Input files: `examples/docs/` (11 synthetic Markdown files), questions as shown below
- Command mode: AI (default); no `--access` tag, so `restricted/break-glass-access.md` is not searchable

One recorded run; language-model output varies.

```text
$ runbookqa index examples/docs
Indexed 11 file(s) into 43 section(s): runbookqa.db
Redacted at index time: 4 item(s)
  docs/modules/network/README.md: ipv4: 2
  docs/runbooks/ci-deploy-keys-to-oidc.md: key-value-secret: 1
  docs/runbooks/restore-postgres-backup.md: key-value-secret: 1
Fix the source documents above: secrets do not belong in runbooks.
Sections with text that looks like instructions to an AI (review them): 1
  docs/runbooks/clear-disk-space.md > Clear disk space on a build node > Note for automated assistants

$ runbookqa ask "How do I restore a Postgres backup to a new database?"
Answer (advisory, from the indexed documents only; check the sources before acting)

  To restore a Postgres backup into a new database, first create an empty database. [1]
  Next, restore the dump using four parallel jobs. [2]
  The restore user's password is stored in the team password manager and should not be included in tickets. [3]
  After the restore, compare row counts with the live database for the `orders` and `payments` tables. [4]
  If there is a difference of more than 1% in row counts, the dump is incomplete and the restore should be stopped. [5]
  Nightly backups are stored in the S3 bucket `s3://backups.example.com/postgres/orders/` with filenames in the format `orders-YYYY-MM-DD.dump`. [6]

Sources
  [1] docs/runbooks/restore-postgres-backup.md > Restore a Postgres backup > Restore into a new database
      "1. Create an empty database: `createdb -h db.example.com -U restore_user orders_restore`"
  [2] docs/runbooks/restore-postgres-backup.md > Restore a Postgres backup > Restore into a new database
      "2. Restore the dump with four parallel jobs: `pg_restore -h db.example.com -U restore_user -d orders_restore -j 4 orders-2026-11-01.dump`"
  [3] docs/runbooks/restore-postgres-backup.md > Restore a Postgres backup > Restore into a new database
      "The restore user's password is in the team password manager. Do not paste it into tickets."
  [4] docs/runbooks/restore-postgres-backup.md > Restore a Postgres backup > Check the restore
      "Compare row counts with the live database for the `orders` and `payments` tables."
  [5] docs/runbooks/restore-postgres-backup.md > Restore a Postgres backup > Check the restore
      "A difference of more than 1% means the dump is incomplete: stop and escalate."
  [6] docs/runbooks/restore-postgres-backup.md > Restore a Postgres backup > Find the backup
      "Nightly backups are written to `s3://backups.example.com/postgres/orders/` as `orders-YYYY-MM-DD.dump`."

Confidence: low
Mode: ai, model qwen3:8b (local, Ollama)
Access tags: none (untagged documents only)
Sections retrieved: 5
Redactions before the model call: 0 new (documents were redacted at index time)
Evidence check: 0 citation(s) and 0 claim(s) dropped
Answers come only from the indexed documents. Check the cited sources before acting.

$ runbookqa ask "Which inputs does the network module require?"
Answer (advisory, from the indexed documents only; check the sources before acting)

  The network module requires the inputs 'name' and 'vpc_cidr'. [1]

Sources
  [1] docs/modules/network/README.md > Terraform module: network > Inputs
      "| Name | Type | Required | Description |
       |---|---|---|---|
       | name | string | yes | Prefix for every resource name |
       | vpc_cidr | string | yes | CIDR block for the VPC, for example [REDACTED:ipv4]/16 |"

Confidence: low
Mode: ai, model qwen3:8b (local, Ollama)
Access tags: none (untagged documents only)
Sections retrieved: 5
Redactions before the model call: 0 new (documents were redacted at index time)
Evidence check: 1 citation(s) and 1 claim(s) dropped
Answers come only from the indexed documents. Check the cited sources before acting.

$ runbookqa ask "How do I upgrade the Kafka cluster to a new version?"
Answer (advisory, from the indexed documents only; check the sources before acting)

  The indexed documents don't cover this.

Confidence: low
Mode: ai, model qwen3:8b (local, Ollama)
Access tags: none (untagged documents only)
Sections retrieved: 5
Redactions before the model call: 0 new (documents were redacted at index time)
Evidence check: 0 citation(s) and 0 claim(s) dropped
Answers come only from the indexed documents. Check the cited sources before acting.
```
