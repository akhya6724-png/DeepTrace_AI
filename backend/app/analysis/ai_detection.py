"""ONNX-based AI-generated image detector for DeepTrace AI."""

import os
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

MODEL_PATH = Path(
    os.environ.get(
        "DEEPTRACE_AI_MODEL_PATH",
        str(Path(__file__).resolve().parents[2] / "models" / "model_int8.onnx"),
    )
)

GENERIC_LIMITATIONS = [
    "This model estimates AI-generated image likelihood; it does not prove authenticity.",
    "The reported confidence is a model score, not a calibrated probability.",
    "Performance can vary on unfamiliar generators, edited images, screenshots, and heavily compressed images.",
    "The INT8 quantized model may differ from the full-precision model.",
    "Metadata and ELA alone cannot reliably determine whether an image was AI-generated.",
]


@lru_cache(maxsize=1)
def _load_session(model_path: str):
    import onnxruntime as ort  # imported lazily so the API still starts without it

    if not Path(model_path).is_file():
        raise FileNotFoundError("ONNX detector model file was not found.")
    return ort.InferenceSession(
        model_path,
        providers=["CPUExecutionProvider"],
    )


class ONNXImageDetector:
    name = "CommunityForensics DeepfakeDet-ViT (ONNX INT8)"

    def describe(self) -> dict:
        import onnxruntime as ort

        return {
            "name": self.name,
            "model_file": MODEL_PATH.name,
            "runtime": f"ONNX Runtime {ort.__version__}",
            "provider": "CPUExecutionProvider",
            "input_size": "384x384 RGB",
            "score_semantics": "Sigmoid-transformed model score for AI-generated/fake likelihood; not calibrated.",
            "license": "MIT",
        }

    def detect(self, image: Image.Image) -> dict:
        session = _load_session(str(MODEL_PATH.resolve()))

        image = ImageOps.exif_transpose(image).convert("RGB")
        width, height = image.size
        if width < 1 or height < 1:
            raise ValueError("Invalid image dimensions.")

        # Model card preprocessing: shortest edge 440, preserve aspect ratio,
        # center crop 384x384, then CLIP normalization.
        scale = 440.0 / min(width, height)
        resized = image.resize(
            (max(384, round(width * scale)), max(384, round(height * scale))),
            Image.Resampling.BICUBIC,
        )

        left = (resized.width - 384) // 2
        top = (resized.height - 384) // 2
        cropped = resized.crop((left, top, left + 384, top + 384))

        array = np.asarray(cropped, dtype=np.float32) / 255.0
        mean = np.array([0.4815, 0.4578, 0.4080], dtype=np.float32)
        std = np.array([0.2686, 0.2613, 0.2750], dtype=np.float32)
        array = (array - mean) / std
        tensor = np.expand_dims(array.transpose(2, 0, 1), axis=0).astype(np.float32)

        input_info = session.get_inputs()[0]
        output_info = session.get_outputs()[0]
        if input_info.name != "pixel_values":
            raise RuntimeError("Unexpected ONNX input; expected pixel_values.")
        if output_info.name != "logits":
            raise RuntimeError("Unexpected ONNX output; expected logits.")

        logits = session.run([output_info.name], {input_info.name: tensor})[0]
        logit = float(np.asarray(logits).reshape(-1)[0])

        # Numerically stable sigmoid.
        if logit >= 0:
            score = 1.0 / (1.0 + np.exp(-logit))
        else:
            exp_value = np.exp(logit)
            score = exp_value / (1.0 + exp_value)

        score = float(np.clip(score, 0.0, 1.0))
        prediction = "ai_generated_likely" if score >= 0.5 else "real_image_likely"

        return {
            "prediction": prediction,
            "confidence": round(score, 6),
            "explanation": (
                f"The model returned an AI-generated/fake likelihood score of {score:.3f}. "
                "This is a model score, not a calibrated probability or proof of authenticity."
            ),
            "limitations": list(GENERIC_LIMITATIONS),
        }


DETECTORS = {
    "onnx": ONNXImageDetector,
    "communityforensics": ONNXImageDetector,
}


def detector_ready() -> bool:
    """True only if the runtime is importable and the model file exists (no inference is run)."""
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False
    return MODEL_PATH.is_file()


def _unavailable(explanation: str) -> dict:
    return {
        "status": "unavailable",
        "prediction": None,
        "confidence": None,
        "method": None,
        "detector": None,
        "error": None,
        "explanation": explanation,
        "limitations": list(GENERIC_LIMITATIONS),
    }


def run_ai_detection(image: Image.Image, detector_name: str = "none") -> dict:
    if detector_name in ("", "none"):
        return _unavailable("No AI-image detector is configured.")

    factory = DETECTORS.get(detector_name)
    if factory is None:
        return _unavailable(
            f"The configured detector '{detector_name}' is not registered."
        )

    try:
        detector = factory()
        output = detector.detect(image)
        return {
            "status": "ok",
            "prediction": output["prediction"],
            "confidence": output["confidence"],
            "method": detector.name,
            "detector": detector.describe(),
            "error": None,
            "explanation": output["explanation"],
            "limitations": list(output.get("limitations", [])),
        }
    except (ImportError, FileNotFoundError) as exc:
        # Missing runtime or model file: the detector is not usable, which is not an inference error.
        reason = (
            "The ONNX Runtime package is not installed (pip install onnxruntime)."
            if isinstance(exc, ImportError)
            else "The detector model file was not found in backend/models."
        )
        return _unavailable(f"AI-image detection was not performed. {reason}")
    except Exception as exc:
        result = _unavailable("The configured AI detector failed to run.")
        result.update({"status": "error", "error": type(exc).__name__})
        return result
