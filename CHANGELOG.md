# Changelog

## 0.1.21 — Home Book Carousel support

- Explicitly enable the firmware-owned Book Carousel for the existing native cover card.
- Retain the approved visuals and artwork; compatible firmware handles bounded Home navigation.

## Unreleased — Publishing consistency with Halo

- Publish on a matching `vMAJOR.MINOR.PATCH` Git tag, with a single release holding X3 and X4Plus ZIPs.
- Package only committed manifest, theme configuration, fonts, CPB, USB, and per-device grayscale sleep artwork; do not regenerate images during release.
- Align the checked-in CPB and sleep assets with the already-published v0.1.20 ZIPs to preserve the approved visuals.
- Separate development artwork generation from releases and preserve the GitHub README.
- Retain the X3 `ZIP_STORED` low-memory installer format; keep X4Plus ZIP compression.

## 0.1.20 — Native header status alignment

- Fit Snoopy's header artwork beneath the firmware-owned clock and battery strip without increasing header height.
- Preserve the on-screen Back arrow alongside the theme emblem on touch models.
- Continue offering native-resolution X3 and X4Plus ZIP assets with the ten grayscale sleep scenes and USB artwork.

## 0.1.19 — Full-bleed grayscale USB artwork

- Include native four-tone USB graphics and their monochrome fallback.
- Preserve the ten grayscale sleep scenes and compact X3 installation packages.
