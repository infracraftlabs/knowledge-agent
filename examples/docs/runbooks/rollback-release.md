# Roll back a release

## When to roll back

Roll back when the error rate stays above 2% for five minutes after a release.

## Steps

1. Find the previous revision: `kubectl rollout history deployment/checkout -n shop`
2. Roll back: `kubectl rollout undo deployment/checkout -n shop`
3. Watch the rollout: `kubectl rollout status deployment/checkout -n shop`

## After the rollback

Open an incident using the incident template and link the release that was rolled back.
