# Qdrant Vector Database

## Prerequisites

- Kubernetes cluster
- Helm v3
- kubectl configured with cluster access

## Installation

1. Add the Qdrant Helm repository:

```bash
helm repo add qdrant https://qdrant.github.io/qdrant-helm
helm repo update
```

2. Install Qdrant:

```bash
kubectl create namespace qdrant
helm install qdrant qdrant/qdrant -n qdrant -f qdrant-values.yaml
```

## Verify Installation

Check if pods are running:

```bash
kubectl get pods -n qdrant
```

Check the service (use this for external IP too):

```bash
kubectl get service qdrant -n qdrant
```

## Common Commands

Get Qdrant logs:

```bash
kubectl logs -f deployment/qdrant -n qdrant
```

Port forward to access Qdrant locally:

```bash
kubectl port-forward svc/qdrant 6333:6333 -n qdrant
```

Scale replicas:

```bash
kubectl scale statefulset qdrant --replicas=3 -n qdrant
```

## Health Check

Test the REST API:

```bash
curl http://localhost:6333/health
```

## Uninstall

Remove Qdrant:

```bash
helm uninstall qdrant -n qdrant
```

## Configuration

The deployment uses `qdrant-values.yaml` for configuration. Key settings:

- Single replica deployment
- Resource limits: 4 CPU, 12Gi memory
- Resource requests: 2 CPU, 8Gi memory
- Persistence: 100Gi storage
- Exposed ports:
  - HTTP: 6333
  - gRPC: 6334
  - P2P: 6335

## Troubleshooting

Check pod status:

```bash
kubectl describe pod <pod-name> -n qdrant
```

View pod events:

```bash
kubectl get events -n qdrant
```

Check persistent volumes:

```bash
kubectl get pv,pvc -n qdrant
```

## API Key

Get API key:

```bash
kubectl get secret qdrant-apikey -n qdrant -o jsonpath='{.data.api-key}' | base64 -d
```

```bash
az aks get-credentials --resource-group speck-main-generated-rg --name speck-qdrant-cluster
```
