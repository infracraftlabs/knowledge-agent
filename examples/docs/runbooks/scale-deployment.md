# Scale a deployment

## Manual scaling

To add replicas quickly during a traffic spike:
`kubectl scale deployment checkout -n shop --replicas=6`

Manual scaling is temporary: the HorizontalPodAutoscaler will change the replica count
again within a few minutes if one exists.

## Change the autoscaler limits

Edit `maxReplicas` in `deploy/checkout/hpa.yaml` and open a pull request. The default
limits are `minReplicas: 2` and `maxReplicas: 10`.

## Check capacity first

Before scaling above 10 replicas, check that the node pool has room:
`kubectl describe nodes | grep -A 5 "Allocated resources"`
If nodes are full, scale the node pool first or pods will stay Pending.
