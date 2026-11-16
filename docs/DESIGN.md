---
name: CMF Speaker S Local Console
description: A read-back-true sound console for one or two CMF Speaker S units on Linux.
colors:
  graphite-ground: "#0a0a0b"
  graphite-panel: "#111113"
  graphite-raised: "#161619"
  hairline: "#26262b"
  hairline-strong: "#34343a"
  warm-white: "#f4f2ec"
  warm-grey: "#b4b1a8"
  muted-grey: "#8a877f"
  signal-orange: "#ff5a36"
  signal-orange-hover: "#ff7052"
  signal-ink: "#0a0a0b"
  signal-deep: "#a33a22"
  alert-coral: "#ff6b5e"
  focus-orange: "#ff8a66"
typography:
  display:
    fontFamily: "Doto, Archivo, monospace"
    fontSize: "84px"
    fontWeight: 700
    lineHeight: 0.78
    letterSpacing: "0.01em"
  headline:
    fontFamily: "Archivo, Noto Sans, system-ui, sans-serif"
    fontSize: "30px"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Archivo, Noto Sans, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.45
  body:
    fontFamily: "Archivo, Noto Sans, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
  control:
    fontFamily: "Archivo, Noto Sans, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.45
  small:
    fontFamily: "Archivo, Noto Sans, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.45
  note:
    fontFamily: "Archivo, Noto Sans, system-ui, sans-serif"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Archivo, Noto Sans, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.45
    letterSpacing: "0.08em"
rounded:
  panel: "3px"
  control: "2px"
  track: "9px"
  scrollbar: "6px"
spacing:
  xs: "6px"
  sm: "10px"
  md: "16px"
  lg: "22px"
  xl: "28px"
components:
  button-primary:
    backgroundColor: "{colors.signal-orange}"
    textColor: "{colors.signal-ink}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
    typography: "{typography.control}"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.warm-grey}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
    typography: "{typography.control}"
  target-selected:
    backgroundColor: "{colors.signal-orange}"
    textColor: "{colors.signal-ink}"
    rounded: "{rounded.control}"
    padding: "8px 13px"
  level-selected:
    backgroundColor: "rgba(255, 90, 54, 0.14)"
    textColor: "{colors.signal-orange}"
    rounded: "{rounded.control}"
    padding: "8px 10px"
  unit-panel:
    backgroundColor: "{colors.graphite-panel}"
    rounded: "{rounded.panel}"
    padding: "16px"
  chip:
    backgroundColor: "transparent"
    textColor: "{colors.muted-grey}"
    rounded: "{rounded.control}"
    padding: "3px 7px"
    typography: "{typography.label}"
---

# Design System: CMF Speaker S Local Console

## Overview

**Creative North Star: "The Grille at Night"**

This is a device console, not a settings page. The room is dark; the speaker is the only lit object; the screen is the laptop beside it. The interface keeps that scene: a graphite ground the color of the cabinet, a warm-white readout, one signal orange where the device would use an LED, and hairlines where a molded seam would be. Nothing glows for decoration. The dot matrix is the one expressive material, and it always carries a measured number or the stored custom EQ.

The system is deliberately flat and dense. Depth comes from two graphite planes and 1px rules, never from shadows. The eye reads the unit strips first — name, MAC, battery, the dot field — then moves to the sound controls. Orange is scarce: a selected preset, an enabled state, the primary pairing action, a low battery. Everything else is warm grey on graphite.

**Key Characteristics:**
- Graphite ground, warm-white text, one signal-orange accent.
- Doto dot numerals only at display size; Archivo for every label, value, and note.
- 1px hairlines and 2px control corners; no shadows, gradients, or glass.
- The 32×6 dot matrix is a data field, not ornament.
- Every displayed value is the device's read-back, never the requested value.

## Colors

The palette is a dark room with one indicator lamp: graphite neutrals carry the whole surface, and signal orange is reserved for action, selection, and state.

### Primary
- **Signal Orange** (`#ff5a36`): the primary action (`Pair stereo`), the selected target/preset, the active custom EQ dots, a low battery, and the focus ring's warmer sibling. It never appears as decoration.
- **Signal Orange Hover** (`#ff7052`): the lighter orange used only on the primary button's hover fill.
- **Signal Ink** (`#0a0a0b`): text on orange fills; identical to the ground so the fill reads as a lit panel.

