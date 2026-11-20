"""Evaluate a pilot fit on its recording; this is not held-out validation."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from bam.model import load_model
from bam.simulate import Simulator

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('session', type=Path)
a = p.parse_args()
model = load_model(str(a.session / 'params_m1_pilot.json'))
results = []
for path in sorted((a.session / 'processed').glob('*.json')):
    log = json.loads(path.read_text())
    predicted = np.asarray(Simulator(model).rollout_log(log, simulate_control=True)[0])
    t, measured, target = (np.asarray([e[k] for e in log['entries']])
                           for k in ['timestamp', 'position', 'goal_position'])
    assert np.isfinite(predicted).all()
    error = np.rad2deg(predicted - measured)
    results.append(dict(file=path.name, fit_mae_deg=float(np.abs(error).mean()),
                        fit_rmse_deg=float(np.sqrt(np.mean(error**2))),
                        evaluation='training recording only; no held-out validation'))
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True,
                             gridspec_kw={'height_ratios': [3, 1]})
    for values, label in [(target, 'Command'), (measured, 'Measured'),
                          (predicted, 'BAM m1 pilot fit')]:
        axes[0].plot(t, np.rad2deg(values), label=label)
    axes[0].set(ylabel='Angle (degrees)', title='STS3215 12V · 100 mm red · P=4 · up_and_down')
    axes[0].legend()
    axes[1].plot(t, error)
    axes[1].axhline(0, color='gray', linewidth=.6)
    axes[1].set(xlabel='Time (s)', ylabel='Fit − measured (°)')
    for ax in axes:
        ax.grid(alpha=.2)
    fig.text(.1, .01, 'Source: 2026-11-18 acquisition, resampled at 5 ms. Fit evaluated on training data only.', fontsize=9)
    fig.tight_layout(rect=[0, .03, 1, 1])
    fig.savefig(a.session / 'pilot_fit.png', dpi=160)
    plt.close(fig)
(a.session / 'fit_evaluation.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
