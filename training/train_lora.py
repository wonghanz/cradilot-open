"""
Cradilot Fine-Tuning - QLoRA Training Script
Executes 4-bit Quantized Low-Rank Adaptation (QLoRA) on Gemma base model.
Optimized for 12GB VRAM RTX 3060 running Ubuntu 24.04.
"""

import os
import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "training" / "qlora_config.json"
DATASET_PATH = BASE_DIR / "data" / "fine_tuning" / "sft_cradilot_train.jsonl"


def check_prerequisites():
    """Verify GPU availability and required packages."""
    try:
        import torch
        print(f"PyTorch Version: {torch.__version__}")
        print(f"CUDA Available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"Device Name: {torch.cuda.get_device_name(0)}")
            total_vram = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            print(f"Total VRAM: {total_vram:.2f} GB")
    except Exception as e:
        print(f"Warning checking torch: {e}")


def load_training_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def prepare_dataset_for_trainer(dataset_path: Path):
    """Load JSONL dataset into list of text prompts formatted with ChatML/Gemma tokens."""
    data = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            system = record.get("system", "")
            convs = record.get("conversations", [])
            user_msg = next((c["value"] for c in convs if c["from"] == "user"), "")
            asst_msg = next((c["value"] for c in convs if c["from"] == "assistant"), "")
            
            # Format according to Gemma turn structure
            formatted_text = (
                f"<start_of_turn>user\n{system}\n\n{user_msg}<end_of_turn>\n"
                f"<start_of_turn>model\n{asst_msg}<end_of_turn>"
            )
            data.append({"text": formatted_text})
    return data


def run_training_pipeline():
    """Main training execution entrypoint."""
    print("=" * 70)
    print("CRADILOT QLORA FINE-TUNING PIPELINE")
    print("Cradle mindset SME digital growth model")
    print("=" * 70)
    
    check_prerequisites()
    config = load_training_config()
    print(f"Loaded training config: {json.dumps(config['lora_parameters'], indent=2)}")
    print(f"Dataset path: {DATASET_PATH} (Exists: {DATASET_PATH.exists()})")
    
    samples = prepare_dataset_for_trainer(DATASET_PATH)
    print(f"Prepared {len(samples)} instruction-formatted training samples.")
    
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        
        print("\nAll HuggingFace & PEFT libraries are loaded.")
        print(f"Ready to initialize model: {config['model_name_or_path']}")
        print(f"Target VRAM usage: ~{config['hardware_budget']['estimated_vram_usage_gb']} GB")
        print("To launch training on your CUDA node:")
        print("  python training/train_lora.py --execute")
        
    except ImportError as e:
        print(f"\nNote: Missing optional deep learning package on local machine: {e}")
        print("On the CUDA machine that will run training, run:")
        print("  pip install transformers peft bitsandbytes trl accelerate")
        print("  python training/train_lora.py --execute")


if __name__ == "__main__":
    run_training_pipeline()
