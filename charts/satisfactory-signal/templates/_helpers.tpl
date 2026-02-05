{{/*
Expand the name of the chart.
*/}}
{{- define "satisfactory-signal.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "satisfactory-signal.fullname" -}}
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
Create chart name and version as used by the chart label.
*/}}
{{- define "satisfactory-signal.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "satisfactory-signal.labels" -}}
helm.sh/chart: {{ include "satisfactory-signal.chart" . }}
{{ include "satisfactory-signal.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "satisfactory-signal.selectorLabels" -}}
app.kubernetes.io/name: {{ include "satisfactory-signal.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "satisfactory-signal.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "satisfactory-signal.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Signal CLI REST API fullname
*/}}
{{- define "satisfactory-signal.signalCliRestApi.fullname" -}}
{{- printf "%s-signal-cli" (include "satisfactory-signal.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
