package main

import (
	"bytes"
	"crypto"
	"crypto/ed25519"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"time"
)

type payload struct {
	Subject   string `json:"subject"`
	Body      string `json:"body"`
	Timestamp int64  `json:"timestamp"`
}

func httpError(err error) error {
	if err == nil {
		return nil
	}
	urlErr, ok := err.(*url.Error)
	if !ok {
		return err
	}

	return urlErr.Err
}

func main() {
	baseUri := os.Getenv("BASE_URI")
	if len(baseUri) == 0 {
		log.Fatalf("BASE_URI must be set")
	}

	privateKeyHex := os.Getenv("PRIVATE_KEY")
	privateKeyBytes, err := hex.DecodeString(privateKeyHex)
	if err != nil {
		log.Fatalf("decoding private key: %w", err)
	}

	privateKey := ed25519.NewKeyFromSeed(privateKeyBytes)

	data, err := io.ReadAll(os.Stdin)
	if err != nil {
		log.Fatalf("read failed: %w", err)
	}

	timestamp := time.Now().Unix()
	p := payload{
		Subject:   "no subject",
		Body:      string(data),
		Timestamp: timestamp,
	}

	marshalled, err := json.Marshal(p)
	if err != nil {
		log.Fatalf("json: %w", err)
	}

	signature, err := privateKey.Sign(nil, marshalled, crypto.Hash(0))
	if err != nil {
		log.Fatalf("sign: %w", err)
	}

	signed := append(signature, marshalled...)
	signedHex := hex.EncodeToString(signed)

	jsonData := fmt.Sprintf(`{"signature": "%s"}`, signedHex)

	_, err = http.Post(baseUri+"/notification", "application/json", bytes.NewBuffer([]byte(jsonData)))
	if err != nil {
		log.Fatalf("post: %s: %w", err.Error(), httpError(err))
	}
}
