package main

import (
	"crypto/ed25519"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"log"
	"os"
	"time"

	"github.com/emersion/go-sasl"
	"github.com/emersion/go-smtp"

	"github.com/asssaf/appengine-mail-relay/client"
)

// The Backend implements SMTP server methods.
type Backend struct{}

// NewSession is called after client greeting (EHLO, HELO).
func (bkd *Backend) NewSession(c *smtp.Conn) (smtp.Session, error) {
	return &Session{}, nil
}

// A Session is returned after successful login.
type Session struct{}

// AuthMechanisms returns a slice of available auth mechanisms; only PLAIN is
// supported in this example.
func (s *Session) AuthMechanisms() []string {
	return []string{sasl.Plain}
}

// Auth is the handler for supported authenticators.
func (s *Session) Auth(mech string) (sasl.Server, error) {
	return sasl.NewPlainServer(func(identity, username, password string) error {
		if username != "username" || password != "password" {
			return errors.New("Invalid username or password")
		}
		return nil
	}), nil
}

func (s *Session) Mail(from string, opts *smtp.MailOptions) error {
	log.Println("Mail from:", from)
	return nil
}

func (s *Session) Rcpt(to string, opts *smtp.RcptOptions) error {
	log.Println("Rcpt to:", to)
	return nil
}

func (s *Session) Data(r io.Reader) error {
	request := buildRequest(r)

	err := client.SendRequest(request)
	if err != nil {
		return fmt.Errorf("SendRequest: %w", err)
	}
	return nil
}

func (s *Session) Reset() {}

func (s *Session) Logout() error {
	return nil
}

func buildRequest(r io.Reader) client.Request {
	request := client.Request{}
	request.DataReader = r

	baseUri := os.Getenv("BASE_URI")
	if len(baseUri) == 0 {
		log.Fatalf("BASE_URI must be set")
	}
	request.BaseUri = baseUri

	privateKeyHex := os.Getenv("PRIVATE_KEY")
	privateKeyBytes, err := hex.DecodeString(privateKeyHex)
	if err != nil {
		log.Fatalf("decoding private key: %w", err)
	}

	privateKey := ed25519.NewKeyFromSeed(privateKeyBytes)
	request.PrivateKey = privateKey

	return request
}

// ExampleServer runs an example SMTP server.
//
// It can be tested manually with e.g. netcat:
//
//	> netcat -C localhost 1025
//	EHLO localhost
//	AUTH PLAIN
//	AHVzZXJuYW1lAHBhc3N3b3Jk
//	MAIL FROM:<root@nsa.gov>
//	RCPT TO:<root@gchq.gov.uk>
//	DATA
//	Hey <3
//	.
func main() {
	// validate inputs are valid
	_ = buildRequest(nil)

	be := &Backend{}

	s := smtp.NewServer(be)

	s.Addr = "localhost:1025"
	s.Domain = "localhost"
	s.WriteTimeout = 10 * time.Second
	s.ReadTimeout = 10 * time.Second
	s.MaxMessageBytes = 1024 * 1024
	s.MaxRecipients = 50
	s.AllowInsecureAuth = true

	log.Println("Starting server at", s.Addr)
	if err := s.ListenAndServe(); err != nil {
		log.Fatal(err)
	}
}
