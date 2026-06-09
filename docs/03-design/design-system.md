# design-system.md

# Sistema de Diseño - Kiosk POS

## Principios

- Alta densidad.
- Bajo contraste visual innecesario, alto contraste funcional.
- Operación con teclado primero.
- Compatible con pantalla táctil.
- Sin scroll global.
- Feedback inmediato.

## Tema

Modo oscuro por defecto.

| Token | Valor | Uso |
|---|---|---|
| --color-primary | #0284C7 | foco, acción principal |
| --color-success | #16A34A | confirmaciones, vuelto |
| --color-warning | #D97706 | alertas |
| --color-error | #DC2626 | errores, cancelaciones |
| --color-bg-dark | #0F172A | fondo |
| --color-surface-dark | #1E293B | paneles |
| --color-text-primary | #F8FAFC | texto principal |
| --color-text-muted | #94A3B8 | texto secundario |

## Tipografía

- UI: system-ui.
- Números: ui-monospace.

## Layout POS

- Header: 48px.
- Panel catálogo: 65%.
- Panel carrito: 35%.
- Total: mínimo 32px.
- Botones críticos: mínimo 56px.
- Botones táctiles: mínimo 48px.

## Estados visuales

- Caja cerrada: modal bloqueante.
- Producto sin stock: rojo.
- Scanner error: alerta amarilla + sonido.
- Vuelto suficiente: verde.
- Modo pantalla completa: recomendado.
