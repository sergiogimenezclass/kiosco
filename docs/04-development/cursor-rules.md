# cursor-rules.md

# Reglas para Cursor / OpenClaw / Claude Code

## Objetivo

Generar un MVP estable de POS para kioscos respetando estrictamente la documentación.

## Reglas obligatorias

1. No inventar funcionalidades fuera de alcance.
2. No agregar AFIP/ARCA.
3. No agregar multi-tenant.
4. No agregar multi-sucursal.
5. No agregar venta mixta.
6. No agregar ventas pendientes.
7. No permitir stock negativo.
8. No editar ventas guardadas.
9. Usar transacciones SQLite para ventas, anulaciones, devoluciones y stock.
10. Guardar montos como INTEGER en centavos.
11. Guardar cantidades pesables en unidad mínima.
12. Validar permisos en backend, no solo frontend.
13. Mantener frontend Vanilla JS.
14. No introducir React/Vue/Svelte.
15. No introducir PostgreSQL en MVP.
16. No usar ORM complejo si no es necesario.
17. Mantener código simple, modular y testeable.

## Orden recomendado de generación

1. database/schema.sql
2. app/core/database.py
3. app/core/security.py
4. schemas Pydantic
5. repositories
6. services
7. routers FastAPI
8. tests backend
9. frontend POS
10. reportes/exportaciones

## Criterio de calidad

Cada módulo debe incluir:

- Validaciones.
- Manejo de errores.
- Tests mínimos.
- Comentarios solo donde aporten.
- Tipado.
- Nombres claros.
