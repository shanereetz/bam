# STS3215 12 V bench acquisitions — 2026-11-19

191 accepted recordings: 96 new-motor and 95 worn-motor recordings across 100, 150 and 200 mm arms, red (306.1 g) and yellow (142.9 g) tip weights, P=4/8/16/32 and four BAM trajectories. Arm masses: 25.1/30.9/37.5 g. Nominal supply metadata: 12.6 V.

Only worn 200 mm red P=32 sin_time_square is excluded, following repeated status-2 faults and reported voltage collapse. Failed and preflight-error attempts remain in failed/; superseded-reference recordings and the 2026-11-18 pilot are not part of the accepted set. Do not combine them with training data.

Each session contains raw/, processed/ at 5 ms, settings backups, setup metadata and a validation manifest. acquisition_20261119_manifest.json provides SHA-256 hashes of accepted raw files. New-motor and worn-motor settings differ; comparisons do not establish causation by wear alone. Temperature and load fields inside trajectories are zero placeholders. Supply voltage is servo-reported, not externally measured. Completed recordings can have substantial voltage dips (including P32 mixed sine); integrity validation does not certify fixed-voltage operation or fitness for a particular model.

## Plot reproduction

Run `.venv/bin/python tools/export_bam_plots.py data/SESSION` to export upstream `bam.plot` figures. Session plots/index.html galleries show accepted processed data only. Their control-voltage panel uses the default STS3215 actuator model, not measured supply voltage and not the fitted 12 V model.

Run `.venv/bin/python tools/plot_200mm_comparison.py` for raw angle/supply-voltage comparisons; the faulted accelerating sine is explicitly diagnostic. New-motor preliminary fit results are retained separately with their limitations and split metadata; no worn-motor fit is claimed.

Validate full sessions with `tools/validate_bam_session.py data/SESSION`; for worn 200 mm red append `--exclude-cell 32:sin_time_square`.

## Sessions

- new_motor_100mm_red_20261119: 16 recordings, 48602 samples
- new_motor_100mm_yellow_20261119: 16 recordings, 48439 samples
- new_motor_150mm_red_20261119: 16 recordings, 48946 samples
- new_motor_150mm_yellow_20261119: 16 recordings, 48986 samples
- new_motor_200mm_red_20261119: 16 recordings, 49022 samples
- new_motor_200mm_yellow_20261119: 16 recordings, 49032 samples
- worn_motor_100mm_red_20261119: 16 recordings, 49223 samples
- worn_motor_100mm_yellow_20261119: 16 recordings, 48858 samples
- worn_motor_150mm_red_20261119: 16 recordings, 49774 samples
- worn_motor_150mm_yellow_20261119: 16 recordings, 49954 samples
- worn_motor_200mm_red_20261119: 15 recordings, 47144 samples
- worn_motor_200mm_yellow_20261119: 16 recordings, 49582 samples
