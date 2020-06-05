##### KAFKA INTEGRATION LABS

[Distributed Kafka ingestion with Confluent Platform](README.md)
<hr>

# 1. FOCUS: INSTALL CONFLUENT OPERATOR
This module covers installing Confluent operator on AKS.

# 2. Confluent operator install

### 2.1. Command:
```
helm install operator ./confluent-operator --values $VALUES_FILE --namespace operator --set operator.enabled=true
```

Output:
```
NAME: operator
LAST DEPLOYED: Thu May 14 14:25:53 2020
NAMESPACE: operator
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
The Confluent Operator

The Confluent Operator interacts with kubernetes API to create statefulsets resources. The Confluent Operator runs three
controllers, two component specific controllers for kubernetes by providing components specific Custom Resource
Definition (CRD) (for Kafka and Zookeeper) and one controller for creating other statefulsets resources.

  1. Validate if Confluent Operator is running.

  kubectl get pods -n operator | grep cc-operator

  2. Validate if custom resource definition (CRD) is created.

  kubectl get crd | grep confluent


```

### 2.2. Validate if Confluent operator is running.
The command-
```
kubectl get pods -n operator | grep cc-operator
```

The output should be-
```
cc-operator-67b8f68f6f-s7s4v   1/1     Running   0          35s
```

### 2.3. Validate if custom resource definition (CRD) is created
The command-
```
kubectl get crd | grep confluent
```
The output should be like this-
```
kafkaclusters.cluster.confluent.com                 2020-05-14T19:07:43Z
physicalstatefulclusters.operator.confluent.cloud   2020-05-14T19:07:43Z
zookeeperclusters.cluster.confluent.com             2020-05-14T19:07:44Z
```

This concludes this module.


[Distributed Kafka ingestion with Confluent Platform](README.md)
<hr>
