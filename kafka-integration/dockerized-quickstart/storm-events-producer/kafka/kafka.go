package kafka

import (
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"io/ioutil"
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

	tlsConfig, err := NewTLSConfig("/client.cer.pem",
		"/client.key.pem",
		"/server.cer.pem")
	if err != nil {
		log.Fatal(err)
	}
	// This can be used on test server if domain does not match cert:
	tlsConfig.InsecureSkipVerify = true

	consumerConfig := sarama.NewConfig()
	consumerConfig.Net.TLS.Enable = true
	consumerConfig.Net.TLS.Config = tlsConfig
	consumerConfig.Producer.Return.Successes = true

	producer, err = sarama.NewSyncProducer(brokerList, consumerConfig)
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

// func getAuthConfig() *sarama.Config {
// 	config := sarama.NewConfig()
// 	config.Net.DialTimeout = 10 * time.Second

// 	config.Version = sarama.V1_0_0_0
// 	config.Producer.Return.Successes = true
// 	return config
// }

// NewTLSConfig generates a TLS configuration used to authenticate on server with
// certificates.
// Parameters are the three pem files path we need to authenticate: client cert, client key and CA cert.
func NewTLSConfig(clientCertFile, clientKeyFile, caCertFile string) (*tls.Config, error) {
	tlsConfig := tls.Config{}

	// Load client cert
	cert, err := tls.LoadX509KeyPair(clientCertFile, clientKeyFile)
	if err != nil {
		return &tlsConfig, err
	}
	tlsConfig.Certificates = []tls.Certificate{cert}

	// Load CA cert
	caCert, err := ioutil.ReadFile(caCertFile)
	if err != nil {
		return &tlsConfig, err
	}
	caCertPool := x509.NewCertPool()
	caCertPool.AppendCertsFromPEM(caCert)
	tlsConfig.RootCAs = caCertPool

	tlsConfig.BuildNameToCertificate()
	return &tlsConfig, err
}
