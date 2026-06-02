# Google Stitch UI Specification: Kiosk POS

## 1. Project Identity & Theme Configuration

* **Application Name:** Kiosk Billing & Cash POS

* **Interface Density:** High Density (Optimized for maximum data presentation on small touch screens)

* **Design Philosophy:** Utilitarian, tactile, keyboard-driven, low-latency.

* **Color System:** Dark/High-Contrast Mode Default (reduces eye strain in 24/7 kiosk environments). Supports adaptive Light Mode.

### Design Tokens (Material 3 Alignment)

| Token Name | Value (Hex) | Semantic Use | 
| ----- | ----- | ----- | 
| `--color-primary` | `#0284C7` (Sky Blue) | Primary actions, current focus outline, active navigation. | 
| `--color-success` | `#16A34A` (Emerald Green) | Cash totals, payment confirmation, successful checkout. | 
| `--color-warning` | `#D97706` (Amber) | Low stock warning, digital payment processing. | 
| `--color-error` | `#DC2626` (Red) | Out of stock, cash register deviation, cancel action. | 
| `--color-bg-dark` | `#0F172A` (Slate 900) | Root application background. | 
| `--color-surface-dark` | `#1E293B` (Slate 800) | Card containers, Cart panel, Modal backgrounds. | 
| `--color-text-primary` | `#F8FAFC` (Slate 50) | High-contrast body text. | 
| `--color-text-muted` | `#94A3B8` (Slate 400) | Secondary information (Barcode, Category tags). | 

### Typography

* **Primary Font Family:** System Sans-Serif (`ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto`) for UI elements and fast scanning.

* **Numeric Font Family:** Monospace (`ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono"`) for prices, quantities, and barcode alignment.

## 2. Layout & Grid Architecture

The viewport must be strictly locked to `100vh` / `100vw` without default body scroll. The screen is split into a **Two-Column Grid** designed to fit an aspect ratio of `16:9` or `4:3`.

+-----------------------------------------------------------------------------+
| [Header] Cashier: Juan | Shift Status: OPEN | Current Box ID: xxxx-xxxx     |
+------------------------------------------------------+----------------------+
| [Column 1 - Catalog & Quick Access: 65% width]       | [Column 2 - Cart]    |
|                                                      | [35% width]          |
| +--------------------------------------------------+ | +------------------+ |
| | [Search Input (Focus Local: bar code or text)]   | | | [Cart Items List] | |
| +--------------------------------------------------+ | | - Item 1 (Qty x) | |
|                                                      | | - Item 2 (Qty x) | |
| +--------------------------------------------------+ | |                    | |
| | [Quick Access Grid - Tabbed]                      | | |                    | |
| | +-----------+ +-----------+ +-----------+          | | |                    | |
| | | Cigarette | | Soft Drink| | Ice       |          | | +------------------+ |
| | +-----------+ +-----------+ +-----------+          | | | [Summary Box]    | |
| |                                                  | | | TOTAL: $ 12,500  | |
| |                                                  | | +------------------+ |
| |                                                  | | | [Action Buttons] | |
| |                                                  | | | F2-PAY   F9-CLEAR| |
| +--------------------------------------------------+ | +------------------+ |
+------------------------------------------------------+----------------------+


### Component Breakdown by Section

1. **Top Status Bar (Header):** Full width. Minimal height (`48px`). Displays active shift, box status, and online/offline connectivity indicator.

2. **Left Panel (65%):** Catalog explorer.

   * Top-half: Search Bar with persistent autofocus.

   * Bottom-half: Grid Layout for "Quick Access Items" (items without physical barcodes). Hit target minimum of `64px` for touch accessibility.

3. **Right Panel (35%):** Cart and Action controls.

   * Flex Column configuration:

     * Product List Container (`flex-grow: 1`, vertical scrollbar enabled when content overflows).

     * Totals Summary Panel (fixed to bottom, font size minimum `32px` for total amount).

## 3. UI Component Specifications

### 3.1. Keyboard Focus States & Outlines

* **Focus State:** Any active/focused input or item must show a `--color-primary` border with `outline-offset: 2px` and a box-shadow of `0 0 0 4px rgba(2, 132, 199, 0.4)`.

* **Selected Row (Cart):** Background color changes to `rgba(2, 132, 199, 0.15)` with a solid vertical indicator block on the left edge.

### 3.2. Tactile Buttons (Grid / Actions)

* **Quick Access Button:**

  * Background: `--color-surface-dark` with a subtle top border gradient.

  * Border: `1px solid rgba(148, 163, 184, 0.1)`.

  * Padding: `16px 12px`.

  * Text Alignment: Centered. Uses a stacked layout: `[Emoji/Icon] <br> [Short Label] <br> [Price]`.

* **Checkout Button (F2 / Pay):**

  * Background: `--color-success`.

  * Text Color: Pure white.

  * Weight: Bold.

  * Height: `56px`.

### 3.3. Dialog / Modal (Checkout Overlay)

* **Backdrop Blur:** `backdrop-filter: blur(8px); background-color: rgba(15, 23, 42, 0.75)`.

* **Modal Body Card:**

  * Border Radius: `12px` (`rounded-xl`).

  * Width: Max `500px` (centered).

  * Padding: `24px` (`p-6`).

  * Layout: Strict vertical column layout.

## 4. Key Screen States for Implementation

### State A: No Open Box (Enforced Shift Start)

* Screen overlays a blurred shield over the POS.

* A single, focused modal demands input for "Monto Inicial de Apertura" (Opening Cash Amount).

* Text inputs are styled with a prefix icon (`$`).

### State B: Offline Indicator Alert

* A floating status badge in the header transitions from a subtle green dot (`Online`) to a flashing amber badge (`Offline Mode - Saving Locally`).

* Product searches and additions remain responsive using cached IndexedDB local stores.

### State C: Payment Modal (Cash Exchange)

* Input fields default to numeric virtual keyboard styles on touch devices.

* Vuelto (Change Due) calculation panel must flash with `--color-success` text color as soon as `Monto Recibido` is greater than or equal to `TOTAL`.