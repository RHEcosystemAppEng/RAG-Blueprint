# LLaMA Stack RAG Deployment

This guide helps you deploy the **LLaMA Stack RAG UI** on an OpenShift cluster using Helm.


## Prerequisites

Before deploying, make sure you have the following:

- Access to an **OpenShift** cluster with appropriate permissions.
- Two GPU nodes, one for vLLM and the other for Safety Model(A10 nodes)
- The label - you can have any label on the node and pass it as part of the parameter to the deploy script. Please refer `deploy.sh`.
- Helm is installed
- A valid **Hugging Face Token**.
- Access to meta-llama/Llama-3.2-3B-Instruct model


## Deployment Steps

1. Prior to deploying, ensure that you have access to the meta-llama/Llama-3.2-3B-Instruct model. If not, you can visit this meta and get access - https://www.llama.com/llama-downloads/

2. Once everything's set, navigate to the Helm deployment directory:

   ```bash
   cd deploy/helm
   ```

3. Run the install command:

   ```bash
   make install
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
