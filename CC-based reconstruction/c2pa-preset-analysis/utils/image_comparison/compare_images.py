"""
Pixel-level image comparison script using OpenCV.
Compares two images and reports whether they are identical,
optionally saves difference as summary image.

Usage:
    python compare_images.py <image1> <image2> [--diff-output diff.png]
    <image1> and <image2> are the paths to the images to compare.
"""

import sys
import argparse
import numpy as np

try:
    import cv2
except ImportError:
    sys.exit("OpenCV is not installed. Run: pip install opencv-python")


# ANSI colours 
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def load_image(path: str) -> np.ndarray:
    """Load an image in BGR format, raising a clear error on failure."""
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(
            f"Could not open image: {path!r}\n"
            "Make sure the path is correct and the file is a supported format."
        )
    return img


def normalise_channels(img1: np.ndarray, img2: np.ndarray):
    """
    Make both images comparable by converting to a shared colour space.
    Returns (img1_norm, img2_norm, channel_label).
    """
    def channels(img):
        return 1 if img.ndim == 2 else img.shape[2]

    c1, c2 = channels(img1), channels(img2)

    print(f"channels_img1: {c1}, channels_img2: {c2}")

    if c1 == c2:
        label = {1: "Grayscale", 3: "BGR", 4: "BGRA"}.get(c1, f"{c1}-ch")
        return img1, img2, label

    # check with RGB

    # Flatten both to grayscale for a fair pixel comparison
    def to_gray(img):
        if img.ndim == 2: # grayscale
            return img
        if img.shape[2] == 4:
            return cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    print(
        f"{YELLOW}⚠  Channel mismatch ({c1} vs {c2}). "
        f"Converting both to grayscale for comparison.{RESET}"
    )
    return img1, img2, "Grayscale (normalised)"


def compare_images(path1: str, path2: str, diff_output: str | None = None) -> bool:
    """
    Compare two images at pixel level.

    Returns True if the images are identical, False otherwise.
    Writes a visual diff image to *diff_output* when provided and images differ.
    """
    # Load images
    img1 = load_image(path1)
    img2 = load_image(path2)

    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]

    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD}Image 1:{RESET} {path1}  [{w1}×{h1}]")
    print(f"{BOLD}Image 2:{RESET} {path2}  [{w2}×{h2}]")
    print(f"{'─'*60}")

    # Check images dimension (w, h) 
    if (h1, w1) != (h2, w2):
        print(f"\n{RED}✗  DIFFERENT  —  dimensions do not match{RESET}")
        print(f"   Image 1: {w1}×{h1} px")
        print(f"   Image 2: {w2}×{h2} px")
        return False

    # Normalize channels (from rgb to greyscale)
    img1n, img2n, colour_space = normalise_channels(img1, img2)

    print(f"\n{CYAN}✓  DIMENSIONS MATCH  —  both images are {w1}×{h1} px{RESET}")

    # Compute pixel-level-difference
    diff = cv2.absdiff(img1n, img2n)         # |pixel_A − pixel_B|
    diff_mask = diff > 0                     # True wherever pixels differ
    total_pixels = h1 * w1
    changed_pixels = int(np.count_nonzero(
        diff_mask if diff_mask.ndim == 2 else np.any(diff_mask, axis=2)
    ))

    # identical = changed_pixels == 0

    # Print Summary
    print(f"\n{BOLD}Colour space:{RESET} {colour_space}")
    print(f"{BOLD}Dimensions  :{RESET} {w1}×{h1} px  ({total_pixels:,} total pixels)")

    if changed_pixels == 0:
        print(f"\n{GREEN}{BOLD}✓  IDENTICAL  —  every pixel matches exactly{RESET}\n")
        # return changed_pixel
    else:
        pct = changed_pixels / total_pixels * 100
        max_diff = int(diff.max())
        mean_diff = float(diff[diff > 0].mean()) if changed_pixels else 0.0

        print(f"\n{RED}{BOLD}✗  DIFFERENT{RESET}")
        print(f"   Changed pixels : {changed_pixels:,} / {total_pixels:,}  ({pct:.4f} %)")
        print(f"   Max  |Δ| value : {max_diff}  (out of 255)")
        print(f"   Mean |Δ| value : {mean_diff:.2f}  (changed pixels only)")

        # Bounding box of the changed region
        coords = np.argwhere(
            diff_mask if diff_mask.ndim == 2 else np.any(diff_mask, axis=2)
        )
        y0, x0 = coords.min(axis=0)
        y1, x1 = coords.max(axis=0)
        print(f"   Changed region : x={x0}–{x1}, y={y0}–{y1}")

        # Optional diff image
        if diff_output:
            # Amplify the diff so small changes are visible
            diff_vis = (diff.astype(np.float32) * (255.0 / max(max_diff, 1))).astype(np.uint8)
            if diff_vis.ndim == 2:
                diff_vis = cv2.cvtColor(diff_vis, cv2.COLOR_GRAY2BGR)

            # Highlight changed pixels in red on a side-by-side canvas
            if img1n.ndim == 2:
                base = cv2.cvtColor(img1n, cv2.COLOR_GRAY2BGR)
            elif img1n.shape[2] == 4:
                base = cv2.cvtColor(img1n, cv2.COLOR_BGRA2BGR)
            else:
                base = img1n.copy()

            overlay = base.copy()
            mask2d = diff_mask if diff_mask.ndim == 2 else np.any(diff_mask, axis=2) # >
            overlay[mask2d] = (0, 0, 255)   # red highlights

            canvas = np.hstack([base, overlay, diff_vis])
            cv2.imwrite(diff_output, canvas)
            print(f"\n   Diff image saved → {diff_output}")
            print("   (left = image 1 | centre = changed pixels in red | right = amplified diff)")

    print(f"{'─'*60}\n")
    return changed_pixels == 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Compare two images at the pixel level.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
--------
  # Basic comparison
  python compare_images.py photo_a.png photo_b.png

  # Save a visual diff image
  python compare_images.py photo_a.jpg photo_b.jpg --diff-output diff.png

Exit codes
----------
  0  — images are identical
  1  — images differ (or an error occurred)
""",
    )
    p.add_argument("image1", help="Path to the first image")
    p.add_argument("image2", help="Path to the second image")
    p.add_argument(
        "--diff-output",
        metavar="PATH",
        default=None,
        help="If provided, save a side-by-side diff image to this path (PNG recommended)",
    )
    return p


def main() -> None:
    args = build_parser().parse_args()
    try:
        identical = compare_images(args.image1, args.image2, args.diff_output)
        sys.exit(0 if identical else 1)
    except FileNotFoundError as exc:
        print(f"\n{RED}Error: {exc}{RESET}\n", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\n{RED}Unexpected error: {exc}{RESET}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()