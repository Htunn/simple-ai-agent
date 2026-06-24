{{/*
Expand the name of the chart.
*/}}
{{- define "aiops-orchestrator.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
Truncate at 63 chars because Kubernetes name fields are limited.
*/}}
{{- define "aiops-orchestrator.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart label value (chart-version).
*/}}
{{- define "aiops-orchestrator.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "aiops-orchestrator.labels" -}}
helm.sh/chart: {{ include "aiops-orchestrator.chart" . }}
{{ include "aiops-orchestrator.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "aiops-orchestrator.selectorLabels" -}}
app.kubernetes.io/name: {{ include "aiops-orchestrator.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "aiops-orchestrator.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "aiops-orchestrator.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
DATABASE_URL helper.
When postgresql subchart is enabled, build from the bitnami service name.
The actual password is injected at runtime via Kubernetes env var substitution.
*/}}
{{- define "aiops-orchestrator.databaseUrl" -}}
{{- if .Values.postgresql.enabled -}}
postgresql+asyncpg://{{ .Values.postgresql.auth.username }}:$(POSTGRESQL_PASSWORD)@{{ .Release.Name }}-postgresql:5432/{{ .Values.postgresql.auth.database }}
{{- else -}}
{{ required "secrets.externalDatabaseUrl is required when postgresql.enabled=false" .Values.secrets.externalDatabaseUrl }}
{{- end }}
{{- end }}

{{/*
REDIS_URL helper.
When redis subchart is enabled, build from bitnami redis-master service.
*/}}
{{- define "aiops-orchestrator.redisUrl" -}}
{{- if .Values.redis.enabled -}}
redis://{{ .Release.Name }}-redis-master:6379/0
{{- else -}}
{{ required "secrets.externalRedisUrl is required when redis.enabled=false" .Values.secrets.externalRedisUrl }}
{{- end }}
{{- end }}

{{/*
PROMETHEUS_URL helper.
*/}}
{{- define "aiops-orchestrator.prometheusUrl" -}}
{{- if index .Values "prometheus-stack" "enabled" -}}
http://{{ .Release.Name }}-prometheus-stack-prometheus.{{ .Release.Namespace }}.svc.cluster.local:9090
{{- else -}}
{{ .Values.external.prometheus.url }}
{{- end }}
{{- end }}

{{/*
GRAFANA_URL helper.
*/}}
{{- define "aiops-orchestrator.grafanaUrl" -}}
{{- if index .Values "prometheus-stack" "enabled" -}}
http://{{ .Release.Name }}-prometheus-stack-grafana.{{ .Release.Namespace }}.svc.cluster.local:3000
{{- else -}}
{{ .Values.external.grafana.url }}
{{- end }}
{{- end }}

{{/*
OTLP_ENDPOINT helper.
When jaeger subchart is enabled, point to the collector gRPC port.
*/}}
{{- define "aiops-orchestrator.otlpEndpoint" -}}
{{- if .Values.jaeger.enabled -}}
http://{{ .Release.Name }}-jaeger-collector.{{ .Release.Namespace }}.svc.cluster.local:4317
{{- else -}}
{{ .Values.otel.endpoint }}
{{- end }}
{{- end }}

{{/*
Name of the secret created by this chart.
*/}}
{{- define "aiops-orchestrator.secretName" -}}
{{- include "aiops-orchestrator.fullname" . }}
{{- end }}

{{/*
Name of the configmap created by this chart.
*/}}
{{- define "aiops-orchestrator.configmapName" -}}
{{- include "aiops-orchestrator.fullname" . }}
{{- end }}
