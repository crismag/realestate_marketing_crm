# Design reuse rules
Use fixed source revision from DESIGN_SOURCE.yaml. Manifest inspected: @crisgen/ui 1.1.0 private package; install from checkout/tarball rather than assumed public npm.
Manifest exposes React/Vue and their patterns, vanilla CSS/runtime, Web Components, CSS Modules, Tailwind and SCSS targets. App framework remains undecided; availability of exports does not select it.
Inspect exact selected export, implementation/types, example and behavior before task executable snippets. Reuse patterns/components/semantic tokens first. Compose CRM behavior in app files; never hand-edit upstream generated targets or modify unrelated design systems.
README theme setup: load theme CSS after base/component styles; data-cg-theme=crisgen-light or data-theme=dark plus data-cg-theme=crisgen-dark. This documented setup is not an app integration test.
Documentation discrepancy: README and llms.txt give different behavior counts; do not use counts as coverage evidence.
Partial catalogs disclose missing sources. Record a scoped gap and rationale before bespoke equivalent or adapter. Framework incompatibility needs an explicit decision; do not silently substitute a UI library.
