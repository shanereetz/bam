# STS3215 12 V acquisition workspace

This branch ports the Microduck experiment to shanereetz/bam, based on commit b9e11118e17fe8ec803d430202f6fcf31d57901e.

- [Commands and setup](rig/ACQUISITION_COMMANDS.md)
- [Recorder adaptations](rig/BAM_RECORDER_CHANGES.md)
- [Physical rig and acquisition status](rig/config.json)
- [Dependency snapshot](rig/acquisition-environment-freeze.txt)

The local clone includes an independent `.venv`, `vendor/pypot`, and a copy of `data`; all three are Git-ignored. The original Microduck files remain intact. For another machine, copy the archived data separately and obtain Pypot from the fork documented in the command guide. The dependency snapshot contains local paths and is an environment record, not a portable requirements file.

100 mm/yellow is complete: 16 recordings validated and processed at 5 ms. 100 mm/red has seven complete recordings plus one partial in `data/bam_pypot_100mm_red/failed/`. USB disconnected during P=8 sin_sin. Torque-off and PID restoration were not confirmed; do not assume cleanup succeeded. No motor commands were run during repository migration.

Recorder uses BAM's trajectories and Pypot API, with zero temperature/load placeholders and fault checks. This is acquisition work, not a fitted or validated 12 V actuator model. Prior SDK scripts are retained as historical tools; use `bam.feetech.all_record` for new acquisition.
