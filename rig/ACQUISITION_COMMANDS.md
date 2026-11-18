# STS3215 12 V: acquisition commands and reproduction guide

Experiment: 2026-11-18, Microduck. Motor was **brand new at experiment start**; commissioning and pilot runs preceded the BAM/Pypot dataset.

This is a reproducible command guide reconstructed from the scripts, saved artifacts and current session. It is **not a verbatim terminal transcript of every earlier diagnostic invocation**: those exact one-off commands are not all retained. The active acquisition command below is exact. Setup and historical commands are labelled separately so that they are not mistaken for a new acquisition sequence.

## 1. Open the existing project

```sh
cd /Users/virtualaxis/Documents/ChatGPT/Microduck/bam-fork
.venv/bin/python --version
ls /dev/cu.usbmodem*
```

Our Python is 3.12.8; adapter port is `/dev/cu.usbmodem5AE60570831`, baud rate 1,000,000, motor ID 1. Check the port after reconnecting. Only one process should open it at a time.

## 2. Rebuild the Python environment if needed

These are reproduction commands, not a claim that each was typed in this exact form originally. Skip this section when using the working `.venv`.

```sh
uv venv --python /opt/homebrew/bin/python3.12 .venv
uv pip install --python .venv/bin/python -e .
uv pip install --python .venv/bin/python ./vendor/pypot
uv pip install --python .venv/bin/python -r rig/acquisition-requirements.txt
```

The venv was created with `uv` and does not contain `pip`; use `uv pip`, not `.venv/bin/python -m pip`. The current complete dependency snapshot is `rig/acquisition-environment-freeze.txt`. Preserve `bam/` and `vendor/pypot/` alongside that snapshot: BAM has local recorder changes, and the Pypot Feetech implementation comes from a fork. Fetching upstream again alone does not reproduce this recorder.

Sources used:

- BAM: <https://github.com/Rhoban/bam>, main branch source archive, local package version 1.0.3.
- Pypot: <https://github.com/pollen-robotics/pypot/tree/support-feetech-sts3215>, installed version 5.0.2.
- Pypot archive: <https://codeload.github.com/pollen-robotics/pypot/tar.gz/refs/heads/support-feetech-sts3215>.
- BAM identification instructions: <https://bam.readthedocs.io/en/latest/identification/index.html>.

Branch names can change; the preserved local source is the reference for this experiment. `BAM_RECORDER_CHANGES.md` lists our adaptations, and `bam_feetech_record_upstream.py` / `bam_feetech_all_record_upstream.py` preserve the original scripts.

## 3. Read-only hardware check (only when acquisition is stopped)

```sh
.venv/bin/python tools/servo_check.py \
  --port /dev/cu.usbmodem5AE60570831 --id 1
```

Expected model 777, position mode 0, torque 0 while idle, fault 0. Supply measured 12.6 V. This diagnostic uses `ftservo-python-sdk==2.0.1` through `tools/servo_sdk_compat.py`; the active BAM recorder uses Pypot instead.

## 4. Current physical configuration and reference

| Arm | Arm mass (kg) | Yellow tip assembly (kg) | Red tip assembly (kg) |
|---|---:|---:|---:|
| 100 mm | 0.0251 | 0.1429 | 0.3061 |
| 150 mm | 0.0309 | 0.1429 | 0.3061 |
| 200 mm | 0.0375 | 0.1429 | 0.3061 |

Yellow = 132.3 g taped washers + 10.6 g hardware. Red = 295.5 g taped washers + 10.6 g hardware. `--mass` is the tip assembly; `--arm-mass` is separate. Length is pivot to load pivot, in metres.

Mounted for this run: **100 mm / yellow**. Downward encoder reference is **2048**, direction **-1** (positive joint angle is counterclockwise viewed from output). The same reference is valid only while the physical mounting/reference remains unchanged. The supplied BAM trajectories include approximately ±100.8° commands; the user confirmed the sandbox movement clearance.

## 5. Exact active acquisition command

This powers and moves the motor. Run with the stated arm/load mounted and clear to move.

```sh
.venv/bin/python -u -m bam.feetech.all_record \
  --port /dev/cu.usbmodem5AE60570831 --id 1 \
  --motor sts3215_12v --vin 12.6 \
  --length 0.100 --arm-mass 0.0251 --mass 0.1429 \
  --zero-ticks 2048 --direction -1 \
  --logdir data/bam_pypot_100mm_yellow/raw
```

