##### KAFKA INTEGRATION LABS

[Distributed Kafka ingestion with Confluent Platform](README.md)
<hr>

# 1. FOCUS: CREATE KAFKA TOPIC
This document details creation of a Kafka topic.<br>

# 2. Create a Kafka topic (one time activity)

1.  SSH to broker b0
```
kubectl -n operator exec -it kafka-0 bash
```

2. Create topic on broker b0 from the SSH terminal from #1
```
kafka-topics --create --zookeeper  zookeeper.operator.svc.cluster.local:2181/kafka-operator --replication-factor 3 --partitions 6 --topic crimes-topic
```

3. Set retention to 10 minutes on the topic created
```
kafka-configs --zookeeper zookeeper.operator.svc.cluster.local:2181/kafka-operator --alter --entity-type topics --entity-name crimes-topic --add-config retention.ms=600000
```

4. Port-forward on your local machine to connect to Confluent Control Center
```
kubectl -n operator port-forward controlcenter-0 12345:9021
```

5. Launch control center from where you can monitor the Kafka cluster<br>

http://http://localhost:12345/

<hr>

This concludes this module.

[Distributed Kafka ingestion with Confluent Platform](README.md)
