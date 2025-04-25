# Makefile for RAG Deployment
# Replaces the original deploy.sh script with additional uninstall functionality

ifeq ($(NAMESPACE),)
	ifeq ($(findstring list-models,$(MAKECMDGOALS)),)
		$(error NAMESPACE is not set)
	endif
endif

# Default values
POSTGRES_USER ?= postgres
POSTGRES_PASSWORD ?= rag_password
POSTGRES_DBNAME ?= rag_blueprint
MINIO_USER ?= minio_rag_user
MINIO_PASSWORD ?= minio_rag_password
RELEASE_NAME ?= rag
CHART_PATH ?= chartOfCharts
TOLERATION_LLM_SERVER ?= odh-notebook
TOLERATION_SAFETY_SERVER ?= odh-notebook
HF_TOKEN ?= $(shell bash -c 'read -r -p "Enter Hugging Face Token: " HF_TOKEN; echo $$HF_TOKEN')
MCP_SERVERS_CHART_PATH ?= mcp-servers/weather
INGESTION_PIPELINE_CHART_PATH ?= ingestion-pipeline
MCP_SERVERS_RELEASE_NAME ?= mcp-servers
INGESTION_PIPELINE_RELEASE_NAME ?= ingestion-pipeline
TOLERATIONS_TEMPLATE=[{"key":"$(1)","effect":"NoSchedule","operator":"Exists"}]

# Default target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  install       - Install the RAG deployment (creates namespace, secrets, and deploys Helm chart)"
	@echo "  install-cpu   - Install the RAG deployment without GPU (creates namespace, secrets, and deploys Helm chart)"
	@echo "  uninstall     - Uninstall the RAG deployment and clean up resources"
	@echo "  status        - Check status of the deployment"
	@echo "  wait          - Wait for all pods to be ready and verify deployment health"
	@echo ""
	@echo "Configuration options (set via environment variables or make arguments):"
	@echo "  NAMESPACE     			- Target namespace (default: llama-stack-rag)"
	@echo "  RELEASE_NAME  			- Helm release name (default: rag)"
	@echo "  CHART_PATH    			- Path to the Helm chart (default: chartOfCharts)"
	@echo "  HF_TOKEN      			- Hugging Face Token (will prompt if not provided)"
	@echo "  TOLERATION_LLM_SERVER			- Toleration for LLM Server (default: odh-notebook)"
	@echo "  TOLERATION_SAFETY_SERVER		- Toleration for Safety Server (default: odh-notebook)"

# Create namespace and deploy
.PHONY: namespace
namespace:

	@echo "Creating namespace $(NAMESPACE)..."
	oc create namespace $(NAMESPACE) && oc label namespace $(NAMESPACE) modelmesh-enabled=false || oc project $(NAMESPACE) ||:

.PHONY: secrets
secrets:
	@echo "Creating Hugging Face secret..."
	oc create secret -n $(NAMESPACE) generic huggingface-secret --from-literal=HF_TOKEN="$(HF_TOKEN)" --dry-run=client -o yaml | oc apply -f -

	@echo "Creating pgvector secret"
	oc create secret -n $(NAMESPACE) generic pgvector \
		--from-literal=username="$(POSTGRES_USER)" \
		--from-literal=password="$(POSTGRES_PASSWORD)" \
		--from-literal=host=pgvector \
		--from-literal=port=5432 \
		--from-literal=dbname="$(POSTGRES_DBNAME)" || echo "PGVector secret not created"

	@echo "Creating minio secret"
	oc create secret -n $(NAMESPACE) generic minio \
       --from-literal=username=$(MINIO_USER) \
       --from-literal=password=$(MINIO_PASSWORD) \
       --from-literal=host=minio \
       --from-literal=port=9000 || echo "Minio secret not created"

	@echo "Annotating secrets..."
	oc annotate secret huggingface-secret -n $(NAMESPACE) meta.helm.sh/release-name=$(RELEASE_NAME) meta.helm.sh/release-namespace=$(NAMESPACE) --overwrite
	oc annotate secret pgvector -n $(NAMESPACE) meta.helm.sh/release-name=rag meta.helm.sh/release-namespace=$(NAMESPACE)
	oc annotate secret minio -n $(NAMESPACE) meta.helm.sh/release-name=rag meta.helm.sh/release-namespace=$(NAMESPACE)

