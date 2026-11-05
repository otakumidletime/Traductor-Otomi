"""Check or fine-tune a tagged Spanish→Otomí ByT5 baseline.

Default: validate the three joint JSONL splits only.
With --train: download google/byt5-small, train on the tagged inputs, select
the best validation-loss checkpoint, then evaluate the held-out test once.
"""
from __future__ import annotations

import argparse
import csv
import inspect
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent / "data"
FILES = {
    "train": HERE / "dataset_conjunto_entrenamiento.jsonl",
    "validation": HERE / "dataset_conjunto_validacion.jsonl",
    "test": HERE / "dataset_conjunto_test.jsonl",
}


def norm(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value).casefold()).strip()


def check_data():
    data = {}
    for split, path in FILES.items():
        with path.open(encoding="utf-8") as handle:
            data[split] = [json.loads(line) for line in handle if line.strip()]
        assert data[split], f"Empty split: {split}"
        for item in data[split]:
            assert item["input_text"] and item["target_text"]
            assert item["input_text"] == f"<{item['variante_id']}><{item['tipo_unidad']}> {item['espanol']}"
            assert item["target_text"] == item["otomi"]
            assert item["variante_id"] in {"santiago_mexquititlan", "san_ilde_tultepec"}
            assert item["tipo_unidad"] in {"lexico", "oracion"}
            assert "pruebaespanol" not in item["espanol"].casefold()
    assert sum(map(len, data.values())) == 415
    splits = defaultdict(set)
    for split, items in data.items():
        for item in items:
            splits[norm(item["espanol"])].add(split)
    assert all(len(value) == 1 for value in splits.values())
    return data


def train_model(output_dir, epochs, allow_cpu):
    try:
        import torch
        from datasets import load_dataset
        from transformers import (
            AutoModelForSeq2SeqLM, AutoTokenizer, DataCollatorForSeq2Seq,
            Seq2SeqTrainer, Seq2SeqTrainingArguments,
        )
    except ImportError as error:
        raise SystemExit("Instala torch, datasets, transformers y accelerate en un entorno virtual.") from error
    if not torch.cuda.is_available() and not allow_cpu:
        raise SystemExit("No se detectó GPU CUDA. Usa --allow-cpu para aceptar un entrenamiento mucho más lento.")

    dataset = load_dataset("json", data_files={split: str(path) for split, path in FILES.items()})
    tokenizer = AutoTokenizer.from_pretrained("google/byt5-small")
    model = AutoModelForSeq2SeqLM.from_pretrained("google/byt5-small")

    def encode(batch):
        inputs = tokenizer(batch["input_text"], max_length=192, truncation=True)
        inputs["labels"] = tokenizer(text_target=batch["target_text"], max_length=128, truncation=True)["input_ids"]
        return inputs

    tokenized = dataset.map(encode, batched=True, remove_columns=dataset["train"].column_names)
    params = {
        "output_dir": str(output_dir), "per_device_train_batch_size": 2,
        "per_device_eval_batch_size": 2, "gradient_accumulation_steps": 4,
        "learning_rate": 1e-4, "num_train_epochs": epochs,
        "logging_strategy": "epoch", "save_strategy": "epoch",
        "save_total_limit": 2, "load_best_model_at_end": True,
        "metric_for_best_model": "eval_loss", "greater_is_better": False,
        "predict_with_generate": True, "generation_max_length": 128,
        "report_to": "none", "seed": 42, "data_seed": 42,
        "push_to_hub": False,
    }
    arg_names = inspect.signature(Seq2SeqTrainingArguments).parameters
    params["eval_strategy" if "eval_strategy" in arg_names else "evaluation_strategy"] = "epoch"
    args = Seq2SeqTrainingArguments(**params)
    settings = {
        "model": model, "args": args,
        "data_collator": DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model),
        "train_dataset": tokenized["train"], "eval_dataset": tokenized["validation"],
    }
    trainer_names = inspect.signature(Seq2SeqTrainer).parameters
    settings["processing_class" if "processing_class" in trainer_names else "tokenizer"] = tokenizer
    trainer = Seq2SeqTrainer(**settings)
    trainer.train()
    output_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(output_dir / "modelo_final"))
    tokenizer.save_pretrained(str(output_dir / "modelo_final"))

    result = trainer.predict(tokenized["test"])
    predictions = tokenizer.batch_decode(result.predictions, skip_special_tokens=True)
    test_items = list(dataset["test"])
    details = []
    by_group = defaultdict(list)
    for item, predicted in zip(test_items, predictions):
        correct = norm(item["target_text"]) == norm(predicted)
        group = (item["variante_id"], item["tipo_unidad"])
        by_group[group].append(correct)
        details.append({
            "id": item["id"], "variante_id": group[0], "tipo_unidad": group[1],
            "espanol": item["espanol"], "otomi_referencia": item["target_text"],
            "otomi_prediccion": predicted, "coincidencia_exacta": correct,
        })
    with (output_dir / "predicciones_test.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(details[0]))
        writer.writeheader()
        writer.writerows(details)
    summary = {
        "modelo_base": "google/byt5-small",
        "particiones": {split: len(dataset[split]) for split in FILES},
        "coincidencia_exacta_por_grupo": {
            f"{variant}/{unit}": {"aciertos": sum(values), "total": len(values), "fraccion": sum(values) / len(values)}
            for (variant, unit), values in by_group.items()
        },
        "metricas_modelo": result.metrics,
    }
    (output_dir / "metricas_test.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(summary["coincidencia_exacta_por_grupo"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--epochs", type=float, default=5)
    parser.add_argument("--output-dir", type=Path, default=HERE.parent / "work" / "modelo_byt5_conjunto")
    args = parser.parse_args()
    data = check_data()
    print("Corpus conjunto correcto:", {split: len(items) for split, items in data.items()})
    print("Variedad y tipo:", dict(Counter((item["variante_id"], item["tipo_unidad"]) for items in data.values() for item in items)))
    if args.train:
        train_model(args.output_dir, args.epochs, args.allow_cpu)


if __name__ == "__main__":
    main()
