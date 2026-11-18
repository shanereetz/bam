# BAM Feetech recorder adaptation

Original source snapshots are `bam_feetech_record_upstream.py` and `bam_feetech_all_record_upstream.py` in this directory. The active scripts are `bam/feetech/record.py` and `all_record.py`.

- Uses the same `pypot.feetech.FeetechSTS3215IO` interface as upstream. Pypot source is preserved under `vendor/pypot`, downloaded from pollen-robotics/pypot branch `support-feetech-sts3215`.
- Uses the original six-second BAM trajectory implementations unchanged.
- Preserves separate Pypot position, speed and voltage reads, and upstream `temp=0`, `load=0` placeholders. No host temperature sampling, median filter, confirmation reads or temperature threshold.
- Adds port/ID arguments in place of hardcoded device and ID; arm mass metadata; measured encoder zero and direction conversion; explicit 12 V motor label and measured voltage.
- Uses monotonic timestamps; adds fault-status reads, try/finally torque shutdown, settings backup/restoration and partial-log saving.
- Applies P gain with D=I=0 as used by upstream's P-only recording; verifies and restores original gains afterward.
- Replaces shell execution in all_record with checked subprocesses using the same Python environment. Uses the four documented trajectories; removes upstream's nonexistent `brutal` entry. Gain sweep remains 4,8,16,32.
- Pypot's degree conversions use 4095 as their full-scale denominator; logs follow that conversion consistently. This differs slightly from earlier custom-SDK pilot logs, which used 4096. Keep the fresh Pypot dataset separate.

Hardware temperature-protection settings remain unchanged. Temperature placeholders must not be interpreted as measured zero Celsius. BAM's fitting does not consume the temperature field.
