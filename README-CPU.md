# LLaMA Stack RAG Deployment - CPU Local Dev

This guide helps you deploy the **LLaMA Stack RAG UI** locally using openshift-local for single-node and microshift and use your CPU for inferencing.


## Prerequisites

Before deploying, make sure you have the following:

- Download [openshift-local](https://console.redhat.com/openshift/create/local) (do not run crc setup at this time)
- [Helm](https://helm.sh/docs/intro/install/) is installed
- A valid [Hugging Face Token](https://huggingface.co/settings/tokens).
- Access to [Meta Llama](https://www.llama.com/llama-downloads/) models

### Build vLLM with CPU support

```bash
git clone https://github.com/vllm-project/vllm
cd vllm
git checkout v0.8.4
curl -sL -o $PWD/docker/Containerfile.cpu https://gist.githubusercontent.com/mrhillsman/0f791a1d3c14abf333a9ea233ae44e0b/raw/ff055b2e5fd34198be53eb1fdf30ea3ea9dd24a8/Containerfile.cpu
podman build -f $PWD/docker/Containerfile.cpu --tag quay.io/vllm/vllm-cpu:v0.8.4 --target vllm-openai .
```
_push the image to a public registry or ensure you can pull the image if [authentication](https://access.redhat.com/RegistryAuthentication) is required_

## Setting up openshift-local
_make sure that port 2222 is not being used as it is a common practice to change SSH to use port 2222 instead of port 22_

1. single-node openshift

```bash
crc setup openshift --show-progressbars
crc start -c 16 -d 80 -m 32768 $HOME/pull-secret
```

2. microshift

```bash
crc setup microshift --show-progressbars
crc start -c 8 -d 40 -m 16384 $HOME/pull-secret
```

_crc uses $HOME/.crc by default if you need to recover files like the kubeconfig for example_

## Deployment Steps

1. Prior to deploying, ensure that you have access to the meta-llama/Llama-3.2-3B-Instruct model. If not, you can visit this meta and get access - https://www.llama.com/llama-downloads/

2. Once everything's set, navigate to the Helm deployment directory:

   ```bash
   cd deploy/helm
   ```
   
3. Update the values-crc-cpu.yaml file setting the repository and tag to point to your image for vLLM  
and add extraEnv [VLLM_CPU_KVCACHE_SPACE](https://docs.vllm.ai/en/latest/serving/env_vars.html#environment-variables)=1 for llama-serve and safety-model
```bash
llama-serve:
  extraEnv:
  - name: VLLM_CPU_KVCACHE_SPACE
    value: '1'
    
safety-model
  extraEnv:
  - name: VLLM_CPU_KVCACHE_SPACE
    value: '1'
```

4. If running microshift create the namespace llama-rag-stack manually since `make install-crc` will fail due to the projects api-resource not being available.

5. Run the install command:

   ```bash
   make install-crc
   ```

6. When prompted, enter your **Hugging Face Token**.

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

## Resource cleanup

```
make unistall
```
