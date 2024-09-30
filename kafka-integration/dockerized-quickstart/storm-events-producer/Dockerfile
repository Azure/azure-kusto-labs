FROM golang as build-stage
WORKDIR /app

COPY go.mod /app
COPY go.sum /app
RUN go mod download

COPY main.go /app
COPY kafka/ /app/kafka
COPY client.key.pem /app/kafka/client.key.pem
COPY server.key.pem /app/kafka/server.key.pem
COPY client.cer.pem /app/kafka/client.cer.pem
COPY server.cer.pem /app/kafka/server.cer.pem

COPY StormEvents.csv /app/StormEvents.csv

RUN cd /app && CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o producer

FROM alpine
COPY --from=build-stage /app/producer /
COPY --from=build-stage /app/StormEvents.csv /
COPY --from=build-stage /app/kafka/client.key.pem /client.key.pem
COPY --from=build-stage /app/kafka/client.cer.pem /client.cer.pem
COPY --from=build-stage /app/kafka/server.key.pem /server.key.pem
COPY --from=build-stage /app/kafka/server.cer.pem /server.cer.pem
RUN ls -lrt
CMD ["/producer"]