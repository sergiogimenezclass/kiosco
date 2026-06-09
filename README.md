# Kiosk Billing & Cash POS - Documentación MVP 1.0

Este paquete contiene la documentación completa para construir el MVP del sistema POS para kioscos.

## Estructura

```text
docs/
├── 00-discovery/
│   ├── encuesta-product-owner.json
│   └── decisiones-arquitectonicas.md
├── 01-functional/
│   └── functional-spec.md
├── 02-technical/
│   ├── technical-spec.md
│   ├── data-model.md
│   ├── erd.md
│   ├── api-spec.md
│   ├── database-schema.sql
│   └── openapi.yaml
├── 03-design/
│   ├── design-system.md
│   ├── wireframes.md
│   └── user-flows.md
├── 04-development/
│   ├── implementation-tasks.md
│   ├── test-plan.md
│   └── cursor-rules.md
└── 05-archive/
```

## Uso recomendado

1. Leer `00-discovery/decisiones-arquitectonicas.md`.
2. Congelar alcance con `01-functional/functional-spec.md`.
3. Implementar base de datos desde `02-technical/database-schema.sql`.
4. Generar backend siguiendo `api-spec.md`.
5. Generar frontend siguiendo `03-design/`.
6. Usar `cursor-rules.md` como reglas del agente IA.

## Estado

Versión: MVP-SPEC-1.0
