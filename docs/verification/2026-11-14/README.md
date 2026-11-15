# Verification evidence

The authoritative final regression result is final-regression/results.json. Content screenshots are in content/. Native 200% zoom assertions were run with native_zoom.py; the independently recaptured readable modal is zoom/ZOOM200-native-modal-top.png and the hero is zoom/ZOOM200-independent-hero.png.

Other screenshot / portability directories are diagnostic attempts, not final pass evidence. Early runs exposed a source-history dependency in inherited tests, generated-evidence hashing, and external CDN timing. These harness issues were addressed without weakening application assertions; the final full regression is run after the updates.

Headless Chromium's native-zoom screenshot at a nonzero page scroll sometimes captured a blank surface despite visible DOM. The modal was recaptured with the background page at scrollY=0, preserving its native 200% zoom and modal state. Blank diagnostic captures are not proof of rendering and must not be used as visual pass evidence.

See VERIFICATION_REPORT.md for final counts, inspected images and limitations.
