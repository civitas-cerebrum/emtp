import os
import json
import torch
from typing import List, Dict, Optional
from huggingface_hub import login
from datasets import Dataset
from trl import SFTTrainer, SFTConfig
from peft import PeftModel, LoraConfig
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForImageTextToText, BitsAndBytesConfig

from util.utilities import getConfig, getLogger, getEmtpDirectory

config = getConfig()
log = getLogger(__name__)


def load_and_format_dataset(file_path: str, system_message: str) -> List[Dict]:
    """
    Loads Q&A data from JSON and formats it for TRL training.
    """
    formatted_data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            qa_data = json.load(f)
            
        for item in qa_data:
            conversation = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": item["q"]},
                {"role": "assistant", "content": item["a"]}
            ]
            formatted_data.append({"messages": conversation})
            
    except Exception as e:
        log.error(f"Error processing JSON file {file_path}: {e}")
    
    return formatted_data


def train_model(
    output_model_name: str,
    base_model_id: str,
    dataset_path: str,
    model_expertise: str,
    hf_token: str,
    system_prompt_template: str,
):
    """
    Orchestrates the model training process: loads data, configures the model,
    runs SFT training, and merges the LoRA adapter.
    """
    if hf_token:
        login(hf_token)
    else:
        log.warning("No Hugging Face token provided. Ensure you are logged in via CLI.")

    # Prepare System Prompt
    system_prompt = system_prompt_template.format(
        model_name=output_model_name, 
        model_expertise=model_expertise
    )
    log.info(f"System Prompt: {system_prompt}")

    # Load and Format Data
    dataset_path = os.path.join(getEmtpDirectory(), dataset_path)
    formatted_data = load_and_format_dataset(dataset_path, system_prompt)
    
    if not formatted_data:
        log.error("No training data found. Aborting.")
        return

    dataset = Dataset.from_list(formatted_data)
    log.info(f"Loaded {len(dataset)} training examples from {dataset_path}")

    # Determine Model Class
    if base_model_id == "google/gemma-3-1b-pt":
        model_class = AutoModelForCausalLM
    else:
        model_class = AutoModelForImageTextToText

    # Determine Dtype
    if torch.cuda.get_device_capability()[0] >= 8:
        torch_dtype = torch.bfloat16
    else:
        torch_dtype = torch.float16

    # Model Configuration
    model_kwargs = dict(
        attn_implementation="eager",
        torch_dtype=torch_dtype,
        device_map="auto",
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type='nf4',
            bnb_4bit_compute_dtype=torch_dtype,
            bnb_4bit_quant_storage=torch_dtype,
        )
    )

    log.info(f"Loading base model: {base_model_id}")
    model = model_class.from_pretrained(base_model_id, **model_kwargs)
    tokenizer = AutoTokenizer.from_pretrained(base_model_id)

    # LoRA Configuration
    peft_config = LoraConfig(
        lora_alpha=16,
        lora_dropout=0.05,
        r=16,
        bias="none",
        target_modules="all-linear",
        task_type="CAUSAL_LM",
        modules_to_save=["lm_head", "embed_tokens"]
    )

    # Training Arguments
    args = SFTConfig(
        output_dir=output_model_name,
        max_seq_length=512,
        packing=True,
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        gradient_checkpointing=True,
        optim="adamw_torch_fused",
        logging_steps=10,
        save_strategy="epoch",
        learning_rate=2e-4,
        fp16=True if torch_dtype == torch.float16 else False,
        bf16=True if torch_dtype == torch.bfloat16 else False,
        max_grad_norm=0.3,
        warmup_ratio=0.03,
        lr_scheduler_type="constant",
        push_to_hub=False,
        report_to="tensorboard",
        dataset_kwargs={
            "add_special_tokens": False,
            "append_concat_token": True,
        }
    )

    # Set Chat Template
    tokenizer.chat_template = "{% if not add_generation_prompt is defined %}{% set add_generation_prompt = false %}{% endif %}{% for message in messages %}{{'<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>' + '\n'}}{% endfor %}{% if add_generation_prompt %}{{ '<|im_start|>assistant\n' }}{% endif %}"

    # Initialize Trainer
    trainer = SFTTrainer(
        model=model,
        args=args,
        train_dataset=dataset,
        peft_config=peft_config,
        processing_class=tokenizer
    )

    # Train
    log.info("Starting training...")
    try:
        trainer.train(resume_from_checkpoint=True)
    except ValueError:
        log.warning("No previous checkpoint found. Starting training from scratch.")
        trainer.train()

    # Save Adapter
    torch.save(trainer.model.state_dict(), f"{args.output_dir}/adapter_model.bin")
    trainer.save_model()
    
    # Clean up for Merging
    del model, trainer
    torch.cuda.empty_cache()

    # Merge and Save
    log.info("Merging LoRA adapter with base model...")
    model = model_class.from_pretrained(base_model_id, low_cpu_mem_usage=True, torch_dtype=torch_dtype)
    
    peft_model = PeftModel.from_pretrained(model, args.output_dir)
    merged_model = peft_model.merge_and_unload()
    
    output_merged_dir = f"merged_model-{output_model_name}"
    merged_model.save_pretrained(output_merged_dir, safe_serialization=True)

    processor = AutoTokenizer.from_pretrained(args.output_dir)
    processor.save_pretrained(output_merged_dir)

    log.info(f"Model and tokenizer saved successfully to {output_merged_dir}")


def main(
    output_model_name: str = config.get("DEFAULT", "model_name", fallback="Quail"),
    base_model_id: str = config.get("DEFAULT", "base_model_id", fallback="google/gemma-3-12b-pt"),
    dataset_path: str = "qna_dataset.json",
    model_expertise: str = config.get("DEFAULT", "model_expertise", fallback="Quality Assurance"),
    hf_token: str = config.get("DEFAULT", "hf_token", fallback=None),
    system_prompt_template: str = config.get(
        "DEFAULT", 
        "training_system_prompt", 
        fallback="You are {model_name}, a {model_expertise} expert LLM model. You provide expert opinion on {model_expertise} topics you are queried for. Keep it conversational and engaging."
    )
):
    """
    Main entry point for training configuration and execution.
    """
    train_model(
        output_model_name=output_model_name,
        base_model_id=base_model_id,
        dataset_path=dataset_path,
        model_expertise=model_expertise,
        hf_token=hf_token,
        system_prompt_template=system_prompt_template
    )


if __name__ == "__main__":
    main()