"""Train and evaluate Spanish -> Otomi sequence-to-sequence models.

The default command validates the corpus. --baseline evaluates a train-only
character retrieval baseline on validation. --train fine-tunes on train,
selects the best checkpoint on validation loss, then evaluates test once.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import inspect
import json
import platform
import random
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CSV_FILE = DATA / "dataset_conjunto_definitivo_es_otomi.csv"
FILES = {
    "train": DATA / "dataset_conjunto_entrenamiento.jsonl",
    "validation": DATA / "dataset_conjunto_validacion.jsonl",
    "test": DATA / "dataset_conjunto_test.jsonl",
}
EXPECTED = {"train": 341, "validation": 36, "test": 38}
VARIANTS = {"santiago_mexquititlan", "san_ilde_tultepec"}
UNITS = {"lexico", "oracion"}
MODEL_NAME = "google/byt5-small"


def model_input(row: dict, input_format: str) -> str:
    if input_format == "tagged":
        return row["input_text"]
    variant = ("Santiago Mexquititlán" if row["variante_id"] == "santiago_mexquititlan"
               else "San Ildefonso Tultepec")
    unit = "palabra" if row["tipo_unidad"] == "lexico" else "oración"
    return f"español a otomí de {variant}, {unit}: {row['espanol']}"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text).casefold()).strip()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_data(max_source: int, max_target: int):
    with CSV_FILE.open(encoding="utf-8-sig", newline="") as stream:
        master = list(csv.DictReader(stream))
    if len(master) != 415:
        raise ValueError(f"CSV: se esperaban 415 filas; hay {len(master)}")
    by_id = {row["id"]: row for row in master}
    if len(by_id) != len(master):
        raise ValueError("Hay IDs duplicados en el CSV")

    data = {}
    seen = set()
    spanish_splits = defaultdict(set)
    narrative_splits = defaultdict(set)
    for split, path in FILES.items():
        with path.open(encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream if line.strip()]
        if len(rows) != EXPECTED[split]:
            raise ValueError(f"{split}: se esperaban {EXPECTED[split]} filas; hay {len(rows)}")
        for row in rows:
            row_id = row["id"]
            if row_id in seen or row_id not in by_id:
                raise ValueError(f"ID duplicado o ausente: {row_id}")
            seen.add(row_id)
            source = by_id[row_id]
            variant, unit = row["variante_id"], row["tipo_unidad"]
            if variant not in VARIANTS or unit not in UNITS:
                raise ValueError(f"Etiqueta desconocida: {row_id}")
            expected_input = f"<{variant}><{unit}> {row['espanol']}"
            if (row["input_text"] != expected_input or row["target_text"] != row["otomi"]
                    or row["espanol"] != source["espanol"] or row["otomi"] != source["otomi"]
                    or source["split"] != {"train": "entrenamiento", "validation": "validacion", "test": "test"}[split]):
                raise ValueError(f"CSV y JSONL no concuerdan: {row_id}")
            for field in ("espanol", "otomi", "input_text", "target_text"):
                if not row[field] or "\ufffd" in row[field] or unicodedata.normalize("NFC", row[field]) != row[field]:
                    raise ValueError(f"Texto vacío, corrupto o no NFC: {row_id}/{field}")
            if len(row["input_text"].encode("utf-8")) + 1 > max_source:
                raise ValueError(f"Entrada mayor que --max-source: {row_id}")
            if len(row["target_text"].encode("utf-8")) + 1 > max_target:
                raise ValueError(f"Salida mayor que --max-target: {row_id}")
            spanish_splits[normalize(row["espanol"])].add(split)
            if source.get("texto_corpus"):
                narrative_splits[source["texto_corpus"]].add(split)
        data[split] = rows
    if len(seen) != 415 or any(len(s) != 1 for s in spanish_splits.values()):
        raise ValueError("IDs faltantes o español compartido entre particiones")
    if any(len(s) != 1 for s in narrative_splits.values()):
        raise ValueError("Un texto narrativo cruza particiones")
    return data


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, char_a in enumerate(a, 1):
        curr = [i]
        for j, char_b in enumerate(b, 1):
            curr.append(min(curr[-1] + 1, prev[j] + 1, prev[j - 1] + (char_a != char_b)))
        prev = curr
    return prev[-1]


def score_rows(rows: list[dict]) -> dict:
    groups = defaultdict(list)
    for row in rows:
        groups[(row["variante_id"], row["tipo_unidad"])].append(row)
    groups[("TOTAL", "TOTAL")] = rows
    output = {}
    for (variant, unit), items in groups.items():
        exact = sum(normalize(r["prediccion"]) == normalize(r["referencia"]) for r in items)
        errors = sum(edit_distance(normalize(r["prediccion"]), normalize(r["referencia"])) for r in items)
        chars = sum(len(normalize(r["referencia"])) for r in items)
        output[f"{variant}/{unit}"] = {
            "aciertos_exactos": exact, "total": len(items),
            "cer": round(errors / max(chars, 1), 4),
        }
    try:
        from sacrebleu.metrics import CHRF
    except ImportError:
        return output
    chrf = CHRF(word_order=0)
    for (variant, unit), items in groups.items():
        output[f"{variant}/{unit}"]["chrf"] = round(
            chrf.corpus_score([r["prediccion"] for r in items],
                              [[r["referencia"] for r in items]]).score, 2)
    return output


def evaluate_baseline(data: dict) -> dict:
    """Train-only nearest-neighbour baseline; never fit on validation/test."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    train, validation = data["train"], data["validation"]
    results = []
    for variant, unit in sorted({(r["variante_id"], r["tipo_unidad"]) for r in validation}):
        examples = [r for r in train if (r["variante_id"], r["tipo_unidad"]) == (variant, unit)]
        queries = [r for r in validation if (r["variante_id"], r["tipo_unidad"]) == (variant, unit)]
        vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 5), lowercase=False)
        matrix = vectorizer.fit_transform([normalize(r["espanol"]) for r in examples])
        similarities = (vectorizer.transform([normalize(r["espanol"]) for r in queries]) @ matrix.T).toarray()
        for row, sims in zip(queries, similarities):
            index = int(sims.argmax())
            results.append({"id": row["id"], "variante_id": variant, "tipo_unidad": unit,
                            "referencia": row["otomi"], "prediccion": examples[index]["otomi"],
                            "similitud_entrada": round(float(sims[index]), 4)})
    return {"solo_validacion": score_rows(results), "detalle": results}


