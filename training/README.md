# Model Training

This module handles the training of expert models using the enriched data from the acquisition and enrichment stages.

## Current Status

This module is currently a placeholder for future development. It will consume processed data from `dataset/enrichment/` and train machine learning models.

## Planned Features

- Model architecture definition
- Training pipeline implementation
- Hyperparameter tuning
- Model evaluation and validation
- Checkpointing and model saving
- Integration with popular ML frameworks (PyTorch, TensorFlow, etc.)

## Setup

To convert a `.safetensors` file (commonly used for Hugging Face / PyTorch models like LLaMA) to the `gguf` format (used by [GGML-based](https://github.com/ggerganov/ggml) inference engines like `llama.cpp`), you generally need to follow these steps:

---

### 🔧 **Step-by-step Guide:**

#### 1. **Install Python Environment (if not already set up)**

Make sure you have Python 3.9+ and `pip` installed.

#### 2. **Clone llama.cpp**

```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
```

#### 3. **Install Dependencies**

Install `transformers`, `safetensors`, and other required tools:

```bash
pip install -U transformers datasets safetensors
```

Some conversions also require `sentencepiece`. `accelerate` and `peft`:

```bash
pip install sentencepiece accelerate peft
```

#### 4. **Download/Prepare the Model**

Make sure you have the full model directory (e.g., LLaMA, Mistral, etc.) in HF format, including `config.json`, `tokenizer.model`, and the `.safetensors` files.

Example structure:
```
llama-2/
├── config.json
├── tokenizer.model
├── model-00001-of-00002.safetensors
├── model-00002-of-00002.safetensors
├── tokenizer_config.json
└── generation_config.json
```

#### 5. **Use `convert.py` to Convert**

In the `llama.cpp` repo, use the built-in `convert.py` script:

```bash
python3 convert.py models/llama-2/ --outfile llama-2-f16.gguf
```

You can specify options like `--outtype f16` or `--outtype q4_0` for quantized output.

```bash
python /home/ay/github/project-engram/model-converter/llama.cpp/convert_hf_to_gguf.py /home/ay/github/project-engram/merged_model-Quality_Assurance-expert_model --outfile /home/ay/github/project-engram/model-converter/engrams/merged_model-Quality_Assurance-expert_model.gguf
```

---

### ⚠️ Notes:

- You **must use a model architecture supported** by `llama.cpp` (e.g., LLaMA, Mistral, Mixtral, Phi-2, Gemma). Others like GPT-J or Falcon won't work directly.
- If you don't have the original Hugging Face format and only the `.safetensors` weights, you'll need the original config files as well.
- If you're using a newer architecture (e.g., `Mixtral`, `Gemma`), check the latest instructions and `convert-*.py` scripts in the [`llama.cpp/scripts`](https://github.com/ggerganov/llama.cpp/tree/master/scripts) folder.

---
