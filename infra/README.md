# Infraestructura

Herramientas de terceros desplegadas vía Helm/kubectl — no código original del
TFM, documentado aquí por trazabilidad.

## Clúster
- `kind create cluster --name aiops-platform`

## Aplicación de referencia
- Online Boutique (Google): `kubectl apply -n online-boutique -f https://raw.githubusercontent.com/GoogleCloudPlatform/microservices-demo/main/release/kubernetes-manifests.yaml`

## Observabilidad (namespace `observability`)
- `kube-prometheus-stack` (Prometheus + Grafana + Alertmanager + node-exporter + kube-state-metrics)
- `loki-stack` (Loki + Promtail) para logs

## Pendiente
- Chaos Mesh para inyección de fallos