This runs 16 recordings: gains **4, 8, 16, 32**, each with **up_and_down, sin_time_square, lift_and_drop, sin_sin**. Each trajectory lasts six seconds; setup, return to zero and pauses add time. The sweep uses the current interpreter, launches `bam.feetech.record` for each cell and stops if a child fails. Each recording restores original gains/lock and releases torque in cleanup. Initial gains were P=32, D=32, I=0; recording sets D=I=0 and sweeps P.

Temperature and load are upstream BAM **zero placeholders**, not measurements. The user explicitly approved this run with no host temperature monitoring. Built-in thermal protection remains unchanged (70°C limit; unloading register 19 retains value 44) and fault-status checks remain enabled. Earlier powered temperature spikes remain unexplained; this run does not establish their cause.

Use a **new output session folder for every repeat**: timestamp filenames avoid overwrites, but the validator expects exactly one recording per gain/trajectory pair.

### Single-recording equivalent (example, not an extra run already performed)

```sh
.venv/bin/python -u -m bam.feetech.record \
  --port /dev/cu.usbmodem5AE60570831 --id 1 \
  --motor sts3215_12v --vin 12.6 \
  --length 0.100 --arm-mass 0.0251 --mass 0.1429 \
  --zero-ticks 2048 --direction -1 \
  --kp 4 --trajectory up_and_down \
  --logdir data/bam_pypot_100mm_yellow_repeat/raw
```

## 6. Validate and resample after all 16 finish

```sh
.venv/bin/python tools/validate_bam_session.py data/bam_pypot_100mm_yellow
```

Checks completion, cleanup, exact 16-cell coverage, increasing timestamps, finite position/speed, status=0 and expected torque flags. Writes `manifest.json` and calls BAM's processor at 5 ms:

```sh
.venv/bin/python -m bam.process \
  --raw data/bam_pypot_100mm_yellow/raw \
  --logdir data/bam_pypot_100mm_yellow/processed \
  --dt 0.005
```

The second command is shown for transparency; the validator already runs it. Resampling does not eliminate underlying sampling gaps; inspect the manifest's timing statistics. Settings backups are in the session's `settings/` folder.

## 7. Remaining configurations

After physically changing the assembly, reuse section 5 with the corresponding values below, and section 6 with the matching session folder. These are **future runs**, not commands already executed. Do not batch the six configurations without stopping to change the hardware.

| Configuration | `--length` | `--arm-mass` | `--mass` | Session folder |
|---|---:|---:|---:|---|
| 100 mm yellow | 0.100 | 0.0251 | 0.1429 | `data/bam_pypot_100mm_yellow` |
| 100 mm red | 0.100 | 0.0251 | 0.3061 | `data/bam_pypot_100mm_red` |
| 150 mm yellow | 0.150 | 0.0309 | 0.1429 | `data/bam_pypot_150mm_yellow` |
| 150 mm red | 0.150 | 0.0309 | 0.3061 | `data/bam_pypot_150mm_red` |
| 200 mm yellow | 0.200 | 0.0375 | 0.1429 | `data/bam_pypot_200mm_yellow` |
| 200 mm red | 0.200 | 0.0375 | 0.3061 | `data/bam_pypot_200mm_red` |

Append `/raw` for `--logdir`. These six combinations are our acquisition plan, not a universal BAM minimum. No fitting commands have been run for this motor yet; `sts3215_12v` is currently a recording label, and model registration/fitting/held-out validation remain separate work.

## 8. Earlier commissioning and diagnostic work (historical)

These tools/command forms explain earlier work, but are **not prerequisites to repeat the BAM session**. Exact arguments of every historical invocation are not recoverable from the retained command context.

```sh
# Unloaded movement checks used this tool (3° and later 30°).
# Remove the load before using these commissioning commands.
.venv/bin/python tools/servo_check.py --port /dev/cu.usbmodem5AE60570831 --move --degrees 3
.venv/bin/python tools/servo_check.py --port /dev/cu.usbmodem5AE60570831 --move --degrees 30

# Earlier custom-SDK pilot recorder command form; superseded by BAM/Pypot.
.venv/bin/python tools/record_bam.py --kp 4 8 16 32 \
  --trajectories up_and_down sin_time_square lift_and_drop sin_sin

# Pilot log summary utility.
.venv/bin/python tools/summarize_logs.py
```

