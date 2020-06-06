##### KAFKA INTEGRATION LABS

[Distributed Kafka ingestion with HDInsight](README.md)
<hr>


# 1. FOCUS: HELM CHART for connect cluster

This module details download and updates to the Confluent Helm Chart for the KafkaConnect Kusto sink connector deployment.

# 2. Helm Chart for KafkaConnect on AKS

## 1. Create a directory for cloning from git
```
mkdir -p ~/Work/public-git-repos/
```

```
git clone https://github.com/confluentinc/cp-helm-charts.git
```


## 2. Create a directory for just the KafkaConnect helm chart

```
mkdir -p ~/opt/kafka/connect-sink-deploy
```

## 3. Copy just the KafkaConnect helm chart

1) Change directory
```
cd ~/opt/kafka/connect-sink-deploy
```

2) Copy from git cloned local repo, just the cp-kafka-connect
```
cp -R ~/Work/public-git-repos/cp-helm-charts/charts/cp-kafka-connect .
```

3) Run tree command..
```
tree
```

4) You should see this...
```
.
└── cp-kafka-connect
    ├── Chart.yaml
    ├── README.md
    ├── templates
    │   ├── NOTES.txt
    │   ├── _helpers.tpl
    │   ├── deployment.yaml
    │   ├── jmx-configmap.yaml
    │   └── service.yaml
    └── values.yaml
```

## 4. Update the values.yaml

The YAML is [here](../conf/hdi-aks-helm-chart/values.yaml).<br>
The below is for your understanding and if you want to scale/alter.

1) Replica count update
```
replicaCount: 6
```

2) Image update
```
## Image Info
## ref: https://hub.docker.com/r/confluentinc/cp-kafka/
# image: confluentinc/cp-kafka-connect
# imageTag: 5.5.0

image: akhanolkar/kafka-connect-kusto-sink
imageTag: 0.3.4v1

## Specify a imagePullPolicy
## ref: http://kubernetes.io/docs/user-guide/images/#pre-pulling-images
imagePullPolicy: IfNotPresent

## Specify an array of imagePullSecrets.
## Secrets must be manually created in the namespace.
## ref: https://kubernetes.io/docs/concepts/containers/images/#specifying-imagepullsecrets-on-a-pod
imagePullSecrets:
```

3) As is..

```
servicePort: 8083

## Kafka Connect properties
## ref: https://docs.confluent.io/current/connect/userguide.html#configuring-workers
configurationOverrides:
  "plugin.path": "/usr/share/java,/usr/share/confluent-hub-components"
  "key.converter": "io.confluent.connect.avro.AvroConverter"
  "value.converter": "io.confluent.connect.avro.AvroConverter"
  "key.converter.schemas.enable": "false"
  "value.converter.schemas.enable": "false"
  "internal.key.converter": "org.apache.kafka.connect.json.JsonConverter"
  "internal.value.converter": "org.apache.kafka.connect.json.JsonConverter"
  "config.storage.replication.factor": "3"
  "offset.storage.replication.factor": "3"
  "status.storage.replication.factor": "3"

## Kafka Connect JVM Heap Option
heapOptions: "-Xms512M -Xmx512M"

## Additional env variables
## CUSTOM_SCRIPT_PATH is the path of the custom shell script to be ran mounted in a volume
customEnv: {}
  # CUSTOM_SCRIPT_PATH: /etc/scripts/create-connectors.sh

resources: {}
  # We usually recommend not to specify default resources and to leave this as a conscious
  # choice for the user. This also increases chances charts run on environments with little
  # resources, such as Minikube. If you do want to specify resources, uncomment the following
  # lines, adjust them as necessary, and remove the curly braces after 'resources:'.
  # limits:
  #  cpu: 100m
  #  memory: 128Mi
  # requests:
  #  cpu: 100m
  #  memory: 128Mi

## Custom pod annotations
podAnnotations: {}

## Node labels for pod assignment
## Ref: https://kubernetes.io/docs/concepts/configuration/assign-pod-node/
nodeSelector: {}

## Taints to tolerate on node assignment:
## Ref: https://kubernetes.io/docs/concepts/configuration/taint-and-toleration/
tolerations: []

## Monitoring
## Kafka Connect JMX Settings
## ref: https://kafka.apache.org/documentation/#connect_monitoring
jmx:
  port: 5555
```

4) Prometehus<br>
Set to false..

```
## Prometheus Exporter Configuration
## ref: https://prometheus.io/docs/instrumenting/exporters/
prometheus:
  ## JMX Exporter Configuration
  ## ref: https://github.com/prometheus/jmx_exporter
  jmx:
    enabled: false
    image: solsson/kafka-prometheus-jmx-exporter@sha256
    imageTag: 6f82e2b0464f50da8104acd7363fb9b995001ddff77d248379f8788e78946143
    imagePullPolicy: IfNotPresent
    port: 5556

    ## Resources configuration for the JMX exporter container.
    ## See the `resources` documentation above for details.
    resources: {}
```

5) Kafka updated with **YOUR broker list**<br>

```
## You can list load balanced service endpoint, or list of all brokers (which is hard in K8s).  e.g.:
## bootstrapServers: "PLAINTEXT://dozing-prawn-kafka-headless:9092"
kafka:
  bootstrapServers: "172.16.4.7:9092,172.16.4.5.98:9092,172.16.4.6:9092,172.16.4.4:9092"
```

6) Rest, as is

```
## If the Kafka Chart is disabled a URL and port are required to connect
## e.g. gnoble-panther-cp-schema-registry:8081
cp-schema-registry:
  url: ""

## List of volumeMounts for connect server container
## ref: https://kubernetes.io/docs/concepts/storage/volumes/
volumeMounts:
# - name: credentials
#   mountPath: /etc/creds-volume

## List of volumeMounts for connect server container
## ref: https://kubernetes.io/docs/concepts/storage/volumes/
volumes:
# - name: credentials
#   secret:
#     secretName: creds

## Secret with multiple keys to serve the purpose of multiple secrets
## Values for all the keys will be base64 encoded when the Secret is created or updated
## ref: https://kubernetes.io/docs/concepts/configuration/secret/
secrets:
  # username: kafka123
  # password: connect321

## These values are used only when "customEnv.CUSTOM_SCRIPT_PATH" is defined.
## "livenessProbe" is required only for the edge cases where the custom script to be ran takes too much time
## and errors by the ENTRYPOINT are ignored by the container
## As an example such a similar script is added to "cp-helm-charts/examples/create-connectors.sh"
## ref: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
livenessProbe:
  # httpGet:
  #   path: /connectors
  #   port: 8083
  # initialDelaySeconds: 30
  # periodSeconds: 5
  # failureThreshold: 10
```

This concludes this module.

<hr>

[Distributed Kafka ingestion with HDInsight](README.md)
