{{/*
Expand the name of the chart.
*/}}
{{- define "simple-ai-agent.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
Truncate at 63 chars because Kubernetes name fields are limited.
*/}}
{{- define "simple-ai-agent.fullname" -}}
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
{{- define "simple-ai-agent.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "simple-ai-agent.labels" -}}
helm.sh/chart: {{ include "simple-ai-agent.chart" . }}
{{ include "simple-ai-agent.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "simple-ai-agent.selectorLabels" -}}
app.kubernetes.io/name: {{ include "simple-ai-agent.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "simple-ai-agent.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "simple-ai-agent.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
DATABASE_URL helper.
When postgresql subchart is enabled, build from the bitnami service name.
The actual password is injected at runtime via Kubernetes env var substitution.
*/}}
{{- define "simple-ai-agent.databaseUrl" -}}
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
{{- define "simple-ai-agent.redisUrl" -}}
{{- if .Values.redis.enabled -}}
redis://{{ .Release.Name }}-redis-master:6379/0
{{- else -}}
{{ required "secrets.externalRedisUrl is required when redis.enabled=false" .Values.secrets.externalRedisUrl }}
{{- end }}
{{- end }}

{{/*
PROMETHEUS_URL helper.
*/}}
{{- define "simple-ai-agent.prometheusUrl" -}}
{{- if index .Values "prometheus-stack" "enabled" -}}
http://{{ .Release.Name }}-prometheus-stack-prometheus.{{ .Release.Namespace }}.svc.cluster.local:9090
{{- else -}}
{{ .Values.external.prometheus.url }}
{{- end }}
{{- end }}

{{/*
GRAFANA_URL helper.
*/}}
{{- define "simple-ai-agent.grafanaUrl" -}}
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
{{- define "simple-ai-agent.otlpEndpoint" -}}
{{- if .Values.jaeger.enabled -}}
http://{{ .Release.Name }}-jaeger-collector.{{ .Release.Namespace }}.svc.cluster.local:4317
{{- else -}}
{{ .Values.otel.endpoint }}
{{- end }}
{{- end }}

{{/*
Name of the secret created by this chart.
*/}}
{{- define "simple-ai-agent.secretName" -}}
{{- include "simple-ai-agent.fullname" . }}
{{- end }}

{{/*
Name of the configmap created by this chart.
*/}}
{{- define "simple-ai-agent.configmapName" -}}
{{- include "simple-ai-agent.fullname" . }}
{{- end }}
