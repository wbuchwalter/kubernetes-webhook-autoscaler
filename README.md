# Kubernetes-webhook-autoscaler

### Running locally
```
$ docker build -t autoscaler .
$ ./devenvh.sh
#in the container
$ python main.py [arguments]
```


## Full List of Options

```
$ python main.py [options]
```
- --kubeconfig: Path to kubeconfig YAML file. Leave blank if running in Kubernetes to use [service account](http://kubernetes.io/docs/user-guide/service-accounts/).
- --scale-out-webhook: URI to be called when a scaling out need is detected by the autoscaler
- --scale-in-webhook: URI to be called when a scaling in need is detected by the autoscaler
- --pool-name-regex: Regex used to identify agents in the pool(s), default to `agent`. The regex should not match masters
- --drain: Wether the autoscaler should drain and cordon nodes before passing them to the scale-in webhook.
- --sleep: Time (in seconds) to sleep between scaling loops (to be careful not to run into AWS API limits)
- --slack-hook: Optional [Slack incoming webhook](https://api.slack.com/incoming-webhooks) for scaling notifications
- -v: Sets the verbosity. Specify multiple times for more log output, e.g. `-vvv`
- --debug: Do not catch errors. Explicitly crash instead.
- --ignore-pools: Names of the pools that the autoscaler should ignore, separated by a comma.
- --spare-agents: Number of agent per pool that should always stay up (default is 1)
- --idle-threshold: Maximum duration (in seconds) an agent can stay idle before being deleted
- --over-provision: Number of extra agents to create when scaling up, default to 0.
