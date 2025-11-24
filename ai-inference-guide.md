# AI Inference Workflow Guide

## Training vs Inference
- **Training**: Creates the model by learning from data (done once, resource-intensive)
- **Inference**: Uses trained model for predictions (ongoing, lighter compute)

## Model Approaches
### Use Existing Models (Recommended 90% of time)
- Fine-tuning: Modify existing model weights for your domain
- RAG: Same model + external knowledge retrieval
- Prompt engineering: Optimize inputs to existing models

### Train New Models (Rare)
- Only for: massive datasets (>10M examples), unique domains, $1M+ budgets

## Fine-tuning Libraries
```python
# Hugging Face (most popular)
from transformers import AutoModelForCausalLM, Trainer

# LoRA/QLoRA (memory efficient)
from peft import LoraConfig, get_peft_model

# Unsloth (fastest)
from unsloth import FastLanguageModel
```

## Model Sizes & Requirements
- **7B model**: ~13-15 GB, RTX 4090 (24GB), 32GB RAM
- **13B model**: ~25-30 GB, Multiple GPUs, 64GB+ RAM
- **70B model**: ~140-150 GB, Multiple A100s/H100s

## Local Deployment Options
1. **Ollama** (simplest): `ollama run llama2:7b`
2. **vLLM** (production): Python API server
3. **Kubernetes**: Container orchestration for scaling

## Kubernetes Benefits
- **Orchestration**: Manages multiple AI agents/services
- **Auto-scaling**: Adjusts resources based on demand
- **Load balancing**: Distributes inference requests
- **Rolling updates**: Updates models without downtime

## Medical AI Recommendations
1. Start with medical LLM (BioGPT, Meditron)
2. Fine-tune on de-identified hospital data
3. Use RAG for latest research correlation
4. Deploy locally for privacy compliance
5. Implement quality assurance and hallucination detection

## Performance Evaluation
- **Standard benchmarks**: MedQA, PubMedQA, MMLU clinical
- **Custom evaluation**: Your specific hospital data/workflows
- **Key metrics**: Diagnostic accuracy, hallucination rate, response time

## Privacy & Compliance
- Local deployment keeps PHI on-premises
- Fine-tuned models run entirely offline
- HIPAA compliance easier with local infrastructure
- Air-gapped networks for maximum security
