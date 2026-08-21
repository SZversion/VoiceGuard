# Whisper LoRA P0/T2 Drive 데이터 재학습

## Why

청크 음성은 `data_chunked_30s_overlap10_v2`, 라벨은 `30s_overlap10_label_v3`로 분리되어 있어 기존 같은 폴더 탐색 방식으로는 학습 쌍을 만들 수 없다.

## Goal

- Drive의 음성·라벨 폴더를 복사하지 않고 상대 경로와 파일명으로 매칭한다.
- P0/T2 설정으로 train·validation·test를 원본 통화 단위로 분리한다.
- 빈 라벨과 매칭 실패 파일을 학습 전에 보고한다.

## What

- 음성 루트와 라벨 루트의 하위 폴더 구조가 동일하다고 가정한다.
- 같은 상대 경로와 stem을 가진 WAV/TXT만 학습 쌍으로 사용한다.
- 라벨이 비어 있거나 없으면 이슈로 기록하고 학습에서 제외한다.

## How

- `discover_pairs(..., text_root=...)`가 별도 라벨 루트를 탐색한다.
- `train_whisper_lora.py --data AUDIO_ROOT --labels LABEL_ROOT`로 실행한다.
- `group_by_source=true`를 사용해 overlap 청크가 서로 다른 split에 섞이지 않게 한다.

## AC

- Given 동일한 상대 경로의 음성·TXT가 두 루트에 있을 때, When manifest를 생성하면, Then 하나의 유효한 pair로 기록된다.
- Given 음성에 대응하는 TXT가 없을 때, When manifest를 생성하면, Then `missing_text` 이슈로 기록되고 pair에서 제외된다.
- Given 같은 원본 통화의 청크들이 있을 때, When split을 수행하면, Then 모든 청크가 하나의 split에만 포함된다.
