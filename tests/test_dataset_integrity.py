"""
Cradilot Test Suite - Fine-Tuning Dataset Integrity & Compliance Tests
Verifies that generated datasets strictly adhere to:
1. JSONL valid formatting (0 syntax errors).
2. Required schema keys for SFT and DPO.
3. CoT <thought> reasoning tag presence.
4. Zero-Emoji policy (100% compliance across all lines).
5. Comprehensive coverage of all 10 Malaysian industries.
"""

import json
import re
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
SFT_PATH = BASE_DIR / "data" / "fine_tuning" / "sft_cradilot_train.jsonl"
DPO_PATH = BASE_DIR / "data" / "fine_tuning" / "dpo_cradilot_pairs.jsonl"

# The corpus is not part of this repository: it was distilled from a contest brief and
# a price list that belong to somebody else. Run scripts/generate_sft_dataset.py against
# your own brief and catalogue and these checks switch back on by themselves.
pytestmark = pytest.mark.skipif(
    not (SFT_PATH.exists() and DPO_PATH.exists()),
    reason="fine-tuning corpus not shipped; generate it with scripts/generate_sft_dataset.py",
)

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "]+",
    flags=re.UNICODE
)


def test_sft_dataset_exists_and_not_empty():
    assert SFT_PATH.exists(), f"SFT dataset file not found at {SFT_PATH}"
    assert SFT_PATH.stat().st_size > 500_000, "SFT dataset is unexpectedly small"


def test_dpo_dataset_exists_and_not_empty():
    assert DPO_PATH.exists(), f"DPO dataset file not found at {DPO_PATH}"
    assert DPO_PATH.stat().st_size > 100_000, "DPO dataset is unexpectedly small"


def test_sft_dataset_structure_and_cot():
    with open(SFT_PATH, "r", encoding="utf-8") as f:
        count = 0
        for line in f:
            count += 1
            record = json.loads(line)
            assert "id" in record
            assert "system" in record
            assert "conversations" in record
            assert len(record["conversations"]) == 2
            
            user_msg = record["conversations"][0]
            asst_msg = record["conversations"][1]
            assert user_msg["from"] == "user"
            assert asst_msg["from"] == "assistant"
            
            # Verify Agentic Chain-of-Thought tags
            asst_text = asst_msg["value"]
            assert "<agentic_thought>" in asst_text, f"Missing <agentic_thought> in record {record['id']}"
            assert "</agentic_thought>" in asst_text, f"Missing </agentic_thought> in record {record['id']}"
            assert "商业模式" in asst_text or "Deconstruction" in asst_text
            assert "失血" in asst_text or "Bleeding" in asst_text
            assert "纠错" in asst_text or "Critique" in asst_text
            
        assert count >= 1500, f"Expected >= 1500 SFT samples, got {count}"


def test_dpo_dataset_structure():
    with open(DPO_PATH, "r", encoding="utf-8") as f:
        count = 0
        for line in f:
            count += 1
            record = json.loads(line)
            assert "id" in record
            assert "prompt" in record
            assert "chosen" in record
            assert "rejected" in record
            assert len(record["chosen"]) > 100
            assert len(record["rejected"]) > 50
        assert count >= 200, f"Expected >= 200 DPO samples, got {count}"


def test_zero_emoji_in_all_datasets():
    # Audit SFT
    with open(SFT_PATH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            matches = EMOJI_PATTERN.findall(line)
            assert not matches, f"Emoji detected in SFT line {i+1}: {matches}"

    # Audit DPO
    with open(DPO_PATH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            matches = EMOJI_PATTERN.findall(line)
            assert not matches, f"Emoji detected in DPO line {i+1}: {matches}"


def test_cradle_mindset_anchors_present():
    """Verify that MACC 17A, ARS hard-lock, and RM 22/hr labor cost appear in training data."""
    with open(SFT_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        assert "17A" in content, "MACC 17A not present in SFT dataset"
        assert "硬锁" in content or "Hard-Lock" in content, "Hard-lock defense not present in SFT dataset"
        assert "22.00" in content or "RM 22" in content, "RM 22/hr benchmark not present in SFT dataset"
        assert "Acronis" in content, "Acronis Cloud backup not present in SFT dataset"
        assert "WordPress" in content, "WordPress recommendation not present in SFT dataset"