.PHONY: pg-vector
pg-vector:

	@echo "Bootstrapping pgvector database"
	oc rollout status sts/pgvector
	oc exec -it sts/pgvector -- psql -U postgres -c "CREATE DATABASE $(POSTGRES_DBNAME);"
	oc exec -it sts/pgvector -- psql -U postgres -d $(POSTGRES_DBNAME) -c "CREATE EXTENSION VECTOR;"

.PHONY: install-mcp-servers
install-mcp-servers: namespace
	
	@echo "Deploying Helm chart $(MCP_SERVERS_CHART_PATH) as release $(MCP_SERVERS_RELEASE_NAME) in namespace $(NAMESPACE)..."
	helm upgrade --install $(MCP_SERVERS_RELEASE_NAME) $(MCP_SERVERS_CHART_PATH) -n $(NAMESPACE)

.PHONY: install-ingestion-pipeline
install-ingestion-pipeline: namespace
	
	@echo "Deploying Helm chart $(INGESTION_PIPELINE_CHART_PATH) as release $(INGESTION_PIPELINE_RELEASE_NAME) in namespace $(NAMESPACE)..."
	helm install ingestion-pipeline $(INGESTION_PIPELINE_CHART_PATH) -n $(NAMESPACE)

list-models-%:

	@helm dependency build chartOfCharts/
	@helm template dummy-release chartOfCharts/ --set _debugListModels=true --values chartOfCharts/values-$*.yaml | grep model_id

.PHONY: list-models
list-models: list-models-gpu


install-dry-run-%:

	@helm dependency build chartOfCharts/
	@helm template dummy-release chartOfCharts/ --set _debugListModels=true --values chartOfCharts/values-$*.yaml


.PHONY: install-dry-run
install-dry-run: install-dry-run-gpu

set_helm_args = \
    $(if $(LLM),--set-json global.models.$(LLM).enabled='true',) \
    $(if $(SAFETY),--set-json global.models.$(SAFETY).enabled='true',) \
    $(if $(LLM_URL),--set-json global.models.$(LLM).llamaStack.modelUrl.envValue='"$(LLM_URL)"',) \
    $(if $(SAFETY_URL),--set-json global.models.$(SAFETY).llamaStack.modelUrl.envValue='"$(SAFETY_URL)"',) \
    $(if $(LLM_TOLERATION),--set-json global.models.$(LLM).inferenceService.tolerations='$(call TOLERATIONS_TEMPLATE,$(LLM_TOLERATION))',) \
    $(if $(SAFETY_TOLERATION),--set-json global.models.$(SAFETY).inferenceService.tolerations='$(call TOLERATIONS_TEMPLATE,$(SAFETY_TOLERATION))',)

install-%: namespace secrets

	# Build helm upgarde args from env
	@$(eval HELM_ARGS := $(call set_helm_args))

	@$(MAKE) install-mcp-servers

	@echo "Deploying Helm chart $(CHART_PATH) (services) release $(RELEASE_NAME) in namespace $(NAMESPACE)..."
	helm upgrade --install $(RELEASE_NAME) $(CHART_PATH) -n $(NAMESPACE) --values $(CHART_PATH)/values-$*.yaml \
	--set-json llama-stack.enabled=false $(HELM_ARGS) $(EXTRA_HELM_ARGS)
	oc wait -n $(NAMESPACE) --for=condition=Ready --timeout=60m inferenceservice --all ||:

	@echo "Deploying Helm chart $(CHART_PATH) (llamastack) as release $(RELEASE_NAME) in namespace $(NAMESPACE)..."
	helm upgrade --install $(RELEASE_NAME) $(CHART_PATH) -n $(NAMESPACE) --values $(CHART_PATH)/values-$*.yaml \
	--set-json llama-stack.enabled=true $(HELM_ARGS) $(EXTRA_HELM_ARGS)

	@$(MAKE) pg-vector

	@$(MAKE) status
	@$(MAKE) install-ingestion-pipeline
	@echo "Waiting for deployment to be ready..."
	@$(MAKE) wait
	oc exec minio-0 -- bash -c "mc alias set local http://localhost:9000 $(MINIO_USER) $(MINIO_PASSWORD) && mc mb local/llama"

.PHONY: install
install: install-gpu