Encoder recentering was performed once using `.venv/bin/python tools/recenter_encoder.py`. **Do not rerun as a routine setup step.** It changes the persistent homing offset. Original downward reading 2957 and offset 85 became downward 2048 and offset 994. Backup: `rig/encoder_recenter_20261118_140050.json`; active reference: `rig/reference_centered_20261118_140050.json`.

Stationary and manual-motion temperature tests were one-off diagnostics, with results preserved in `data/stationary_temperature_20261118_141350.json` and `data/manual_motion_temperature_20261118_141757.json`. Their exact inline shell commands are not retained here. Earlier timestamped pilot folders use the custom SDK and a 4096-count conversion; keep them separate from the Pypot dataset (4095 denominator).

Published 7.4 V reference data was downloaded and inspected from:

```sh
curl -L 'https://huggingface.co/buckets/Gregwar/bam_data/resolve/feetech_sts3215_raw.zip?download=true' \
  -o /tmp/bam_feetech_7v4_raw.zip
```

This download command reproduces the reference fetch. Findings are in `rig/bam_7v4_reference_dataset_summary.json`: 100 logs, five configurations, four gains, **five** historical trajectories including `brutal`, and all temperature entries zero. Current BAM's trajectory registry omits `brutal`; our 16-run sweep follows its four current documented trajectories. The historical 7.4 V fitted parameters are not 12 V identification results.

## 9. Capture dependencies again

```sh
uv --cache-dir /tmp/microduck-uv-cache pip freeze --python .venv/bin/python \
  > rig/acquisition-environment-freeze.txt
```

Keep this file, both source trees, `rig/`, `tools/`, and raw/processed session folders together when archiving the experiment.

## Completed run result

The section 5 command completed successfully on 2026-11-18. Section 6 validation was then run successfully: **16/16 recordings, 35,264 raw samples, 16 processed files at 5 ms**. Post-run section 3 check returned position 2050, torque 0, fault 0, voltage 12.6 V, stationary temperature 33°C. Manifest: `data/bam_pypot_100mm_yellow/manifest.json`. No subsequent physical configuration has been acquired yet.

## Plot the completed recordings with BAM

Installed Matplotlib and used BAM's actual `bam.plot` module without simulation overlays:

```sh
uv --cache-dir /tmp/microduck-uv-cache pip install --python .venv/bin/python matplotlib
.venv/bin/python -m bam.plot \
  --logdir data/bam_pypot_100mm_yellow/processed --actuator sts3215
```

The direct command opens interactive Matplotlib windows (close each to advance). To save all figures in a gallery, we ran this wrapper, which executes `bam.plot` unchanged and replaces only `plt.show()` with image export:

```sh
MPLCONFIGDIR=/tmp/microduck-matplotlib .venv/bin/python tools/export_bam_plots.py \
  data/bam_pypot_100mm_yellow
```

Gallery: `data/bam_pypot_100mm_yellow/plots/index.html`. `--actuator sts3215` selects the existing BAM control implementation; log metadata supplies 12.6 V and each gain. Its control-voltage panel is an estimate with default actuator parameters, not a measured command or an identified 12 V model. Position/target/speed panels show the recorded data. No `--sim` option or 7.4 V fitted parameter file is used.

## 100 mm / red acquisition

User mounted the red weights for the next configuration. Pre-run check: position 2048, torque 0, fault 0, 12.6 V, stationary temperature 34°C. Executed:

```sh
.venv/bin/python -u -m bam.feetech.all_record \
  --port /dev/cu.usbmodem5AE60570831 --id 1 \
  --motor sts3215_12v --vin 12.6 \
  --length 0.100 --arm-mass 0.0251 --mass 0.3061 \
  --zero-ticks 2048 --direction -1 \
  --logdir data/bam_pypot_100mm_red/raw
```

## Migration to the GitHub fork

This guide now uses the cloned repository root. Historical commands above are reproduction instructions adapted to this layout. Origin: https://github.com/shanereetz/bam.git; branch: `sts3215-12v-acquisition`. Data and vendor source were copied locally and remain Git-ignored. Red acquisition stopped after seven complete recordings and one partial recording due to USB disconnect. Torque-off/settings restoration could not be confirmed; no hardware commands were run during migration.
