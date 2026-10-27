"""
preset_comparator_pkg
======================
Package for intra- and cross-class uniqueness analysis of C2PA preset action files.
"""

from .json_helper import load_preset_files, build_json
from .action_comparator import inter_sub_tag, cross_tag
from .display import print_inter, print_cross, print_summary, print_inter_matrix, print_cross_matrix

__all__ = [
    "load_preset_files",
    "build_json",
    "inter_sub_tag",
    "cross_tag",
    "print_inter",
    "print_cross",
    "print_summary",
    "print_inter_matrix",
    "print_cross_matrix",
]