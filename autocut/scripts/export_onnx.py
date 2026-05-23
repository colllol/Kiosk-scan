from pathlib import Path

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]
ROOT_WEIGHTS = ROOT / "best.pt"
TRAINED_WEIGHTS = ROOT / "runs" / "document-yolo" / "weights" / "best.pt"
PUBLIC_MODELS = ROOT / "models"


def main() -> None:
    weights = ROOT_WEIGHTS if ROOT_WEIGHTS.exists() else TRAINED_WEIGHTS
    PUBLIC_MODELS.mkdir(exist_ok=True)
    model = YOLO(str(weights))
    exported = Path(model.export(format="onnx", imgsz=640, simplify=True, opset=12))
    target = PUBLIC_MODELS / "document-yolo.onnx"
    target.write_bytes(exported.read_bytes())
    print(f"Exported {target}")


if __name__ == "__main__":
    main()