# Uninstall the deployment and clean up
.PHONY: uninstall
uninstall: uninstall-helm-release uninstall-mcp-servers uninstall-ingestion-pipeline remove-secrets remove-pvcs

	@echo "Checking for any remaining resources in namespace $(NAMESPACE)..."
	@echo "If you want to completely remove the namespace, run: oc delete project $(NAMESPACE)"
	
	@echo "Remaining resources in namespace $(NAMESPACE):"
	@$(MAKE) status

.PHONY: uninstall-mcp-servers
uninstall-mcp-servers:

	@echo "Uninstalling Helm release $(MCP_SERVERS_RELEASE_NAME) from namespace $(NAMESPACE)..."
	helm uninstall $(MCP_SERVERS_RELEASE_NAME) -n $(NAMESPACE) || echo "MCP servers are not installed or already removed."

.PHONY: uninstall-ingestion-pipeline
uninstall-ingestion-pipeline:

	@echo "Uninstalling Helm release $(INGESTION_PIPELINE_RELEASE_NAME) from namespace $(NAMESPACE)..."
	helm uninstall $(INGESTION_PIPELINE_RELEASE_NAME) -n $(NAMESPACE) || echo "Pipelines are not installed or already removed."

.PHONY: uninstall-helm-release
uninstall-helm-release:

	@echo "Uninstalling Helm release $(RELEASE_NAME) from namespace $(NAMESPACE)..."
	helm uninstall $(RELEASE_NAME) -n $(NAMESPACE) || echo "Helm release not found or already removed."

.PHONY: remove-secrets
remove-secrets:

	@echo "Removing Hugging Face secret..."
	oc delete secret -n $(NAMESPACE) huggingface-secret || echo "Secret not found or already removed."

	@echo "Removing pgvector secret"
	oc delete secret -n $(NAMESPACE) pgvector || echo "Secret not found or already removed."

	@echo "Removing minio secret"
	oc delete secret -n $(NAMESPACE) minio || echo "Secret not found or already removed."

	@echo "Removing pipeline secret"
	oc delete secret -n $(NAMESPACE) rag-pipeline-secrets || echo "Secret not found or already removed."

.PHONY: remove-pvcs
remove-pvcs:

	@echo "Removing pgvector and minio PVCs"
	oc delete pvc -n $(NAMESPACE) $$(oc get pvc -n $(NAMESPACE) -o custom-columns=NAME:.metadata.name --no-headers | grep "^pg-data")
	oc delete pvc -n $(NAMESPACE) $$(oc get pvc -n $(NAMESPACE) -o custom-columns=NAME:.metadata.name --no-headers | grep "^minio-data")

# Check deployment status
.PHONY: status
status:
	@echo "Listing pods..."
	oc get pods -n $(NAMESPACE) || true
	
	@echo "Listing services..."
	oc get svc -n $(NAMESPACE) || true
	
	@echo "Listing routes..."
	oc get routes -n $(NAMESPACE) || true
	
	@echo "Listing secrets..."
	oc get secrets -n $(NAMESPACE) | grep huggingface-secret || true

	@echo "Listing pvcs..."
	oc get pvc -n $(NAMESPACE) || true

# Wait for all pods to be ready
.PHONY: wait
wait:
	@echo "Waiting for all pods to be ready in namespace $(NAMESPACE)..."
	oc wait --for=condition=Ready pods --all -n $(NAMESPACE) --timeout=30m
	@echo "All pods are now ready!"
	
	@echo "Checking deployment health..."
	@if oc get pods -n $(NAMESPACE) | grep -E 'CrashLoopBackOff|Error|Failed|Evicted'; then \
		echo "WARNING: Some pods are in an unhealthy state!"; \
		exit 1; \
	else \
		echo "All deployments appear to be healthy."; \
	fi
	
	@echo "Verifying routes are accessible..."
	@for route in $(oc get routes -n $(NAMESPACE) -o name); do \
		echo "Checking route ${route}..."; \
		host=$(oc get ${route} -n $(NAMESPACE) -o jsonpath='{.spec.host}'); \
		if [ -n "${host}" ]; then \
			echo "Route hostname: ${host}"; \
			echo "Note: Manual verification of route accessibility is recommended"; \
		else \
			echo "WARNING: No hostname found for ${route}"; \
		fi; \
	done
