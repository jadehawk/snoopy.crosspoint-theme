# Snoopy CrossPoint Theme (X3-first prototype)

An **unofficial, non-commercial fan-made theme** with AI-generated Snoopy and Woodstock illustrations. It is a CrossPoint theme pack, not a plugin or firmware.

## Install

Download the device-matched `snoopy-x3-0.1.13.crosspoint-theme.zip` or `snoopy-x4plus-0.1.13.crosspoint-theme.zip` via The Cantina Store, or extract either ZIP to SD path:

```
/.crosspoint/themes/snoopy.crosspoint-theme/
```

Then use **Settings -> Display -> UI Theme -> Snoopy** and return to Home.
Select a firmware Dark/Light sleep screen to test the theme's sleep image; Custom sleep pools take precedence.

## X3-specific corrections to the concept

1. The X3 is 528 x 792 and has no touch interface. This version uses one native Continue Reading card and a navigable list, not the concept's four-cover touchscreen grid.
2. A 76px Home/Settings header leaves space for firmware-owned battery, title and Back actions; the Snoopy heart is now inset fully within the emblem.
3. The Home tile expands into previously unused X3 space to restore a real cached cover, book title, author, and actual progress bar when available; firmware keeps book selection and menu behavior.
4. All graphics are CPB v1, 1-bit black/white. Colors in the source artwork become e-ink grayscale/dithered monochrome.
5. Sleep art is a fixed X3-sized 528 x 792 background. Preview it on-device before adopting for other displays.
6. DynaPuff is bundled as four size-specific one-bit v4 CPFONT files. Stock fonts remain the firmware fallback.

## Limitations

- Theme schemas cannot replace the firmware's core Home layout, add new menu actions, draw live book grids, or add touch control on X3.
- Full-screen theme sleep galleries are used for Dark/Light regular sleep entries, not the independent timed sleep refresh pool.
- This unofficial, non-commercial theme uses Snoopy and Woodstock characters; all Peanuts character trademarks and copyrights remain with their respective rights holders. It is not endorsed by them.
- Version 0.1.13 ships independent X3 and X4+ archives under one Snoopy theme identity, each with 23 randomly rotated sleep scenes. X3 artwork is unchanged; hardware testing is ongoing.

## Files

- `snoopy.crosspoint-theme/` is the only installable payload. It contains no executable scripts.
- `source-art/` contains the approved X3 Home and doghouse art. The two larger touch-footer CPBs are recomposed directly from those original sources; the experimental full-page Woodstock image is not included or activated.
- `source-fonts/` contains the upstream DynaPuff TTF and SIL OFL license. Run `python tools/build_fonts.py` before `python tools/build.py` when updating font assets.
- `previews/` has illustrative X3-size previews, not exact firmware screenshots.

Compatibility is capability-based. Snoopy v0.1.13 additionally requires `theme.book-cover.v1`, `theme.screen-decoration.v1`, `theme.fonts.v1`, and `theme.font-family.v1`; older firmware must reject this feature rather than degrade to a fake book cover. No branded firmware name is a requirement.
