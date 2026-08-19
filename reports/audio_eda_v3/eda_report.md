# stt_finetuning_cleaned_v3 오디오 전처리 EDA

- 대상: `C:\Users\SZ\Documents\his_voice\stt_finetuning_cleaned_v3`
- manifest: 590행 / 실제 WAV: 590개 / 실제 TXT: 590개 / 디코드 성공: 590개

## 1. 데이터 정합성

- 그룹: {'D03': 461, 'voice_phishing': 129}
- manifest `aligned`: {'True': 590}
- manifest 이름이 디스크에 없음: 0개; 디스크 WAV 이름이 manifest에 없음: 0개
- TXT 동반 여부: 590/590
- TXT에서 삐-/신호음 관련 표기 후보: 14개 파일
- 원본 source 경로 확인 불가: 590/590개 (manifest 경로가 현재 환경에 없음)

## 2. 청킹

- 실제 길이 구간: {'20-30s': 479, '<20s': 111}
- 청크 base 수: 229; base별 청크 수 분포: {2: 27, 12: 1, 4: 8, 6: 10, 3: 22, 7: 6, 9: 2, 8: 5, 15: 1, 18: 2, 5: 8, 10: 2, 11: 2, 1: 133}
- 실제- manifest duration 차이(ms): {'n': 590, 'min': 0.0, 'p05': 0.0, 'median': 0.0, 'p95': 0.0, 'max': 0.0, 'mean': 0.0, 'std': 0.0}
- 20~30초 규칙은 ‘긴 원본을 청킹한 결과’에는 대체로 부합하는지 확인할 수 있지만, 원본이 짧은 마지막 청크인지 여부는 원본 없이는 판정할 수 없습니다.

## 3. WAV 신호 기본 통계

- sample rate: {8000: 461, 16000: 129}; channels: {1: 590}
- RMS dBFS: {'n': 590, 'min': -25.997769269270773, 'p05': -25.497172572440284, 'median': -19.761352973424753, 'p95': -15.080145873024337, 'max': -14.157380590154226, 'mean': -19.949959864066297, 'std': 3.2616674385012794}; peak dBFS: {'n': 590, 'min': -14.497666196272828, 'p05': -6.4860212592299185, 'median': 0.0, 'p95': 0.0, 'max': 0.0, 'mean': -1.1646922468776326, 'std': 2.292626551237302}
- clipping(>= -0.0087 dBFS 샘플 존재) 파일: 393개
- 그룹별 RMS 평균: {'D03': -19.71, 'voice_phishing': -20.82}
- 정규화/gain은 원본과 전후 gain metadata가 있어야 정확히 검증할 수 있습니다. 현재 통계는 출력 레벨 분포와 clipping 위험을 점검하는 용도입니다.

## 4. 노이즈/삐- 휴리스틱 스크리닝

- 노이즈 후보: 0개; 삐- 후보: 0개
- 후보는 spectral flatness, 고주파 비율, 협대역 tonal peak를 이용한 1차 스크리닝이며 의도적 증강의 확정 판정이 아닙니다. 원본/처리 metadata가 없으므로 실제 삽입률·삐- 구간·노이즈 SNR은 검증할 수 없습니다.

## 5. 결론

- 파일/manifest 정합성, TXT 동반, WAV 디코드, 청크 길이, 기본 레벨 통계는 확인 가능합니다.
- 속도 0.9~1.1 랜덤 적용 여부, gain 추가량, 노이즈·삐- 삽입 여부/비율은 원본 데이터 또는 augmentation metadata가 없어 확인 불가입니다.
- 재현 가능한 원본 비교를 위해 원본 경로를 함께 제공하거나, 각 파일에 `source_id`, `speed_factor`, `gain_db`, `noise_added`, `beep_added`, `chunk_start_s`, `chunk_end_s` metadata를 저장하는 것을 권장합니다.

생성 파일: `audio_file_stats.csv`, `eda_summary.json`, `eda_overview.png`
