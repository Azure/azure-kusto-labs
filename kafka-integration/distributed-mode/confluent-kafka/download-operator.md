
##### KAFKA INTEGRATION LABS

[Distributed Kafka ingestion with Confluent Platform](README.md)
<hr>

# 1. FOCUS: DOWNLOAD CONFLUENT OPERATOR and PREP CONF FILES
This module covers download of Confluent Operator and edits to configuration files.

# 2. Download Confluent operator, install utilities and make changes to YAML

### 2.1. Login
```
az login
```

### 2.2. Switch subscription
```
az account set --subscription <yourSubscription>
```

### 2.3. Create directory
```
mkdir -p opt/kafka/confluent-operator
cd opt/kafka/confluent-operator
```

### 2.4. Download the operator bundle for 5.5 and extract
```
wget "https://platform-ops-bin.s3-us-west-1.amazonaws.com/operator/confluent-operator-5.5.0.tar.gz"
```

### 2.5. Untar
```
tar -xvzf confluent-operator-5.5.0.tar.gz
```

### 2.6. Change directory
```
cd opt/kafka/confluent-operator
```

```
ls -al

-rw-r--r--@ 1 akhanolk  staff  63970 May  4 16:00 confluent-operator-5.5.0.tar.gz

```

### 2.7. Ensure you have k8s/helm utils
```
kubectl version
#Install with if not exists - az aks install-cli

helm version
#Install with if not exists - brew install help
```

### 2.8. Get AKS cluster admin credentials 
```
az aks get-credentials --resource-group zeus-rg --name zeus-confluent-cluster --admin
```

### 2.9. Create namespace and CRDs

1. Change dir
```
cd opt/kafka/confluent-operator/helm
```

2. Create namespace
```
kubectl create namespace operator
```

2. Create CRDs
```
kubectl apply -f ../resources/crds
```

The output is...
```
customresourcedefinition.apiextensions.k8s.io/kafkaclusters.cluster.confluent.com created
customresourcedefinition.apiextensions.k8s.io/physicalstatefulclusters.operator.confluent.cloud created
customresourcedefinition.apiextensions.k8s.io/zookeeperclusters.cluster.confluent.com created
```

### 2.10. Edit a copy of the Global configuration file for Azure<br>

During installation, Confluent Operator and Confluent Platform components are created based on parameters stored in multiple Helm Chart values.yaml files (one for Operator and one for each Confluent Platform component) and the global configuration file.<br>

Do not modify parameters in the individual component values.yaml files. If you need to adjust capacity, add a parameter, or change a parameter for a component, you modify the component section in the global configuration file. You can also adjust configuration parameters after installation using helm upgrade.<br>
```
cd opt/kafka/confluent-operator/helm/providers
cp azure.yaml zeus-azure.yaml 
```

### 2.11. Set environment variable<br>
 ```
 export VALUES_FILE="opt/kafka/confluent-operator/helm/providers/zeus-azure.yaml"
 ```

### 2.12. In zeus-azure.yaml, update cloud, region and zone<br>
Check zones with this command
```
kubectl describe nodes | grep -e "Name:" -e "failure-domain.beta.kubernetes.io/zone"
```
Result for our deployment...
```
Name:               aks-agentpool-30674491-vmss000000
                    failure-domain.beta.kubernetes.io/zone=0
Name:               aks-agentpool-30674491-vmss000001
                    failure-domain.beta.kubernetes.io/zone=1
Name:               aks-agentpool-30674491-vmss000002
                    failure-domain.beta.kubernetes.io/zone=2
Name:               aks-agentpool-30674491-vmss000003
                    failure-domain.beta.kubernetes.io/zone=3
Name:               aks-agentpool-30674491-vmss000004
                    failure-domain.beta.kubernetes.io/zone=4
Name:               aks-agentpool-30674491-vmss000005
                    failure-domain.beta.kubernetes.io/zone=0
Name:               aks-agentpool-30674491-vmss000006
                    failure-domain.beta.kubernetes.io/zone=1
Name:               aks-agentpool-30674491-vmss000007
                    failure-domain.beta.kubernetes.io/zone=2
Name:               aks-agentpool-30674491-vmss000008
                    failure-domain.beta.kubernetes.io/zone=3
```

Update the YAML as follows:

```
global:
  provider:
    name: azure
    region: westeurope
    kubernetes:
       deployment:
         ## If kubernetes is deployed in multi zone mode then specify availability-zones as appropriate
         ## If kubernetes is deployed in single availability zone then specify appropriate values
         zones:
          - "0"
          - "1"
          - "2"
          - "3"
          - "4"

```

### 2.13. Storage configuation

In the same zeus-azure.yaml, insert the global storage class name to provision SSD as we will be doing performance testing in this environment

```
  storageClassName: "managed-premium"
```

Insert just before the zookeeper section

### 2.14. Namespace conf
In the same yaml file, enable namespaced deployment, after the line you inserted in the previous step

```
operator:
  namespaced: true
```
### 2.15. Loadbalancer, resources conf
In the same yaml file, added domain, set kafka loadbalancer to true, modified the cpu and memory, and added the volumes section as shown below...

```
## Kafka Cluster
##
kafka:
  name: kafka
  replicas: 3
  resources:
    requests:
      cpu: 1000m
      memory: 4Gi
  loadBalancer:
    enabled: true
    type: internal
    domain: "zeus-confluent.com"
  tls:
    enabled: false
    fullchain: |-
    privkey: |-
    cacerts: |-
  metricReporter:
    enabled: true
  volume:
    data0: 1024Gi
```

### 2.16. Update the Confluent control center conf
Enable the load balancer and the domain..
```
  ## C3 External Access
  ##
  loadBalancer:
    enabled: true
    domain: "zeus-confluent.com"
  ##

```

# 3. The actual YAML

Is [here](../../conf/confluent-operator/zeus-azure.yaml)..

<br>

