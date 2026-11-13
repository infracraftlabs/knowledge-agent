# Replace CI deploy keys with OIDC

Long-lived cloud keys stored as CI secrets are replaced by short-lived credentials
issued through OpenID Connect (OIDC).

## Why

A stored key works until someone revokes it. An OIDC token expires within an hour and
is bound to one repository and branch.

## Steps

1. In the cloud account `123456789012`, create a role that trusts the CI provider's
   OIDC issuer, limited to the repository `example-org/web` and the branch `main`.
2. Add `permissions: id-token: write` to the deploy job in the workflow file.
3. Replace the step that reads the stored key with the provider's official
   credentials action, pointing at the new role.
4. Run one deploy and confirm it succeeds.
5. Delete the old key from the CI secrets and deactivate it in the cloud account.

## Rollback

Keep the old key deactivated, not deleted, for seven days. Reactivate it only if the
OIDC deploy fails and the fix will take longer than one working day.
