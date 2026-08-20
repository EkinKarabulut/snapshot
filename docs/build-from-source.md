# Building from source

This guide builds the Snapshot operator and node-agent images from a checkout of
this repository and installs the chart against them. Most users should install
[from a release](../README.md#from-a-release) instead — build from source when you
are developing Snapshot or testing unreleased changes.

## Prerequisites

In addition to the [runtime prerequisites](../README.md#prerequisites), you need:

- Go (matching the version pinned in the modules)
- Docker with Buildx
- A container registry your cluster can pull from, and push access to it
- `kubectl` and `helm` configured against your cluster

The node agent is **x86_64 (amd64) only** — `cuda-checkpoint` ships no other
architecture — so its image builds for `linux/amd64`.

<!-- TODO(eng): pin the exact Go version and any other build-tool requirements. -->

## 1. Clone the repository

```bash
git clone https://github.com/ai-dynamo/snapshot.git
cd snapshot
```

## 2. Build the images

The root `Makefile` builds both images. Override `REGISTRY` and `VERSION` to tag
them for your registry:

```bash
make docker-build-agent docker-build-operator \
  REGISTRY=<your-registry> \
  VERSION=<your-tag>
```

This produces `<your-registry>/agent:<your-tag>` and
`<your-registry>/operator:<your-tag>`.

## 3. Push the images

Push both images to a registry your cluster can pull from:

```bash
docker push <your-registry>/agent:<your-tag>
docker push <your-registry>/operator:<your-tag>
```

<!-- TODO(eng): confirm the supported push path (docker push vs buildx --push via DOCKER_BUILD_ARGS) and whether a make target exists. -->

## 4. Install the chart against your images

Install the chart from your checkout, pointing the operator and agent images at
what you built:

```bash
helm install snapshot ./charts/snapshot \
  --namespace snapshot --create-namespace \
  --set image.operator.repository=<your-registry>/operator \
  --set image.operator.tag=<your-tag> \
  --set image.agent.repository=<your-registry>/agent \
  --set image.agent.tag=<your-tag>
```

See [Installation](install.md) for storage, RBAC, runtime, and uninstall options.

## Development workflow

Common `make` targets from the repo root:

- `make build` — compile the agent and operator
- `make test` — run unit tests across the `api`, `agent`, and `operator` modules
- `make lint` — run linters
- `make helm-lint` — lint the Helm chart
- `make check` — the full pre-merge gate (generate, license headers, fmt, tidy, lint, and more)

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the contribution process and DCO
sign-off.
