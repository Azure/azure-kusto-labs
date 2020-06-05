##### KAFKA INTEGRATION LABS

[Distributed Kafka ingestion with Confluent Platform](README.md)
<hr>

# 1. FOCUS: INSTALL ZOOKEEPER
This module covers installing zookeeper service.

# 2. Zookeeper install

### 2.1. Validate if operator is running
```
kubectl get pods -n operator
```
Output should be like this...
```
NAME                           READY   STATUS    RESTARTS   AGE
cc-operator-67b8f68f6f-zm4bq   1/1     Running   0          3m5s
```

### 2.2. Install

The command...
```
helm install zookeeper ./confluent-operator --values $VALUES_FILE --namespace operator --set zookeeper.enabled=true
```

The output..
```
NAME: zookeeper
LAST DEPLOYED: Thu May 14 14:27:51 2020
NAMESPACE: operator
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
Zookeeper Cluster Deployment

Zookeeper cluster is deployed through CR.

  1. Validate if Zookeeper Custom Resource (CR) is created

     kubectl get zookeeper -n operator | grep zookeeper

  2. Check the status/events of CR: zookeeper

     kubectl describe zookeeper zookeeper -n operator

  3. Check if Zookeeper cluster is Ready

     kubectl get zookeeper zookeeper -ojson -n operator

     kubectl get zookeeper zookeeper -ojsonpath='{.status.phase}' -n operator

  4. Update/Upgrade Zookeeper Cluster

     The upgrade can be done either through the helm upgrade or by editing the CR directly as below;

     kubectl edit zookeeper zookeeper  -n operator

```

### 2.3. Check pod creation

```
kubectl get pods -n operator
```

Output:
```
NAME                           READY   STATUS            RESTARTS   AGE
cc-operator-67b8f68f6f-s7s4v   1/1     Running           0          3m29s
zookeeper-0                    0/1     PodInitializing   0          88s
zookeeper-1                    0/1     PodInitializing   0          88s
zookeeper-2                    0/1     PodInitializing   0          88s
gaia:helm akhanolk$ 

```

Note:<br>
It might take 10 minutes or more if you configured use of premium managed disks.<br>
You might see errors such as below but should eventually see all pods running.<br>
```
Unable to mount volumes for pod "zookeeper-2_operator(c3acc27e-cd2b-4d78-ab36-2624eab61cbb)": timeout expired waiting for volumes to attach or mount for pod "operator"/"zookeeper-2". list of unmounted volumes=[data txnlog]. list of unattached volumes=[data txnlog secrets-volume sslcerts-volume shared-config-volume pod-config-volume pod-shared-workdir default-token-w9skr]
```

### 2.4. Check service creation
Note, it could take a few minutes to create the Zookeepers.

```
kubectl get svc -n operator
```

Output:
```
NAME                   TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)                                        AGE
zookeeper              ClusterIP   None           <none>        3888/TCP,2888/TCP,2181/TCP,7203/TCP,7777/TCP   2m1s
zookeeper-0-internal   ClusterIP   10.0.119.198   <none>        3888/TCP,2888/TCP,2181/TCP,7203/TCP,7777/TCP   2m4s
zookeeper-1-internal   ClusterIP   10.0.207.55    <none>        3888/TCP,2888/TCP,2181/TCP,7203/TCP,7777/TCP   2m4s
zookeeper-2-internal   ClusterIP   10.0.88.250    <none>        3888/TCP,2888/TCP,2181/TCP,7203/TCP,7777/TCP   2m4s
```


### 2.5. Validate if Zookeeper Custom Resource (CR) is created<br>

The command...
```
kubectl get zookeeper -n operator | grep zookeeper
```

Output:
```
zookeeper   2m17s
```

### 2.6. Check the status of zookeeper

```
kubectl describe zookeeper zookeeper -n operator
```

