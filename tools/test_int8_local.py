import time
import numpy as np
import onnxruntime as ort
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer


# INT8 모델 상수
MODEL_ID = "user0074/voice-phishing-koelectra"
MODEL_SUBFOLDER = "koelectra_v1_onnx_int8"
MODEL_FILE = "model_quantized.onnx"

MAX_LENGTH = 128

LABELS = {
    0: "normal",
    1: "voice_phishing",
}


# Hugging Face에서 INT8 폴더만 다운로드
local_dir = snapshot_download(
    repo_id=MODEL_ID,
    allow_patterns=[
        f"{MODEL_SUBFOLDER}/*",
    ],
)

model_dir = f"{local_dir}/{MODEL_SUBFOLDER}"

tokenizer = AutoTokenizer.from_pretrained(model_dir)

session = ort.InferenceSession(
    f"{model_dir}/{MODEL_FILE}",
    providers=["CPUExecutionProvider"],
)

text = "검찰청 직원이라며 안전한 계좌로 돈을 이체하라고 요구했습니다."

encoded = tokenizer(
    text,
    max_length=MAX_LENGTH,
    padding="max_length",
    truncation=True,
    return_tensors="np",
)

inputs = {}

for item in session.get_inputs():
    if item.name in encoded:
        inputs[item.name] = encoded[item.name].astype(np.int64)

start = time.perf_counter()

outputs = session.run(None, inputs)

elapsed_ms = (time.perf_counter() - start) * 1000

logits = outputs[0][0]

probabilities = np.exp(logits - np.max(logits))
probabilities = probabilities / probabilities.sum()

predicted_id = int(np.argmax(probabilities))

print("model:", MODEL_ID)
print("model_type: ONNX INT8")
print("predicted_label:", LABELS[predicted_id])
print("suspicion_score:", round(float(probabilities[1]), 6))
print("latency_ms:", round(elapsed_ms, 2))
print("input_names:", [item.name for item in session.get_inputs()])