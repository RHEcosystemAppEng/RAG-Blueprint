# LLaMA Stack RAG Deployment

This guide helps you deploy the **LLaMA Stack RAG UI** on an OpenShift cluster using Helm.


## Prerequisites

Before deploying, make sure you have the following:

- Access to an **OpenShift** cluster with appropriate permissions.
- At least one **GPU-enabled node** in the cluster.
- The following **node labels and taints** are applied:
  - **LLaMA Serve** requires a node with the label: `g6e-gpu`
  - **Safety Model** requires a node with the label: `odh-notebook`
- Helm is installed on your local machine.
- A valid **Hugging Face Token**.
- Access to meta-llama/Llama-3.2-3B-Instruct model


## Node Tolerations

To ensure pods are scheduled on the correct GPU nodes, the deployment uses the following tolerations:

### LLaMA Serve

```yaml
tolerations:
  - key: g6e-gpu
    operator: Exists
    effect: NoSchedule
```

### Safety Model

```yaml
tolerations:
  - key: odh-notebook
    operator: Exists
    effect: NoSchedule
```

> Ensure your GPU nodes are properly **tainted and labeled** to match the toleration keys.


## Deployment Steps

1. Prior to deploying, ensure that you have access to the meta-llama/Llama-3.2-3B-Instruct model. If not, you can visit this url and get access - https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct

2. Once everything's set, navigate to the Helm deployment directory:

   ```bash
   cd deploy/helm
   ```

3. Run the deployment script:

   ```bash
   ./deploy.sh
   ```

4. When prompted, enter your **Hugging Face Token**.

   The script will:

   - Create a new project: `llama-stack-rag`
   - Create and annotate the `huggingface-secret`
   - Deploy the Helm chart with toleration settings
   - Output the status of the deployment


## Post-deployment Verification

Once deployed, verify the following:

```bash
kubectl get pods -n llama-stack-rag

kubectl get svc -n llama-stack-rag

kubectl get routes -n llama-stack-rag
```

You should see the running components, services, and exposed routes.

LLama UI
![Llama UI](Llama-UI.png)
