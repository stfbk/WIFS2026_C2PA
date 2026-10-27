import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .display import SEP, _b, _g, _gb, _rb, print_inter, print_cross, print_summary
from .json_helper import load_preset_files, build_json
from .action_comparator import inter_sub_tag, cross_tag



actions_dir = Path(sys.argv[1]) if len(sys.argv) > 2 else Path("./results/_preset_actions_/seasons")
if not actions_dir.is_dir():
    print(f"{_rb('[ERROR]')} '{actions_dir}' is not a directory.\n" "  Use --actions-dir <path> to specify the preset actions folder.", file=sys.stderr,)
    sys.exit(1)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else (Path("results") / f"presets_comparison/preset_analysis_{timestamp}.json")

print(f"\n{_b(SEP)}")
print(_b("  C2PA-PRESCAN — PRESET ACTION UNIQUENESS ANALYSIS"))
print(_b(SEP))
print(f"  {'Actions dir  :'} {actions_dir}")
print(f"  {'Timestamp    :'} {timestamp}\n")

presets = load_preset_files(actions_dir)
if not presets:
    print(_rb("  No preset action files found. Exiting."), file=sys.stderr)
    sys.exit(1)

tags    = sorted({p["tag"]     for p in presets})
sub_tgs = sorted({p["sub_tag"] for p in presets})
print(f"  Loaded {_g(str(len(presets)))} preset file(s)")
print(f"  Tags     : {', '.join(tags)}")
print(f"  Sub-tags : {', '.join(sub_tgs)}")

# intra = intra_sub_tag(presets)
inter = inter_sub_tag(presets)
cross = cross_tag(presets)

# print_intra(intra)
print_inter(inter, presets)
print_cross(cross, presets)
print_summary(presets, inter, cross, output_path, timestamp)

payload = build_json(presets, inter, cross, actions_dir, timestamp)
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")