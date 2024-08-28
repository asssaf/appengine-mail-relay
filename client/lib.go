package client

import (
	"bytes"
	"crypto"
	"crypto/ed25519"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	_ "github.com/breml/rootcerts"
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

type Request struct {
	BaseUri    string
	PrivateKey ed25519.PrivateKey
	DataReader io.Reader
}

func SendRequest(request Request) error {
	data, err := io.ReadAll(request.DataReader)
	if err != nil {
		return fmt.Errorf("read failed: %w", err)
	}

	timestamp := time.Now().Unix()
	p := payload{
		Subject:   "no subject",
		Body:      string(data),
		Timestamp: timestamp,
	}

	marshalled, err := json.Marshal(p)
	if err != nil {
		return fmt.Errorf("json: %w", err)
	}

	signature, err := request.PrivateKey.Sign(nil, marshalled, crypto.Hash(0))
	if err != nil {
		return fmt.Errorf("sign: %w", err)
	}

	signed := append(signature, marshalled...)
	signedHex := hex.EncodeToString(signed)

	jsonData := fmt.Sprintf(`{"signature": "%s"}`, signedHex)

	_, err = http.Post(request.BaseUri+"/notification", "application/json", bytes.NewBuffer([]byte(jsonData)))
	if err != nil {
		return fmt.Errorf("post: %s: %w", err.Error(), httpError(err))
	}

	return nil
}