Output:
```
Name:         zookeeper
Namespace:    operator
Labels:       component=zookeeper
Annotations:  <none>
API Version:  cluster.confluent.com/v1alpha1
Kind:         ZookeeperCluster
Metadata:
  Creation Timestamp:  2020-05-14T19:27:53Z
  Finalizers:
    zookeeper.cluster.confluent.io
  Generation:        1
  Resource Version:  6922
  Self Link:         /apis/cluster.confluent.com/v1alpha1/namespaces/operator/zookeeperclusters/zookeeper
  UID:               6bed8a3d-5a67-418c-881b-5a591c24dd15
Spec:
  Image:  docker.io/confluentinc/cp-zookeeper-operator:5.5.0.0
  Init Containers:
    Args:
      until [ -f /mnt/config/pod/zookeeper/template.jsonnet ]; do echo "file not found"; sleep 10s; done; /opt/startup.sh
    Command:
      /bin/sh
      -xc
    Image:  docker.io/confluentinc/cp-init-container-operator:5.5.0.0
    Name:   init-container
  Jvm Config:
    Heap Size:  4G
  Pod Security Context:
    Fs Group:         1001
    Run As Non Root:  true
    Run As User:      1001
  Replicas:           3
  Resources:
    Requests:
      Cpu:     200m
      Memory:  512Mi
    Storage:
      Capacity:                        10Gi
      Name:                            data
      Storage Class Name:              managed-premium
      Capacity:                        10Gi
      Name:                            txnlog
      Storage Class Name:              managed-premium
  Termination Grace Period In Second:  180
Status:
  Alternate Endpoint:  zookeeper.operator.svc.cluster.local:2181
  Cluster Name:        zookeeper
  Current Replicas:    3
  Endpoints:           zookeeper.operator.svc.cluster.local:2181
  Phase:               RUNNING
  Ready Replicas:      3
  Replicas:            3
Events:
  Type    Reason   Age    From              Message
  ----    ------   ----   ----              -------
  Normal  Created  2m32s  zookeepercluster  PSC zookeeper
```


### 2.7. Check if Zookeeper cluster is ready

Command...
```
kubectl get zookeeper zookeeper -ojson -n operator
```
Output...
```
{
    "apiVersion": "cluster.confluent.com/v1alpha1",
    "kind": "ZookeeperCluster",
    "metadata": {
        "creationTimestamp": "2020-05-14T19:27:53Z",
        "finalizers": [
            "zookeeper.cluster.confluent.io"
        ],
        "generation": 1,
        "labels": {
            "component": "zookeeper"
        },
        "name": "zookeeper",
        "namespace": "operator",
        "resourceVersion": "6922",
        "selfLink": "/apis/cluster.confluent.com/v1alpha1/namespaces/operator/zookeeperclusters/zookeeper",
        "uid": "6bed8a3d-5a67-418c-881b-5a591c24dd15"
    },
    "spec": {
        "image": "docker.io/confluentinc/cp-zookeeper-operator:5.5.0.0",
        "initContainers": [
            {
                "args": [
                    "until [ -f /mnt/config/pod/zookeeper/template.jsonnet ]; do echo \"file not found\"; sleep 10s; done; /opt/startup.sh"
                ],
                "command": [
                    "/bin/sh",
                    "-xc"
                ],
                "image": "docker.io/confluentinc/cp-init-container-operator:5.5.0.0",
                "name": "init-container"
            }
        ],
        "jvmConfig": {
            "heapSize": "4G"
        },
        "podSecurityContext": {
            "fsGroup": 1001,
            "runAsNonRoot": true,
            "runAsUser": 1001
        },
        "replicas": 3,
        "resources": {
            "requests": {
                "cpu": "200m",
                "memory": "512Mi"
            },
            "storage": [
                {
                    "capacity": "10Gi",
                    "name": "data",
                    "storageClassName": "managed-premium"
                },
                {
                    "capacity": "10Gi",
                    "name": "txnlog",
                    "storageClassName": "managed-premium"
                }
            ]
        },
        "terminationGracePeriodInSecond": 180
    },
    "status": {
        "alternateEndpoint": "zookeeper.operator.svc.cluster.local:2181",
        "clusterName": "zookeeper",
        "currentReplicas": 3,
        "endpoints": "zookeeper.operator.svc.cluster.local:2181",
        "phase": "RUNNING",
        "readyReplicas": 3,
        "replicas": 3
    }
}
```

The command...
```
kubectl get zookeeper zookeeper -ojsonpath='{.status.phase}' -n operator
```

The output...
```
RUNNING
```

If you see "RUNNING", you are good to go...
<br>

This concludes this module.


<hr>


[Distributed Kafka ingestion with Confluent Platform](README.md)