### Neutral
- **Graphite Ground** (`#0a0a0b`): page background and the space between panels.
- **Graphite Panel** (`#111113`): unit strips and the empty-slot panel.
- **Graphite Raised** (`#161619`): the toast surface.
- **Hairline** (`#26262b`): section separators, panel borders, chip borders.
- **Hairline Strong** (`#34343a`): control borders, inactive meter dots, pressed-level inset rule.
- **Warm White** (`#f4f2ec`): headings, values, active labels.
- **Warm Grey** (`#b4b1a8`): secondary text, slider thumbs, connected status.
- **Muted Grey** (`#8a877f`): notes, metadata, inactive labels.

### Semantic
- **Alert Coral** (`#ff6b5e`): banner border/text and the ungroup action.
- **Signal Deep** (`#a33a22`): the A2DP badge border, a dimmed orange edge.

### Named Rules

**The One Signal Rule.** Orange marks action, selection, or a device state that needs attention. If it is not clickable, chosen, or measured, it is warm grey.

**The Read-Back Rule.** Color reports the device's state, not the interface's request. A pending write never recolors the control; the response does.

## Typography

**Display Font:** Doto (self-hosted; fallback Archivo, monospace)
**Body Font:** Archivo (self-hosted; fallback Noto Sans, system-ui, sans-serif)

**Character:** Doto is a dot-matrix face and supplies the one loud voice: the battery readout. Archivo is the quiet workhorse for every label, note, and numeric value. The pairing is a lit LED display above a control panel.

### Hierarchy
- **Display** (Doto 700, 84px, 0.78 line-height, 0.01em tracking): the battery percentage in each unit strip. Never below 32px; the dots stop resolving.
- **Headline** (Archivo 600, 30px, 1.1 line-height, -0.025em): the single page heading, `Sound`.
- **Title** (Archivo 600, 15px): unit names; section headings use 13px uppercase with 0.06em tracking.
- **Body** (Archivo 400, 14px, 1.45): the shared workhorse.
- **Control** (Archivo 500, 12px): buttons, selects, the banner close, and control labels.
- **Small** (Archivo 400, 13px): the workspace lede, stereo status line, and band value outputs, with tabular figures where numeric.
- **Note** (Archivo 400, 12.5px, 1.55): explanatory notes, capped at 60ch.
- **Label** (Archivo 500, 11px, 0.08–0.14em, uppercase): chips, badges, matrix captions, band labels. Numeric values use tabular figures.

### Named Rules

**The Dot Numerals Rule.** Doto carries large measured numerals only. At 16px its dots read as noise; band values, notes, and labels use Archivo.

**The Functional Floor Rule.** No interactive or content-bearing text below 11px. Notes and explanatory copy sit at 12.5px; body at 14px.

## Layout

A two-column console: a 360px unit rail on the left, a fluid sound workspace on the right, both separated by a hairline. The rail stacks 352px unit panels and a 152px dashed empty slot. The workspace caps its reading width naturally and uses a 172px label column beside each control body, separated by 24px.

Vertical rhythm is 20px per section with a 1px rule between; headings get more space above than below. At 1050px the rail narrows to 320px and the label column to 148px. At 860px the layout collapses to one column, the unit rail becomes a horizontal scroller, and each section stacks its label above its controls. At 560px the rail stays a horizontal scroller with 280px cards, so the sound controls remain close to the first viewport; the preset row becomes a two-column grid and the bands become one column. The page is designed at a fixed rem scale, not fluid type.

## Elevation & Depth

No shadows. The system is flat: depth is a tonal step from ground to panel to raised toast, plus 1px hairlines. A dashed 1px border marks the empty second-unit slot. The toast is a bordered raised plane, not a floating card.

**The Flat-By-Default Rule.** If an element needs to separate, change its ground or add a hairline; do not add a shadow. The only shadow-like device is the 4px ground ring around the range thumb, which is a cutout, not elevation.

## Shapes

Corners are 3px on panels and 2px on every control; the switch track is the one 9px capsule. Borders are 1px and always a graphite hairline; the dashed empty slot is the only dashed outline. Circles are reserved for dots, LEDs, and the range thumb. No pills, no large radii, no clipped polygons.

## Components

### Buttons
- **Shape:** 2px radius, 1px border, 7px × 12px padding, 12px label.
- **Primary:** signal orange fill with signal-ink text; the pairing action and confirm state.
- **Quiet:** transparent with a hairline-strong border and warm-grey text; hover lifts the text to warm white and the border to warm grey.
- **Danger:** quiet treatment with alert-coral text and a 40%-mixed coral border; used for ungroup.
- **Confirmable actions:** pair and ungroup never fire on the first click. The button flips to `Confirm pair` / `Confirm ungroup`, an inline coral note names the consequence, and the action fires only on the second click within six seconds; any re-render cancels it.
- **Focus:** 2px focus-orange outline at 2px offset; focus is never conveyed by fill alone.

