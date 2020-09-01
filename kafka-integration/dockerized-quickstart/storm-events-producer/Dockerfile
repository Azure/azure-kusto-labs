FROM golang as build-stage
WORKDIR /app

COPY go.mod /app
COPY go.sum /app
RUN go mod download

COPY main.go /app
COPY kafka/ /app/kafka
COPY StormEvents.csv /app/StormEvents.csv

RUN cd /app && CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o producer

FROM alpine
COPY --from=build-stage /app/producer /
COPY --from=build-stage /app/StormEvents.csv /
RUN ls -lrt
CMD ["/producer"]