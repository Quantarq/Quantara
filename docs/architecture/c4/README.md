# Quantara C4 architecture

These diagrams describe Quantara at three C4 levels:

- [System context](context.svg) shows Quantara's users and external ecosystem dependencies.
- [Containers](container.svg) shows the deployable applications and data stores.
- [Backend components](component.svg) shows the main responsibilities inside the FastAPI backend.

The SVG files are generated from the adjacent PlantUML sources. Regenerate them with PlantUML whenever a source file changes:

```bash
plantuml -tsvg docs/architecture/c4/*.puml
```