def write_predictions(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["id", "variante_id", "tipo_unidad", "espanol", "referencia", "prediccion"])
        writer.writeheader()
        writer.writerows(rows)


def train(args, data: dict) -> None:
    try:
        import torch
        import transformers
        from datasets import load_dataset
        from peft import LoraConfig, TaskType, get_peft_model
        from transformers import (AutoModelForSeq2SeqLM, AutoTokenizer, DataCollatorForSeq2Seq,
                                  EarlyStoppingCallback, Seq2SeqTrainer, Seq2SeqTrainingArguments, set_seed)
    except ImportError as error:
        raise SystemExit("Faltan paquetes. Instala requirements-training.txt en un entorno virtual.") from error

    if not torch.cuda.is_available() and not args.allow_cpu:
        raise SystemExit("No se detectó CUDA. Usa --allow-cpu solo si aceptas un ajuste mucho más lento.")
    final_dir = args.output_dir / "modelo_final"
    if final_dir.exists():
        raise SystemExit(f"Ya existe un modelo en {final_dir}; usa otro --output-dir")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    set_seed(args.seed)
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    low_memory_dtype = (torch.bfloat16 if args.full_finetune and torch.cuda.is_available()
                        and torch.cuda.is_bf16_supported() else None)
    model = (AutoModelForSeq2SeqLM.from_pretrained(args.model_name, dtype=low_memory_dtype)
             if low_memory_dtype is not None else AutoModelForSeq2SeqLM.from_pretrained(args.model_name))
    model.config.use_cache = False
    if not args.full_finetune:
        lora = LoraConfig(task_type=TaskType.SEQ_2_SEQ_LM, inference_mode=False,
                          r=8, lora_alpha=32, lora_dropout=0.1, target_modules=["q", "v"])
        model = get_peft_model(model, lora)
        if hasattr(model, "enable_input_require_grads"):
            model.enable_input_require_grads()
        model.print_trainable_parameters()
    else:
        print("Ajuste completo:", sum(p.numel() for p in model.parameters() if p.requires_grad), "parámetros")

    dataset = load_dataset("json", data_files={key: str(path) for key, path in FILES.items()})

    for split_rows in data.values():
        for row in split_rows:
            source_tokens = len(tokenizer(model_input(row, args.input_format)).input_ids)
            target_tokens = len(tokenizer(text_target=row["target_text"]).input_ids)
            if source_tokens > args.max_source or target_tokens > args.max_target:
                raise ValueError(f"Límite de tokens insuficiente para {row['id']}: {source_tokens}/{target_tokens}")

    def encode(batch):
        formatted = [model_input({key: values[index] for key, values in batch.items()}, args.input_format)
                     for index in range(len(batch["espanol"]))]
        encoded = tokenizer(formatted, max_length=args.max_source, truncation=True)
        encoded["labels"] = tokenizer(text_target=batch["target_text"],
                                       max_length=args.max_target, truncation=True)["input_ids"]
        return encoded

    tokenized = dataset.map(encode, batched=True, remove_columns=dataset["train"].column_names)
    bf16 = bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported())
    params = dict(output_dir=str(args.output_dir / "checkpoints"),
                  per_device_train_batch_size=1, per_device_eval_batch_size=1,
                  gradient_accumulation_steps=8, learning_rate=args.learning_rate,
                  num_train_epochs=args.epochs, optim="adafactor", gradient_checkpointing=True,
                  logging_strategy="epoch", save_strategy="epoch", save_total_limit=2,
                  load_best_model_at_end=True, metric_for_best_model="eval_loss",
                  greater_is_better=False, predict_with_generate=False,
                  bf16=bf16, fp16=bool(torch.cuda.is_available() and not bf16),
                  report_to="none", seed=args.seed, data_seed=args.seed, push_to_hub=False)
    arg_names = inspect.signature(Seq2SeqTrainingArguments).parameters
    params["eval_strategy" if "eval_strategy" in arg_names else "evaluation_strategy"] = "epoch"
    if "gradient_checkpointing_kwargs" in arg_names:
        params["gradient_checkpointing_kwargs"] = {"use_reentrant": False}
    if "torch_empty_cache_steps" in arg_names:
        params["torch_empty_cache_steps"] = args.empty_cache_steps
    training_args = Seq2SeqTrainingArguments(**params)
    trainer_args = dict(model=model, args=training_args,
                        train_dataset=tokenized["train"], eval_dataset=tokenized["validation"],
                        data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model),
                        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)])
    trainer_names = inspect.signature(Seq2SeqTrainer).parameters
    trainer_args["processing_class" if "processing_class" in trainer_names else "tokenizer"] = tokenizer
    trainer = Seq2SeqTrainer(**trainer_args)
    try:
        train_result = trainer.train(resume_from_checkpoint=str(args.resume_from_checkpoint) if args.resume_from_checkpoint else None)
    except RuntimeError as error:
        if "out of memory" in str(error).lower():
            free, total = torch.cuda.mem_get_info() if torch.cuda.is_available() else (0, 0)
            raise SystemExit(f"GPU sin memoria para {args.model_name}: {error}. Libre ahora: {free // 2**20} de {total // 2**20} MiB. Cierra otras apps de GPU o usa una GPU mayor.") from error
        raise
    model.gradient_checkpointing_disable()
    model.config.use_cache = True
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device).eval()

    def predict(items):
        predictions = []
        for item in items:
            inputs = tokenizer(model_input(item, args.input_format), return_tensors="pt", max_length=args.max_source,
                               truncation=True).to(device)
            with torch.inference_mode():
                tokens = model.generate(**inputs, max_new_tokens=args.max_target,
                                        num_beams=2, do_sample=False)
            predictions.append({"id": item["id"], "variante_id": item["variante_id"],
                                "tipo_unidad": item["tipo_unidad"], "espanol": item["espanol"],
                                "referencia": item["otomi"],
                                "prediccion": tokenizer.decode(tokens[0], skip_special_tokens=True)})
        return predictions

    val_predictions = predict(data["validation"])
    test_predictions = predict(data["test"])
    write_predictions(args.output_dir / "predicciones_validacion.csv", val_predictions)
    write_predictions(args.output_dir / "predicciones_test.csv", test_predictions)
    report = {
        "base_model": args.model_name,
        "input_format": args.input_format,
        "tuning_mode": "full" if args.full_finetune else "lora_qv_r8_alpha32",
        "python": platform.python_version(), "torch": torch.__version__,
        "transformers": transformers.__version__, "cuda": torch.cuda.is_available(),
        "weight_dtype": str(low_memory_dtype or torch.float32),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "data_sha256": {name: file_sha256(path) for name, path in {"csv": CSV_FILE, **FILES}.items()},
        "counts": {name: len(items) for name, items in data.items()},
        "train_metrics": train_result.metrics,
        "validation": score_rows(val_predictions), "test": score_rows(test_predictions),
        "warning": "Santiago Mexquititlan has no sentence examples; sentence quality there is unmeasured.",
    }
    (args.output_dir / "metricas.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (final_dir / "otomi_config.json").write_text(json.dumps({"base_model": args.model_name,
            "tuning_mode": "full" if args.full_finetune else "lora",
            "input_format": args.input_format,
            "max_source": args.max_source, "max_target": args.max_target}, indent=2), encoding="utf-8")
    print(json.dumps({"validation": report["validation"], "test": report["test"]}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--baseline", action="store_true", help="Evalúa vecino más cercano solo en validación")
    mode.add_argument("--train", action="store_true", help="Ajusta el modelo y evalúa prueba una vez")
    parser.add_argument("--full-finetune", action="store_true", help="Ajusta todos los pesos en vez de LoRA; requiere más disco y GPU")
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-source", type=int, default=128)
    parser.add_argument("--max-target", type=int, default=80)
    parser.add_argument("--model-name", default=MODEL_NAME)
    parser.add_argument("--input-format", choices=("tagged", "natural"), default="tagged")
    parser.add_argument("--resume-from-checkpoint", type=Path)
    parser.add_argument("--empty-cache-steps", type=int, default=10)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.output_dir is None:
        args.output_dir = ROOT / "runs" / ("byt5_full" if args.full_finetune else "byt5_lora")
    data = read_data(args.max_source, args.max_target)
    print("Corpus verificado:", {key: len(value) for key, value in data.items()})
    print("Grupos:", dict(Counter((row["variante_id"], row["tipo_unidad"])
                                  for items in data.values() for row in items)))
    if args.baseline:
        baseline = evaluate_baseline(data)
        print(json.dumps(baseline["solo_validacion"], ensure_ascii=False, indent=2))
    if args.train:
        train(args, data)


if __name__ == "__main__":
    main()
