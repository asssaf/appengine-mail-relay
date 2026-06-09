# App Engine Mail Relay

A mail relay service consisting of a Python Flask backend designed for Google App Engine and a Go-based client.

## Building and Testing with Bazel

This project uses [Bazel](https://bazel.build/) with [Bzlmod](https://bazel.build/external/overview#bzlmod) for building and testing. It is recommended to use [Bazelisk](https://github.com/bazelbuild/bazelisk) as a wrapper for Bazel to automatically use the correct version specified in `.bazelversion`.

### Prerequisites

- [Bazelisk](https://github.com/bazelbuild/bazelisk#installation) installed and available as `bazel` or `bazelisk`.

### Building Go Client

To build all Go client binaries:

```bash
bazelisk build //client/...
```

The binaries will be available in `bazel-bin/client/cli/cli_/cli` and `bazel-bin/client/smtp/smtp_/smtp`.

#### Cross-Compilation

To cross-compile the Go client for specific platforms:

**Linux AMD64:**
```bash
bazelisk build //client/cli --platforms=@rules_go//go/toolchain:linux_amd64
```

**Linux ARM64:**
```bash
bazelisk build //client/cli --platforms=@rules_go//go/toolchain:linux_arm64
```

### Building and Testing Python Server

To build the Python server:

```bash
bazelisk build //server:server
```

To run the Python server tests:

```bash
bazelisk test //server/tests:test_main
```

### Updating Go Dependencies (Gazelle)

If you add new Go files or change Go dependencies, run Gazelle to update the `BUILD.bazel` files:

```bash
bazelisk run //:gazelle
```

### Updating Python Dependencies

Python dependencies are managed via `server/requirements-lock.txt`. To add new dependencies, update `server/requirements.txt` (and `requirements-dev.txt` if needed) and regenerate the lock file.

## Legacy Build (Optional)

You can still use standard Go and Python tools if needed, but Bazel is the preferred way for reproducible builds.
