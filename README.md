# Kubernetes-webhook-autoscaler

Kubernetes autoscaler using webhooks.

This works in two pieces :
- The Kubernetes autoscaler part is interacting with the API of the cluster and sending webhooks 
- The 'client' part is receiving the hooks and triggering the scaling. You can find example of this part inside the [examples](/examples) folder.

## Full List of Options

```bash
$ python main.py [options]
```

| Option | Description | Default |
|---|---|---|
| `--kubeconfig` | Path to kubeconfig YAML file. Leave blank if running in Kubernetes to use [service account](http://kubernetes.io/docs/user-guide/service-accounts/) | |
| `--scale-out-webhook` | URI to be called when a scaling out need is detected by the autoscaler | |
| `--scale-in-webhook` | URI to be called when a scaling in need is detected by the autoscaler | |
| `--pool-name-regex` | Regex used to identify agents in the pool(s), the regex should not match masters | agent |
| `--drain` | Wether the autoscaler should drain and cordon nodes before passing them to the scale-in webhook | |
| `--sleep` | Time (in seconds) to sleep between scaling loops | 60|
| `-v` | Sets the verbosity. Specify multiple times for more log output, e.g. `-vvv` | |
| `--debug` | Do not catch errors. Explicitly crash instead | |
| `--ignore-pools` | Names of the pools that the autoscaler should ignore, separated by a comma | |
| `--spare-agents` | Number of agent per pool that should always stay up | 1 |
| `--idle-threshold` | Maximum duration (in seconds) an agent can stay idle before being deleted | |
| `--over-provision` | Number of extra agents to create when scaling up | 0 |

### Deploy it in a K8s cluster using Helm

```bash
helm install ./helm-chart/. --name k8s-wh-as \
    --set options.scaleoutwebhook=<SCALE-OUT-URL>,options.scaleinwebhook=<SCALE-OUT-URL>,options.poolnameregex=<REGEX-NODES-TO-WATCH> stable/kubernetes-webhook-autoscaler
```

### Running locally

```bash
$ make build-run
#in the container
$ python main.py [arguments]
```