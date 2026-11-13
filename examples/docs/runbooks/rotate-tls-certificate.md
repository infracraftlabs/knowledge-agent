# Rotate a TLS certificate

Use this when the certificate for `app.example.com` is close to expiry or has been
exposed. Expected time: 20 minutes. Owner: platform on-call.

## Before you start

- Check the current expiry: `openssl s_client -connect app.example.com:443 -servername app.example.com </dev/null | openssl x509 -noout -enddate`
- Confirm cert-manager is healthy: `kubectl get pods -n cert-manager`

## Steps

1. Delete the old certificate secret so cert-manager issues a new one:
   `kubectl delete secret app-example-com-tls -n web`
2. Watch the Certificate resource until it reports Ready:
   `kubectl get certificate app-example-com -n web -w`
3. Restart the ingress controller pods only if they still serve the old certificate.

## Verify

The new expiry date must be at least 60 days in the future. Check it with the
`openssl` command from "Before you start".

## Rollback

If issuance fails, restore the previous secret from the backup taken in step 1 of the
weekly backup job and open an incident using the incident template.
