package kafka

import (
	"fmt"
	"log"
	"os"
	"time"

	"github.com/Shopify/sarama"
)

const kafkaBootstrapServer = "KAFKA_BOOTSTRAP_SERVER"
const kafkaTopicEnvVar = "KAFKA_TOPIC"

var producer sarama.SyncProducer

func init() {
	log.Println("connecting to kafka...")
	time.Sleep(10 * time.Second) //allow kafka container to start

	brokerList := []string{os.Getenv(kafkaBootstrapServer)}
	fmt.Println("Kafka broker", brokerList)

	var err error

	producer, err = sarama.NewSyncProducer(brokerList, getAuthConfig())
	if err != nil {
		log.Fatalf("Failed to start Sarama producer %v", err)
	}
	log.Println("connected to kafka...")

}

func Send(event string) {
	topic := os.Getenv(kafkaTopicEnvVar)

	msg := &sarama.ProducerMessage{Topic: topic, Value: sarama.StringEncoder(event)}

	p, o, err := producer.SendMessage(msg)
	if err != nil {
		fmt.Println("Failed to send msg:", err)
	}
	fmt.Printf("sent message to partition %d offset %d\n", p, o)
}

func getAuthConfig() *sarama.Config {
	config := sarama.NewConfig()
	config.Net.DialTimeout = 10 * time.Second

	config.Version = sarama.V1_0_0_0
	config.Producer.Return.Successes = true
	return config
}
