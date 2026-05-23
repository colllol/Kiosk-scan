from pathlib import Path

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets" / "document.yaml"
RUNS = ROOT / "runs"


def main() -> None:
    model = YOLO("yolov8n.pt")
    model.train(
        data=str(DATASET),
        epochs=80,
        imgsz=640,
        batch=16,
        project=str(RUNS),
        name="document-yolo",
        single_cls=True,
    )


if __name__ == "__main__":
    main()
