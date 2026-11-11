# Snoopy theme authoring and publishing

Snoopy and [Halo](https://github.com/jadehawk/halo.crosspoint-theme) use the same release pattern: committed theme metadata is authoritative, a version tag triggers GitHub Actions, and one release contains separate X3 and X4Plus ZIPs.

## Validate and package existing committed artwork

```powershell
python -m pip install Pillow
python tools/pack_theme_variants.py
python -m unittest discover -s tests -p "test_*.py" -q
```

`pack_theme_variants.py` reads `snoopy.crosspoint-theme/manifest.json`, `themes/snoopy/theme.json`, the committed CPBs, USB BMPs, fonts, and packaged docs. It reads ten **committed** X3 and ten X4Plus sleep BMPs from `source-art/release-sleep/<profile>/` and writes install-only ZIPs to ignored `dist/`. It **never rewrites committed theme configuration, assets, or either README**.

Keep X3 ZIP entries `ZIP_STORED`: its no-PSRAM inflater can fail to allocate a 32-KiB DEFLATE window. Keep X4Plus ZIP entries compressed.

## Changing artwork (development only)

Run `python tools/build.py` only when you intend to regenerate authored CPB/USB imagery and illustrative previews. It no longer rewrites the theme definition, manifest, README, or license details, and does not publish a release. Inspect the asset diffs and commit intentional changes.

To change the sleep gallery, run `python tools/prepare_sleep_grayscale.py` as an authoring tool, inspect its candidate files under `dist/sleep-grayscale/{x3,x4plus}/`, and deliberately copy the approved BMPs into `source-art/release-sleep/` before committing. The release packager never runs this conversion, so Pillow-version differences cannot silently change published wallpaper pixels.

Font assets require `python tools/build_fonts.py` when changing font sources.

## Publishing

Update the manifest version, matching documentation, and `CHANGELOG.md` before creating the version tag. Push reviewed changes to `main`, then push `vMAJOR.MINOR.PATCH`. `.github/workflows/release.yml` validates the matching tag, builds both ZIP variants, runs tests and publishes both assets under `Snoopy vMAJOR.MINOR.PATCH`. `validate-theme.yml` performs the same integrity checks on pull requests, `main`, and tags.

The packed `snoopy.crosspoint-theme/README.md` must stay short, ASCII and within 2048 bytes for device display; the root `README.md` is the GitHub landing page.
