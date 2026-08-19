"""EDA for stt_finetuning_cleaned_v3 audio preprocessing outputs.

This script intentionally reports aggregate audio statistics only; it does not
write audio or transcript contents to the report.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import wave
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


CHUNK_RE = re.compile(r"^(?P<base>.+)__chunk_(?P<idx>\d+)\.wav$")


def read_wav(path: Path) -> tuple[np.ndarray, int, int]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        rate = wf.getframerate()
        width = wf.getsampwidth()
        frames = wf.readframes(wf.getnframes())
    if width == 2:
        x = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 1:
        x = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128) / 128.0
    elif width == 4:
        x = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"unsupported sample width {width}: {path.name}")
    if channels > 1:
        x = x.reshape(-1, channels).mean(axis=1)
    return x, rate, channels


def pct(values: list[float], q: float) -> float | None:
    return None if not values else float(np.percentile(values, q))


def audio_stats(path: Path) -> dict:
    x, rate, channels = read_wav(path)
    duration = len(x) / rate if rate else 0.0
    rms = float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    frame = x[: min(len(x), rate * 30)]
    if len(frame) > 1:
        zcr = float(np.mean(frame[:-1] * frame[1:] < 0))
        spec = np.abs(np.fft.rfft(frame * np.hanning(len(frame))))
        freqs = np.fft.rfftfreq(len(frame), 1.0 / rate)
        power = spec * spec
        total = float(power.sum()) + 1e-12
        centroid = float((freqs * power).sum() / total)
        flatness = float(np.exp(np.mean(np.log(spec + 1e-12))) / (np.mean(spec) + 1e-12))
        high_ratio = float(power[freqs >= 4000].sum() / total)
        # Candidate beep signal: narrow, stable tonal energy around common alert bands.
        band = (freqs >= 800) & (freqs <= 4000)
        band_power = power[band]
        beep_ratio = float(np.max(band_power) / (band_power.sum() + 1e-12)) if band_power.size else 0.0
    else:
        zcr = centroid = flatness = high_ratio = beep_ratio = 0.0
    silence_ratio = float(np.mean(np.abs(x) < 10 ** (-45 / 20))) if len(x) else 1.0
    clipping_ratio = float(np.mean(np.abs(x) >= 0.999)) if len(x) else 0.0
    return {
        "file": str(path),
        "name": path.name,
        "group_dir": path.parent.name,
        "bytes": path.stat().st_size,
        "duration_s": duration,
        "sample_rate_hz": rate,
        "channels": channels,
        "rms_dbfs": 20 * math.log10(max(rms, 1e-12)),
        "peak_dbfs": 20 * math.log10(max(peak, 1e-12)),
        "silence_ratio": silence_ratio,
        "clipping_ratio": clipping_ratio,
        "zcr": zcr,
        "spectral_centroid_hz": centroid,
        "spectral_flatness": flatness,
        "high_band_ratio_ge4k": high_ratio,
        "beep_tonal_ratio_candidate": beep_ratio,
    }


def summarize(vals: list[float]) -> dict:
    return {
        "n": len(vals),
        "min": pct(vals, 0),
        "p05": pct(vals, 5),
        "median": pct(vals, 50),
        "p95": pct(vals, 95),
        "max": pct(vals, 100),
        "mean": float(np.mean(vals)) if vals else None,
        "std": float(np.std(vals)) if vals else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir", type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("reports/audio_eda_v3"))
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = args.data_dir / "manifest.jsonl"
    manifest = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    manifest_by_name = {Path(row["audio"]).name: row for row in manifest}
    wavs = sorted(args.data_dir.rglob("*.wav"))
    txts = sorted(args.data_dir.rglob("*.txt"))
    beep_text_files = [p for p in txts if re.search(r"삐|삑|beep|신호음", p.read_text(encoding="utf-8", errors="ignore"), re.I)]
    rows, errors = [], []
    for path in wavs:
        try:
            row = audio_stats(path)
            m = manifest_by_name.get(path.name)
            row["manifest_duration_s"] = m.get("duration") if m else None
            row["duration_diff_ms"] = 1000 * (row["duration_s"] - m["duration"]) if m else None
            row["manifest_group"] = m.get("group") if m else None
            row["manifest_source_exists"] = bool(m and Path(m.get("source", "")).exists()) if m else None
            row["manifest_aligned"] = m.get("aligned") if m else None
            match = CHUNK_RE.match(path.name)
            row["chunk_base"] = match.group("base") if match else path.stem
            row["chunk_index"] = int(match.group("idx")) if match else 1
            rows.append(row)
        except Exception as exc:
            errors.append({"file": str(path), "error": repr(exc)})

    fieldnames = list(rows[0]) if rows else []
    with (args.out_dir / "audio_file_stats.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    durations = [r["duration_s"] for r in rows]
    groups = Counter(r["manifest_group"] or r["group_dir"] for r in rows)
    chunk_bins = Counter("<20s" if d < 20 else "20-30s" if d <= 30 else ">30s" for d in durations)
    bases = defaultdict(list)
    for r in rows:
        bases[r["chunk_base"]].append(r)
    source_missing = sum(1 for r in rows if r["manifest_source_exists"] is False)
    source_unknown = sum(1 for r in rows if r["manifest_source_exists"] is None)
    manifest_names = set(manifest_by_name)
    actual_names = {Path(r["file"]).name for r in rows}
    dup_names = [n for n, c in Counter(actual_names).items() if c > 1]
    durs = [r["duration_diff_ms"] for r in rows if r["duration_diff_ms"] is not None]
    rms = [r["rms_dbfs"] for r in rows]
    peak = [r["peak_dbfs"] for r in rows]
    clipping = [r for r in rows if r["clipping_ratio"] > 0]
    beep_candidates = [r for r in rows if r["beep_tonal_ratio_candidate"] >= 0.08]
    noise_candidates = [r for r in rows if r["spectral_flatness"] >= 0.35 and r["high_band_ratio_ge4k"] >= 0.05]

    report = {
        "data_dir": str(args.data_dir),
        "manifest_rows": len(manifest),
        "actual_wav_files": len(wavs),
        "actual_txt_files": len(txts),
        "txt_beep_marker_files": len(beep_text_files),
        "decoded_wav_files": len(rows),
        "decode_errors": errors,
        "groups": dict(groups),
        "manifest_aligned_counts": dict(Counter(str(r.get("aligned")) for r in manifest)),
        "manifest_duration_s": summarize([float(r["duration"]) for r in manifest if r.get("duration") is not None]),
        "actual_duration_s": summarize(durations),
        "manifest_actual_duration_diff_ms": summarize(durs),
        "chunk_duration_bins": dict(chunk_bins),
        "source_paths_missing": source_missing,
        "source_paths_unknown": source_unknown,
        "unique_chunk_bases": len(bases),
        "chunk_count_distribution": dict(Counter(len(v) for v in bases.values())),
        "manifest_names_missing_on_disk": len(manifest_names - actual_names),
        "actual_names_missing_in_manifest": len(actual_names - manifest_names),
        "duplicate_basenames": dup_names,
        "sample_rate_counts": dict(Counter(r["sample_rate_hz"] for r in rows)),
        "channel_counts": dict(Counter(r["channels"] for r in rows)),
        "rms_dbfs": summarize(rms),
        "peak_dbfs": summarize(peak),
        "clipping_files": len(clipping),
        "candidate_beep_files": len(beep_candidates),
        "candidate_noise_files": len(noise_candidates),
        "notes": [
            "Speed augmentation, gain amount, and normalization cannot be proven without original audio or augmentation metadata.",
            "Beep/noise candidate counts are heuristic signal-screening results, not proof of intentional augmentation.",
        ],
    }
    (args.out_dir / "eda_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    axes[0].hist(durations, bins=30, color="#4472c4", edgecolor="white")
    axes[0].axvline(20, color="#d62728", linestyle="--", linewidth=1)
    axes[0].axvline(30, color="#d62728", linestyle="--", linewidth=1)
    axes[0].set(title="Chunk duration", xlabel="seconds", ylabel="files")
    axes[1].hist(rms, bins=30, color="#70ad47", edgecolor="white")
    axes[1].set(title="RMS level", xlabel="dBFS", ylabel="files")
    axes[2].scatter(durations, rms, s=8, alpha=0.45, c=[0 if r["manifest_group"] == "D03" else 1 for r in rows])
    axes[2].set(title="Duration vs RMS", xlabel="seconds", ylabel="RMS dBFS")
    fig.tight_layout()
    fig.savefig(args.out_dir / "eda_overview.png", dpi=160)
    plt.close(fig)

    md = [
        "# stt_finetuning_cleaned_v3 오디오 전처리 EDA",
        "",
        f"- 대상: `{args.data_dir}`",
        f"- manifest: {len(manifest):,}행 / 실제 WAV: {len(wavs):,}개 / 실제 TXT: {len(txts):,}개 / 디코드 성공: {len(rows):,}개",
        "",
        "## 1. 데이터 정합성",
        "",
        f"- 그룹: {dict(groups)}",
        f"- manifest `aligned`: {dict(Counter(str(r.get('aligned')) for r in manifest))}",
        f"- manifest 이름이 디스크에 없음: {len(manifest_names - actual_names)}개; 디스크 WAV 이름이 manifest에 없음: {len(actual_names - manifest_names)}개",
        f"- TXT 동반 여부: {sum(1 for r in rows if Path(r['file']).with_suffix('.txt').exists())}/{len(rows)}",
        f"- TXT에서 삐-/신호음 관련 표기 후보: {len(beep_text_files)}개 파일",
        f"- 원본 source 경로 확인 불가: {source_missing + source_unknown}/{len(rows)}개 (manifest 경로가 현재 환경에 없음)",
        "",
        "## 2. 청킹",
        "",
        f"- 실제 길이 구간: {dict(chunk_bins)}",
        f"- 청크 base 수: {len(bases):,}; base별 청크 수 분포: {dict(Counter(len(v) for v in bases.values()))}",
        f"- 실제- manifest duration 차이(ms): {summarize(durs)}",
        "- 20~30초 규칙은 ‘긴 원본을 청킹한 결과’에는 대체로 부합하는지 확인할 수 있지만, 원본이 짧은 마지막 청크인지 여부는 원본 없이는 판정할 수 없습니다.",
        "",
        "## 3. WAV 신호 기본 통계",
        "",
        f"- sample rate: {dict(Counter(r['sample_rate_hz'] for r in rows))}; channels: {dict(Counter(r['channels'] for r in rows))}",
        f"- RMS dBFS: {summarize(rms)}; peak dBFS: {summarize(peak)}",
        f"- clipping(>= -0.0087 dBFS 샘플 존재) 파일: {len(clipping)}개",
        f"- 그룹별 RMS 평균: {dict((g, round(float(np.mean([r['rms_dbfs'] for r in rows if r['manifest_group'] == g])), 2)) for g in sorted(set(r['manifest_group'] for r in rows)))}",
        "- 정규화/gain은 원본과 전후 gain metadata가 있어야 정확히 검증할 수 있습니다. 현재 통계는 출력 레벨 분포와 clipping 위험을 점검하는 용도입니다.",
        "",
        "## 4. 노이즈/삐- 휴리스틱 스크리닝",
        "",
        f"- 노이즈 후보: {len(noise_candidates)}개; 삐- 후보: {len(beep_candidates)}개",
        "- 후보는 spectral flatness, 고주파 비율, 협대역 tonal peak를 이용한 1차 스크리닝이며 의도적 증강의 확정 판정이 아닙니다. 원본/처리 metadata가 없으므로 실제 삽입률·삐- 구간·노이즈 SNR은 검증할 수 없습니다.",
        "",
        "## 5. 결론",
        "",
        "- 파일/manifest 정합성, TXT 동반, WAV 디코드, 청크 길이, 기본 레벨 통계는 확인 가능합니다.",
        "- 속도 0.9~1.1 랜덤 적용 여부, gain 추가량, 노이즈·삐- 삽입 여부/비율은 원본 데이터 또는 augmentation metadata가 없어 확인 불가입니다.",
        "- 재현 가능한 원본 비교를 위해 원본 경로를 함께 제공하거나, 각 파일에 `source_id`, `speed_factor`, `gain_db`, `noise_added`, `beep_added`, `chunk_start_s`, `chunk_end_s` metadata를 저장하는 것을 권장합니다.",
        "",
        "생성 파일: `audio_file_stats.csv`, `eda_summary.json`, `eda_overview.png`",
    ]
    (args.out_dir / "eda_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
