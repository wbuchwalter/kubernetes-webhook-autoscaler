# logger

This is a simple example, this application will listen from the autoscaler and repeat the payload

There are two endpoints :
* http://localhost/in
* http://localhost/out

### Example Output

```bash
...
 * Serving Flask app "main"
 * Running on http://0.0.0.0:5000/ (Press CTRL+C to quit)
Scale Out Endpoint hit :
[{'name': 'worker', 'current_agent_count': 6, 'desired_agent_count': 11}]
172.17.0.3 - - [11/Jan/2018 20:14:53] "POST /out HTTP/1.1" 200 -
...
172.17.0.3 - - [11/Jan/2018 20:19:51] "POST /in HTTP/1.1" 200 -
Scale In Endpoint hit :
[{'name': 'worker', 'current_agent_count': 6, 'desired_agent_count': 2, 'target_nodes': ['ju-cluster-worker-0', 'ju-cluster-worker-1', 'ju-cluster-worker-4', 'ju-cluster-worker-5']}]
```

### Deploying in a cluster using Helm

**You first need to deploy the main autoscaler part*

```bash
helm install ./chart/. --name k8s-wh-as-logger
```

### Running it locally (default is port 5000)
```bash
$ make build-run
```