### Segmented Controls
- **Target:** pill-free 2px-radius strip with 1px dividers; the selected segment is a full signal-orange fill with signal-ink text. Hidden while a stereo pair is active; the lede states that sound applies to the pair.
- **Levels (Ultra Bass):** the selected segment is a 14%-orange wash, signal-orange text, and a 2px inset signal-orange rule at the bottom. This is deliberately quieter than the target selection.

### Switches
- **Track:** 34×18px, 9px radius, hairline-strong border; off is transparent.
- **Thumb:** 10px circle, muted grey; 3px inset.
- **On:** the track takes an 18%-orange wash with a signal-orange border; the thumb turns orange and translates 16px.
- **Mixed:** the thumb centers and stays muted.

### Range Inputs
- **Track:** 2px hairline-strong line.
- **Thumb:** 14px warm-white circle with a 4px ground ring.
- **Focus:** the thumb turns signal orange. The value sits above the track in Archivo 13px tabular figures, never Doto.

### Chips
- **Style:** 2px radius, 1px hairline border, 3px × 7px padding, 11px uppercase muted grey.
- **On:** the border strengthens to hairline-strong and the text to warm white.
- **Content:** label plus measured value (`Night 300 min`, `Bass level 3`), never an icon standing in for the state.

### Unit Panel
- **Container:** graphite panel, 1px hairline border, 3px radius, 16px padding.
- **Contents:** name and MAC, an AUDIO/CONTROL badge (A2DP audio vs BLE control only), an 84px Doto battery numeral, a 10-dot battery meter, firmware/protocol metadata, the dot matrix, three state chips, Find, and the stereo role.
- **Empty slot:** dashed hairline border, 12 dim dots, "Second unit", a 12.5px note, and a quiet Rescan.

### Dot Matrix (Signature)
- **Grid:** 32 columns × 6 rows, 2px gaps, circular dots.
- **Ink:** inactive `#202024`, fill `#2b2b30`, line warm grey; active custom mode turns the line and fill signal orange.
- **Meaning:** each column is a frequency position; the lit line is the stored 3-band custom EQ (low 140 Hz, mid 980 Hz, high 3.4 kHz). The caption says `stored` or `active`. It never invents a curve for a preset.
- **Redraw:** the matrix keeps its 192 nodes across read-backs and toggles classes in place, with a 5ms-per-column transition delay so a confirmed change sweeps left to right. Reduced motion removes both the duration and the delay.

### Banner and Toast
- **Banner:** a full-width strip under the topbar, 8%-coral wash, 45%-coral bottom hairline, 12px body text, a quiet close control.
- **Toast:** a raised graphite panel with a hairline-strong border, 2px radius, 10px × 14px padding, 12px text; it enters with an 8px translate and a 180ms ease, and never blocks the pointer.

## Do's and Don'ts

### Do:
- **Do** show the device's read-back after every write; a control's resting style is the last confirmed state.
- **Do** keep orange for selection, action, active custom EQ, and low battery only.
- **Do** use Doto at 32px or larger, and only for measured numerals.
- **Do** use 1px hairlines and 2px control corners to build structure.
- **Do** say `Units differ` when the selected units disagree, and sync them only when the user applies a value.
- **Do** label the matrix `stored` or `active` and derive it from C044/C01F, not from the requested mode.
- **Do** keep every functional label at 11px or larger and explanatory notes at 12.5px.
- **Do** disable Night's auto-off select until Night mode is on, and show `Mixed` rather than a duration no unit reported.

### Don't:
- **Don't** use Doto for band values, notes, labels, or anything below 32px.
- **Don't** use orange as decoration, for inactive states, or for a pending write.
- **Don't** use shadows, gradients, glass, nested cards, or pills.
- **Don't** draw an EQ curve for a preset the device does not expose; the matrix shows only the stored custom bands.
- **Don't** replace measured state with an icon or a colored dot without a text label.
- **Don't** hide a device interlock; show the post-write state and let the copy name the rule.
- **Don't** show an auto-off duration while Night is off, or a common duration when the units disagree; use the disabled dependency and `Mixed`.
