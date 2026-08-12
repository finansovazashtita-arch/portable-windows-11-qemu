"""
Unsloth.ai Fine-Tuning & Dataset Generator Module for Bulgarian Double-Entry Accounting.

Generates 1,000+ instruction-tuning samples mapping complex Bulgarian bank narratives
to exact Bulgarian Chart of Accounts codes (503, 401, 411, 501, 621, 602, 421, 4531/4532, 702/703)
and provides Unsloth QLoRA fine-tuning training configurations.
"""

import json
import logging
import os
import random
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("unsloth_finetune")


class BulgarianAccountingDatasetGenerator:
    """Generates instruction-tuning datasets for Bulgarian bank transaction narrative classification."""

    NARRATIVE_TEMPLATES = [
        ("Плащане по фактура № {doc_no} от {vendor} за консумативи и материали", "401", "503", "Доставчици"),
        ("ПОСТЪПЛЕНИЕ ОТ КЛИЕНТ {customer} ПО ФАКТУРА № {doc_no}", "503", "411", "Клиенти"),
        ("БАНКОВА ТАКСА ЗА МЕСЕЧНО ОБСЛУЖВАНЕ НА СМЕТКА № {iban}", "621", "503", "Банкови такси"),
        ("ПЛАЩАНЕ НА НАЕМ ЗА ТЪРГОВСКИ ОБЕКТ ЗА МЕСЕЦ {month}", "602", "503", "Наем"),
        ("ВНОСКА НА ДДС ПО СМЕТКА НА НАП ЗА ПЕРИОД {month}", "4531", "503", "ДДС / Данъци"),
        ("ИЗПЛАЩАНЕ НА ЗАПЛАТИ И ВЪЗНАГРАЖДЕНИЯ НА ПЕРСОНАЛА ЗА МЕСЕЦ {month}", "421", "503", "Персонал / Заплати"),
        ("ТЕГЛЕНЕ НА ВНОСКА В БРОЙ ОТ БАНКОМАТ ИЛИ КАСА", "501", "503", "Каса в лева"),
        ("ПЛАЩАНЕ НА ЛИХВА ПО БАНКОВ КРЕДИТ ДОГОВОР {doc_no}", "621", "503", "Финансови разходи / Лихви"),
        ("ПРОДАЖБА НА СТОКИ И УСЛУГИ В БРОЙ / ПОС ТЕРМИНАЛ", "503", "702", "Приходи от продажби"),
    ]

    VENDORS = ["СТОРГОЗИЯ АД", "ТЕХНОПОЛИС БЪЛГАРИЯ", "ОМВ БЪЛГАРИЯ ООД", "ЛУКОЙЛ БЪЛГАРИЯ", "А1 БЪЛГАРИЯ ЕАД", "ЙЕТТЕЛ БЪЛГАРИЯ"]
    CUSTOMERS = ["ИВАНОВ И СИНОВЕ ООД", "БУЛМАРКЕТ АД", "АЛЬОША 2000 ЕООД", "ПЛЕВЕН СТРОЙ ЕООД", "ВИТАФАРМ ООД"]
    MONTHS = ["ЯНУАРИ", "ФЕВРУАРИ", "МАРТ", "АПРИЛ", "МАЙ", "ЮНИ", "ЮЛИ", "АВГУСТ", "СЕПТЕМВРИ", "ОКТЕМВРИ", "НОЕМВРИ", "ДЕКЕМВРИ"]
    IBANS = ["BG71STSA93000028013479", "BG12UBBS80021000998877", "BG98UNCR70001522334455"]

    def generate_samples(self, count: int = 1000) -> List[Dict[str, str]]:
        """Generates instruction-tuning dictionary samples."""
        samples = []
        for i in range(count):
            tmpl, dt_acc, cr_acc, category = random.choice(self.NARRATIVE_TEMPLATES)
            doc_no = str(random.randint(100000, 999999))
            vendor = random.choice(self.VENDORS)
            customer = random.choice(self.CUSTOMERS)
            month = random.choice(self.MONTHS)
            iban = random.choice(self.IBANS)

            narrative = tmpl.format(doc_no=doc_no, vendor=vendor, customer=customer, month=month, iban=iban)

            instruction = (
                "Класифицирай следното банково основание по Българския сметкоплан. "
                "Посочете Дебит сметка, Кредит сметка и Категория в JSON формат."
            )
            output_json = json.dumps(
                {"debit_account": dt_acc, "credit_account": cr_acc, "category": category},
                ensure_ascii=False,
            )

            samples.append(
                {
                    "instruction": instruction,
                    "input": narrative,
                    "output": output_json,
                    "formatted_text": f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{instruction}<|eot_id|><|start_header_id|>user<|end_header_id|>\n{narrative}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n{output_json}<|eot_id|>",
                }
            )
        return samples

    def export_dataset_jsonl(self, output_path: str, count: int = 1000) -> str:
        """Exports dataset to JSONL format for Unsloth SFTTrainer."""
        samples = self.generate_samples(count=count)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        logger.info(f"Successfully exported {len(samples)} fine-tuning samples to: {output_path}")
        return output_path


class UnslothFineTuner:
    """Configures Unsloth FastLanguageModel fine-tuning hyperparameters."""

    def __init__(self, base_model: str = "unsloth/Llama-3.2-3B-Instruct", max_seq_length: int = 2048):
        self.base_model = base_model
        self.max_seq_length = max_seq_length

    def get_training_config(self) -> Dict[str, Any]:
        """Returns Unsloth QLoRA fine-tuning hyperparameters configuration."""
        return {
            "model_name": self.base_model,
            "max_seq_length": self.max_seq_length,
            "load_in_4bit": True,
            "lora_r": 16,
            "lora_alpha": 16,
            "lora_dropout": 0.0,
            "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            "bias": "none",
            "use_gradient_checkpointing": "unsloth",
            "per_device_train_batch_size": 2,
            "gradient_accumulation_steps": 4,
            "learning_rate": 2e-4,
            "optim": "adamw_8bit",
            "weight_decay": 0.01,
            "lr_scheduler_type": "linear",
            "warmup_steps": 5,
        }
