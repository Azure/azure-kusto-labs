package main

import (
	"encoding/csv"
	"io"
	"log"
	"os"
	"strings"
	"time"

	"github.com/abhirockzz/events-producer/kafka"
)

const defaultSourceFile = "StormEvents.csv"

func main() {
	log.Println("starting event producer...")

	mapping := map[int]string{0: "StartTime", 1: "EndTime", 3: "EventId", 4: "State", 5: "EventType", 12: "Source"}

	sourceFile := os.Getenv("SOURCE_FILE")
	if sourceFile == "" {
		sourceFile = defaultSourceFile
	}
	f, err := os.Open(sourceFile)
	if err != nil {
		log.Fatal("unable to open file ", err)
	}
	log.Println("opened source file")

	defer f.Close()

	r := csv.NewReader(f)

	for {
		line, err := r.Read()
		if err == io.EOF {
			log.Println("end of file")
			return
		}
		if err != nil {
			log.Println("error reading line", err)
			continue
		}

		var output []string
		b := &strings.Builder{}
		w := csv.NewWriter(b)

		for i, v := range line {
			_, ok := mapping[i]
			if ok {
				output = append(output, v)
			}
		}

		err = w.Write(output)
		w.Flush()
		if err != nil {
			log.Println("Write failed", err)
		}
		stormEvent := b.String()
		log.Println("event ", stormEvent)
		kafka.Send(stormEvent)
		time.Sleep(3 * time.Second) //on purpose
	}
}
