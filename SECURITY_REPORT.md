# Security Vulnerability Analysis Report

## 1. Overview
This report details the security vulnerabilities identified in the `appengine-mail-relay` codebase. The system consists of a Python/Flask server running on Google App Engine and a Go-based client/relay.

## 2. Server-side Vulnerabilities (Python/Flask)

### 2.1 Unauthorized Key Generation (`/key` Endpoint)
- **Vulnerability:** The `/key` endpoint generates a new Ed25519 key pair and returns both the public and private keys in the response.
- **Impact:** An attacker can generate an unlimited number of key pairs. While these keys aren't used by the server unless manually configured in environment variables, this endpoint serves no purpose for a public-facing production service and could be abused for DoS or to facilitate unauthorized setups.
- **Recommendation:** Remove this endpoint or restrict it to authenticated administrators/internal networks.

### 2.2 Replay Attacks
- **Vulnerability:** The server verifies a timestamp but has a 120-second "fudge" window (`TIME_FUDGE_SECONDS`). It does not track used signatures or nonces.
- **Impact:** An attacker who intercepts a valid notification request can replay it multiple times within the 120-second window, causing the same email to be sent repeatedly.
- **Recommendation:** Implement a nonce-based system or store hashes of processed signatures in a fast cache (like Redis/Memorystore or Datastore with TTL) to ensure each signature is only used once.

### 2.3 Information Leakage via Stack Traces
- **Vulnerability:** The `/health` and `/notification` endpoints catch exceptions and return full stack traces or internal error details in the JSON response.
- **Impact:** Stack traces reveal internal directory structures, library versions, and logic flow, which can assist an attacker in crafting more targeted exploits.
- **Recommendation:** Return generic error messages to the client while logging detailed stack traces to a secure logging service (e.g., Cloud Logging).

### 2.4 Potential Email Header Injection
- **Vulnerability:** In `sendNotification`, the `body` from the signed message is passed directly as `mime_message` to `mail.EmailMessage`.
- **Impact:** If the signing key is compromised or if an authorized client is compromised, the `body` could contain malicious MIME headers (e.g., `Bcc:`, `Subject:`) that might be interpreted by the App Engine mail API, allowing for spoofing or unauthorized relaying.
- **Recommendation:** Sanitize the input `body` or use more structured fields instead of passing a raw MIME message if possible.

### 2.5 Lack of Rate Limiting
- **Vulnerability:** No rate limiting is implemented on the `/notification` or `/key` endpoints.
- **Impact:** A malicious actor (even with a valid key for `/notification`) could flood the service, leading to exhaustion of App Engine quotas or excessive costs.
- **Recommendation:** Implement rate limiting using Flask-Limiter or a Cloud-native solution like Google Cloud Armor.

## 3. Client-side Vulnerabilities (Go)

### 3.1 Hardcoded Credentials
- **Vulnerability:** The SMTP relay (`client/smtp/smtp.go`) has hardcoded credentials: `username == "username"` and `password == "password"`.
- **Impact:** Anyone with network access to the SMTP port can relay emails if they know these trivial credentials.
- **Recommendation:** Move credentials to environment variables or a secret management system.

### 3.2 Insecure SMTP Authentication
- **Vulnerability:** `AllowInsecureAuth = true` is set in the SMTP server configuration.
- **Impact:** Credentials may be sent in plain text if TLS is not enforced, making them susceptible to interception on the network.
- **Recommendation:** Set `AllowInsecureAuth` to `false` and ensure the server is configured with valid TLS certificates.

### 3.3 Sensitive Data in Environment Variables
- **Vulnerability:** Both the Go client and the Python server rely on `PRIVATE_KEY` and `PUBLIC_KEY` being stored in environment variables.
- **Impact:** Environment variables are often logged or visible in process listings and CI/CD logs, increasing the risk of key compromise.
- **Recommendation:** Use Google Cloud Secret Manager to store and retrieve sensitive keys.

## 4. Dependency Vulnerabilities

### 4.1 Python Dependencies
- **PyNaCl (1.5.0):** Vulnerable to CVE-2025-69277 (Mishandles checks for whether an elliptic curve point is valid).
- **Flask (3.0.3):** Vulnerable to CVE-2026-27205 (Information Disclosure due to missing cache-variation headers).
- **Recommendation:** Update `requirements.txt` to use `PyNaCl>=1.6.2` and `Flask>=3.1.3`.

### 4.2 Go Runtime
- **Go Standard Library (1.24.3):** Multiple vulnerabilities identified affecting `net/http`, `crypto/tls`, and `crypto/x509` in the current environment's Go version.
- **Recommendation:** Upgrade the Go runtime to the latest stable version (e.g., Go 1.24.4+ or 1.25.x as per security advisories) and update external modules like `github.com/emersion/go-smtp`.

## 5. Deployment Configuration

### 5.1 Insecure Templates
- **Vulnerability:** `env_variables.yaml.template` contains a placeholder `deadbeaf...` which might be used as a literal if not carefully updated.
- **Recommendation:** Ensure deployment scripts validate that placeholder values have been replaced with secure, unique keys.

## 6. Summary of Mitigation Strategies
1.  **Upgrade All Dependencies:** Both Python and Go environments should be updated to their latest stable and patched versions.
2.  **Secure Key Management:** Transition from environment variables to Google Cloud Secret Manager.
3.  **Implement Replay Protection:** Use a stateful check for signatures or nonces.
4.  **Harden Endpoints:** Remove the `/key` endpoint from production and implement rate limiting on all public routes.
5.  **Remove Hardcoded Secrets:** Clean up `client/smtp/smtp.go` and use proper authentication mechanisms.
6.  **Refine Error Handling:** Disable stack traces in production responses.
