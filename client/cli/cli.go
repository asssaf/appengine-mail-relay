package main

import (
	"crypto/ed25519"
	"encoding/hex"
	"log"
	"os"

	"github.com/asssaf/appengine-mail-relay/client"
)

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

	request := client.Request{}
	request.DataReader = os.Stdin
	request.BaseUri = baseUri
	request.PrivateKey = privateKey

	err = client.SendRequest(request)
	if err != nil {
		log.Fatalf("SendRequest: %w", err)
	}
}
