"""Reusable Spanish -> Otomi inference for a future Flet front end.

Approved exact matches are returned immediately. Unseen text uses the trained
ByT5 LoRA adapter, when available. No synthetic confidence score is invented.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "dataset_conjunto_definitivo_es_otomi.csv"
DEFAULT_MODEL = ROOT / "runs" / "byt5_lora" / "modelo_final"
VARIANTS = {"santiago_mexquititlan", "san_ilde_tultepec"}
UNITS = {"lexico", "oracion"}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text).casefold()).strip()


class OtomiTranslator:
    def __init__(self, model_dir: Path = DEFAULT_MODEL):
        self.model_dir = Path(model_dir)
        self.lookup = {}
        with DATA.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                key = (row["variante_id"], row["tipo_unidad"], normalize(row["espanol"]))
                if key in self.lookup and self.lookup[key] != row["otomi"]:
                    raise ValueError(f"Traducciones contradictorias para {key}")
                self.lookup[key] = row["otomi"]
        self.model = None
        self.tokenizer = None
        self.device = None
        self.config = None

    def _load_model(self):
        if self.model is not None:
            return
        config_file = self.model_dir / "otomi_config.json"
        if not config_file.is_file():
            raise FileNotFoundError(f"Falta el adaptador entrenado: {config_file}")
        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as error:
            raise RuntimeError("Instala requirements-training.txt para inferencia neuronal") from error
        self.config = json.loads(config_file.read_text(encoding="utf-8"))
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        base = AutoModelForSeq2SeqLM.from_pretrained(self.config["base_model"])
        self.model = PeftModel.from_pretrained(base, self.model_dir).to(self.device).eval()
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)

    def translate(self, text: str, variant: str, unit: str = "lexico") -> dict:
        if variant not in VARIANTS or unit not in UNITS:
            raise ValueError("Variante o tipo de unidad desconocidos")
        text = unicodedata.normalize("NFC", text.strip())
        if not text:
            return {"otomi": "", "metodo": "vacio", "variante_id": variant, "tipo_unidad": unit}
        key = (variant, unit, normalize(text))
        if key in self.lookup:
            return {"otomi": self.lookup[key], "metodo": "diccionario_confirmado",
                    "variante_id": variant, "tipo_unidad": unit}
        if variant == "santiago_mexquititlan" and unit == "oracion":
            return {"otomi": "", "metodo": "sin_cobertura",
                    "aviso": "El corpus no contiene oraciones paralelas de Santiago Mexquititlán.",
                    "variante_id": variant, "tipo_unidad": unit}
        self._load_model()
        import torch
        tagged = f"<{variant}><{unit}> {text}"
        inputs = self.tokenizer(tagged, return_tensors="pt", truncation=True,
                                max_length=self.config["max_source"]).to(self.device)
        with torch.inference_mode():
            output = self.model.generate(**inputs, max_new_tokens=self.config["max_target"],
                                         num_beams=2, do_sample=False)
        return {"otomi": self.tokenizer.decode(output[0], skip_special_tokens=True),
                "metodo": "modelo_experimental", "variante_id": variant, "tipo_unidad": unit}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("texto")
    parser.add_argument("--variante", choices=sorted(VARIANTS), required=True)
    parser.add_argument("--tipo", choices=sorted(UNITS), default="lexico")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args()
    try:
        result = OtomiTranslator(args.model_dir).translate(args.texto, args.variante, args.tipo)
    except (FileNotFoundError, RuntimeError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
