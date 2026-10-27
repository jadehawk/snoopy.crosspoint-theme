# Snoopy CrossPoint Theme (X3-first prototype)

An **unofficial, non-commercial fan-made theme** with AI-generated Snoopy and Woodstock illustrations. It is a CrossPoint theme pack, not a plugin or firmware.

## Install

Download the device-matched `snoopy-x3-0.1.16.crosspoint-theme.zip` or `snoopy-x4plus-0.1.16.crosspoint-theme.zip` via The Cantina Store, or extract either ZIP to SD path:

```
/.crosspoint/themes/snoopy.crosspoint-theme/
```

Then use **Settings -> Display -> UI Theme -> Snoopy** and return to Home.
Select a firmware Dark/Light sleep screen to test the theme's sleep image; Custom sleep pools take precedence.

## X3-specific corrections to the concept

1. The X3 is 528 x 792 and has no touch interface. This version uses one native Continue Reading card and a navigable list, not the concept's four-cover touchscreen grid.
2. A 76px Home/Settings header leaves space for firmware-owned battery, title and Back actions; the Snoopy heart is now inset fully within the emblem.
3. The Home tile expands into previously unused X3 space to restore a real cached cover, book title, author, and actual progress bar when available; firmware keeps book selection and menu behavior.
4. UI decorations remain CPB v1 monochrome; USB and ten sleep illustrations use native four-tone grayscale BMPs.
5. Sleep and USB artwork are exported independently at 528 x 792 (X3) and 480 x 800 (X4+).
6. DynaPuff is bundled as four size-specific one-bit v4 CPFONT files. Stock fonts remain the firmware fallback.

## Limitations

- Theme schemas cannot replace the firmware's core Home layout, add new menu actions, draw live book grids, or add touch control on X3.
- Full-screen theme sleep galleries are used for Dark/Light regular sleep entries, not the independent timed sleep refresh pool.
- This unofficial, non-commercial theme uses Snoopy and Woodstock characters; all Peanuts character trademarks and copyrights remain with their respective rights holders. It is not endorsed by them.
- Version 0.1.16 ships independent X3 and X4+ archives under one Snoopy theme identity, each with 10 randomly rotated grayscale sleep scenes and a native grayscale USB screen. Hardware testing is ongoing.

## Files

- `snoopy.crosspoint-theme/` is the only installable payload. It contains no executable scripts.
- `source-art/` contains the approved X3 Home and doghouse art. The two larger touch-footer CPBs are recomposed directly from those original sources; the experimental full-page Woodstock image is not included or activated.
- `source-fonts/` contains the upstream DynaPuff TTF and SIL OFL license. Run `python tools/build_fonts.py` before `python tools/build.py` when updating font assets.
- `previews/` has illustrative X3-size previews, not exact firmware screenshots.

Compatibility is capability-based. Snoopy v0.1.16 requires `theme.sleep-grayscale.v1` and `theme.usb-grayscale.v1` as well as the declared standard theme capabilities; only firmware exposing all required capabilities should install the theme. No branded firmware name is a requirement.
