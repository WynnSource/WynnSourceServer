<div align="center">

# WynnSourceServer

The server component of [WynnSource](https://github.com/WynnSource) — a Wynncraft crowdsourcing mod.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/) [![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/) [![Protobuf](https://img.shields.io/badge/Protocol%20Buffers-4285F4?logo=google&logoColor=white)](https://protobuf.dev/) [![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

</div>

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [buf](https://buf.build/) — Protocol Buffers toolchain
- A PostgreSQL database
- A Redis instance

## Development Setup

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/WynnSource/WynnSourceServer.git
cd WynnSourceServer

# Generate protobuf code
buf generate --template buf.gen.yaml

# Install dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Start the development server
uv run fastapi dev
```

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_USER` | PostgreSQL user | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `postgres` |
| `POSTGRES_DB` | PostgreSQL database name | `wcs_db` |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `WCS_ADMIN_TOKEN` | Admin API token | None |
| `LEVEL` | Log level | `DEBUG` |
| `BETA_ALLOWED_VERSIONS` | Comma-separated allowed mod versions | `` |

## Deploying to Kubernetes

WynnSourceServer uses [Kustomize](https://kustomize.io/) overlays for deployment and [ArgoCD](https://argo-cd.readthedocs.io/) with [Image Updater](https://argocd-image-updater.readthedocs.io/) for GitOps.

### Directory Structure

```
deploy/
  base/                 # Shared manifests
    deployment.yaml     # App deployment with health probes
    service.yaml        # ClusterIP service on port 8000
    postgres.yaml       # CNPG PostgreSQL cluster
    redis.yaml          # Redis instance (via Redis Operator)
    migration-job.yaml  # Alembic migration (ArgoCD sync hook)
    kustomization.yaml
  overlays/
    dev/                # Dev environment (namespace: wynnsource-dev)
      kustomization.yaml
    prod/               # Prod environment (namespace: wynnsource, replicas: 2)
      kustomization.yaml
```

### Cluster Prerequisites

The following operators must be installed in the cluster:

- [CloudNativePG](https://cloudnative-pg.io/) — PostgreSQL operator
- [Redis Operator](https://github.com/OT-CONTAINER-KIT/redis-operator) — Redis operator
- [ArgoCD Image Updater](https://argocd-image-updater.readthedocs.io/) — Automatic image updates

### Step 1: Create Secrets

Create the application secrets in the target namespace. Using [Sealed Secrets](https://sealed-secrets.netlify.app/) is recommended.

```bash
kubectl -n <namespace> create secret generic wynnsource-secrets \
  --from-literal=WCS_ADMIN_TOKEN='<your-admin-token>'
```

### Step 2: Create ConfigMap

```bash
kubectl -n <namespace> create configmap wynnsource-config \
  --from-literal=LEVEL='INFO' \
  --from-literal=BETA_ALLOWED_VERSIONS='0.2.6, 0.2.7'
```

### Step 3: Create ArgoCD Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: wynnsource
  namespace: argocd
  annotations:
    argocd-image-updater.argoproj.io/image-list: app=ghcr.io/wynnsource/wynnsource-server
    argocd-image-updater.argoproj.io/app.update-strategy: newest-build
    argocd-image-updater.argoproj.io/app.allow-tags: "regexp:^dev-"
    argocd-image-updater.argoproj.io/app.ignore-tags: "latest,dev-latest"
spec:
  project: default
  source:
    repoURL: https://github.com/WynnSource/WynnSourceServer.git
    targetRevision: dev           # or master for production
    path: deploy/overlays/dev     # or deploy/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: wynnsource-dev     # or wynnsource
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
```

### Step 4: Configure Ingress

Add an IngressRoute (or Ingress) pointing to the `wynnsource-server` service on port 8000. Make sure the `X-Real-IP` header is forwarded from the ingress controller for proper client IP logging and rate limiting.

## Using the Schema (Protobuf)

WynnSourceServer uses [Protocol Buffers](https://protobuf.dev/) to define item encoding schemas. The `.proto` definitions live in the [`schema`](https://github.com/WynnSource/schema) submodule under `schema/proto/wynnsource/`.

### Generating Python Code

#### With buf (recommended)

Install [buf](https://buf.build/docs/installation), then from the repository root:

```bash
buf generate --template buf.gen.yaml
```

This generates Python protobuf modules into `generated/wynnsource/` based on:

```yaml
# buf.gen.yaml
version: v2
plugins:
  - remote: buf.build/protocolbuffers/python:v33.5
    out: generated
  - remote: buf.build/protocolbuffers/pyi:v33.5
    out: generated
inputs:
  - directory: schema/proto
```

#### With protoc

```bash
protoc \
  --proto_path=schema/proto \
  --python_out=generated \
  --pyi_out=generated \
  schema/proto/wynnsource/**/*.proto
```

### Using Generated Code

Install the `protobuf` runtime, then import the generated modules:

```bash
pip install protobuf
```

```python
from wynnsource.item.gear_pb2 import IdentifiedGear
from wynnsource.item.consumable_pb2 import Consumable
from wynnsource.common.enums_pb2 import Rarity

# Create an item
gear = IdentifiedGear()
gear.name = "Cataclysm"

# Serialize to bytes
data = gear.SerializeToString()

# Deserialize from bytes
parsed = IdentifiedGear()
parsed.ParseFromString(data)
```

### Using as a Workspace Package

In this repository, the generated code is a [uv workspace](https://docs.astral.sh/uv/concepts/workspaces/) package called `wynnsource-proto`. After running `buf generate` and `uv sync`, you can import directly:

```python
from wynnsource.item.wynn_source_item_pb2 import WynnSourceItem
```

### Mappings

The schema repository includes JSON mapping files:

- `schema/mapping/identification.json` — Identification ID mappings
- `schema/mapping/shiny.json` — Shiny stat mappings

### Generating for Other Languages

buf supports many languages. See the [buf plugin registry](https://buf.build/plugins) for available plugins. Example for TypeScript:

```yaml
# buf.gen.yaml
version: v2
plugins:
  - remote: buf.build/connectrpc/es
    out: gen/ts
inputs:
  - directory: schema/proto
```

## License

This project is licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](https://www.gnu.org/licenses/agpl-3.0) with the following exception.

### Exception for Generated Client Code

As a special exception, the copyright holders grant permission to generate, use, distribute, and license client libraries and SDKs produced from this project's API specifications (including OpenAPI documents, Protocol Buffer definitions, and GraphQL schemas) under any license of your choice, including proprietary licenses. This exception applies solely to the generated client code — the server-side source code remains subject to the AGPL-3.0 in full.

### Rationale

The AGPL-3.0 ensures that improvements to the server are shared with the community. However, client libraries derived from our API specifications are commonly embedded in Minecraft mods and other applications whose licenses may be incompatible with the AGPL. This exception removes that friction: developers can freely build and ship clients against our API without licensing concerns, while contributions to the backend itself continue to benefit everyone.
