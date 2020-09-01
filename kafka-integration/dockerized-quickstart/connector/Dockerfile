FROM debezium/connect:1.2
WORKDIR $KAFKA_HOME/connect
ARG KUSTO_KAFKA_SINK_VERSION
RUN curl -L -O https://github.com/Azure/kafka-sink-azure-kusto/releases/download/v$KUSTO_KAFKA_SINK_VERSION/kafka-sink-azure-kusto-$KUSTO_KAFKA_SINK_VERSION-jar-with-dependencies.jar
