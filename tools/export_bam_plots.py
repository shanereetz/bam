"""Run bam.plot unchanged, saving each plt.show() figure to a gallery."""
import argparse
import html
from pathlib import Path
import runpy
import sys
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

p = argparse.ArgumentParser()
p.add_argument('session', type=Path)
a = p.parse_args()
out = a.session / 'plots'
out.mkdir(exist_ok=True)
items = []

def save_show(*args, **kwargs):
    fig = plt.gcf()
    title = fig.axes[0].get_title()
    filename = f'bam_plot_{len(items)+1:02d}.png'
    fig.set_size_inches(11, 8)
    fig.tight_layout()
    fig.savefig(out / filename, dpi=140)
    items.append((title, filename))
    plt.close(fig)

plt.show = save_show
sys.argv = ['bam.plot', '--logdir', str(a.session / 'processed'), '--actuator', 'sts3215']
runpy.run_module('bam.plot', run_name='__main__')
page = '''<!doctype html><meta charset="utf-8"><title>BAM acquisition plots</title>
<style>body{font:16px system-ui;max-width:1100px;margin:32px auto;padding:0 20px;background:#f4f5f7}img{width:100%;background:white}section{margin:32px 0}a{color:#1757b8}</style>
<h1>BAM acquisition plots</h1>
<p>16 recordings, P=4,8,16,32. Angle and speed are recorded data. The voltage panel is BAM's estimated control using its default STS3215 actuator, not a measured motor command or a fitted 12 V model. No simulation overlay.</p>
'''
page += '<nav>' + ' · '.join(f'<a href="#plot{i}">{html.escape(t)}</a>' for i,(t,f) in enumerate(items)) + '</nav>'
page += ''.join(f'<section id="plot{i}"><h2>{html.escape(t)}</h2><img loading="lazy" src="{f}"></section>' for i,(t,f) in enumerate(items))
(out / 'index.html').write_text(page)
print(f'Saved {len(items)} BAM plots to {out}')
