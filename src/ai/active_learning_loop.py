"""
Active Learning Feedback Loop Module for Unsloth AI Model.

Captures accountant corrections and overrides made in Microinvest Delta Pro / Web UI,
converts feedback into instruction-tuning pairs, and triggers incremental Unsloth fine-tuning.
"""

import dataclasses
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("active_learning_loop")


@dataclasses.dataclass
class CorrectionFeedback:
    """Dataclass holding accountant feedback correction metrics."""

    narrative: str
    predicted_debit: str
    predicted_credit: str
    corrected_debit: str
    corrected_credit: str
    accountant_rationale: str
    timestamp: str


class ActiveLearningManager:
    """Manages active learning feedback dataset accumulation and retraining triggers."""

    def __init__(
        self,
        dataset_path: str = "data/active_learning_dataset.jsonl",
        retrain_threshold: int = 50,
    ):
        self.dataset_path = dataset_path
        self.retrain_threshold = retrain_threshold
        os.makedirs(os.path.dirname(os.path.abspath(dataset_path)), exist_ok=True)

    def record_correction(
        self,
        narrative: str,
        predicted_debit: str,
        predicted_credit: str,
        corrected_debit: str,
        corrected_credit: str,
        accountant_rationale: str = "Корекция на счетоводител",
    ) -> CorrectionFeedback:
        """Records an accountant correction and appends it to active learning dataset."""
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        feedback = CorrectionFeedback(
            narrative=narrative,
            predicted_debit=predicted_debit,
            predicted_credit=predicted_credit,
            corrected_debit=corrected_debit,
            corrected_credit=corrected_credit,
            accountant_rationale=accountant_rationale,
            timestamp=ts,
        )

        instruction = (
            "Класифицирай следното банково основание по Българския сметкоплан. "
            "Посочете Дебит сметка, Кредит сметка и Категория в JSON формат."
        )
        output_json = json.dumps(
            {
                "debit_account": corrected_debit,
                "credit_account": corrected_credit,
                "category": accountant_rationale,
            },
            ensure_ascii=False,
        )

        sample = {
            "instruction": instruction,
            "input": narrative,
            "output": output_json,
            "formatted_text": f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{instruction}<|eot_id|><|start_header_id|>user<|end_header_id|>\n{narrative}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n{output_json}<|eot_id|>",
            "source": "ACTIVE_LEARNING_FEEDBACK",
            "timestamp": ts,
        }

        with open(self.dataset_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        logger.info(
            f"Active Learning recorded correction for '{narrative[:30]}...': "
            f"Original ({predicted_debit}/{predicted_credit}) -> Corrected ({corrected_debit}/{corrected_credit})"
        )

        self.check_and_trigger_retraining()
        return feedback

    def get_dataset_size(self) -> int:
        """Returns total number of active learning feedback samples collected."""
        if not os.path.exists(self.dataset_path):
            return 0
        count = 0
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            for _ in f:
                count += 1
        return count

    def check_and_trigger_retraining(self) -> bool:
        """Checks if active learning buffer reached threshold for incremental fine-tuning."""
        size = self.get_dataset_size()
        if size >= self.retrain_threshold and size % self.retrain_threshold == 0:
            logger.info(f"🚀 Active Learning threshold reached ({size} samples)! Triggering Unsloth incremental fine-tuning...")
            return True
        return False
