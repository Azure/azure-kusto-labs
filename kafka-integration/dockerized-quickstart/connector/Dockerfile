# If from github releases
#FROM debezium/connect:1.2
#WORKDIR $KAFKA_HOME/connect
#RUN curl -L -O https://github.com/Azure/kafka-sink-azure-kusto/releases/download/v$KUSTO_KAFKA_SINK_VERSION/kafka-sink-azure-kusto-$KUSTO_KAFKA_SINK_VERSION-jar-with-dependencies.jar

# If from Confluent Hub
FROM confluentinc/cp-kafka-connect-base:6.2.0
ARG KUSTO_KAFKA_SINK_VERSION
RUN confluent-hub install --no-prompt microsoftcorporation/kafka-sink-azure-kusto:$KUSTO_KAFKA_SINK_VERSION
