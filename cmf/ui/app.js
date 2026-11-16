"use strict";

const BANDS = ["low", "mid", "high"];
const COLS = 32;
const ROWS = 6;
const PRESET_IDS = { balanced: 0, voice: 1, treble: 2, bass: 3 };
const EQ_NAMES = { 0: "Balanced", 1: "Voice", 2: "More treble", 3: "More bass", 5: "Custom" };

const els = {
  units: document.getElementById("units"),
  controls: document.getElementById("controls"),
  workspaceEmpty: document.getElementById("workspace-empty"),
  targetSeg: document.getElementById("target-seg"),
  targetNote: document.getElementById("target-note"),
  linkState: document.getElementById("link-state"),
  pulse: document.getElementById("pulse"),
  refresh: document.getElementById("refresh"),
  rescan: document.getElementById("rescan"),
  banner: document.getElementById("banner"),
  bannerText: document.getElementById("banner-text"),
  bannerClose: document.getElementById("banner-close"),
  toast: document.getElementById("toast"),
  eqState: document.getElementById("eq-state"),
  presets: [...document.querySelectorAll(".preset")],
  bandInputs: {
    low: document.getElementById("band-low"),
    mid: document.getElementById("band-mid"),
    high: document.getElementById("band-high"),
  },
  bandOut: {
    low: document.getElementById("out-low"),
    mid: document.getElementById("out-mid"),
    high: document.getElementById("out-high"),
  },
  bassLevels: [...document.querySelectorAll("#bass-levels button")],
  bassState: document.getElementById("bass-state"),
  spatial: document.getElementById("spatial-on"),
  spatialState: document.getElementById("spatial-state"),
  night: document.getElementById("night-on"),
  nightMinutes: document.getElementById("night-minutes"),
  nightState: document.getElementById("night-state"),
  stereoState: document.getElementById("stereo-state"),
  stereoBody: document.getElementById("stereo-body"),
  unitTemplate: document.getElementById("unit-template"),
};

const matrixCache = new Map();

const state = {
  units: [],
  target: "all",
  busy: false,
  loading: true,
  customTimer: null,
  confirmAction: null,
  confirmTimer: null,
  toastTimer: null,
};

async function api(path, body) {
  const options =
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        };
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.error) {
    throw new Error(data.error || `Request failed (${response.status})`);
  }
  return data;
}

function liveUnits() {
  return state.units
    .filter((unit) => !unit.error)
    .sort((left, right) => Number(right.a2dp) - Number(left.a2dp));
}

function targetMacs() {
  if (state.target === "all") return liveUnits().map((unit) => unit.mac);
  return [state.target];
}

function common(values) {
  if (!values.length || values.some((value) => value === null || value === undefined)) return null;
  return values.every((value) => value === values[0]) ? values[0] : null;
}

function fmtGain(value) {
  const number = Math.abs(value) < 0.05 ? 0 : value;
  return `${number > 0 ? "+" : ""}${number.toFixed(1)} dB`;
}

function setBanner(message) {
  els.banner.hidden = !message;
  els.bannerText.textContent = message || "";
}

function toast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => els.toast.classList.remove("show"), 2600);
}

function updateTopStatus() {
  const live = liveUnits();
  const broken = state.units.some((unit) => unit.error);
  els.pulse.dataset.state = state.busy ? "scan" : broken ? "error" : live.length ? "live" : "off";
  if (state.busy) return;
  els.linkState.textContent = live.length
    ? `${live.length} control link${live.length === 1 ? "" : "s"}`
    : state.units.length
      ? "Link error"
      : "No units";
}

function setBusy(busy, message) {
  state.busy = busy;
  els.refresh.disabled = busy;
  els.rescan.disabled = busy;
  els.controls.inert = busy;
  els.targetSeg.inert = busy;
  if (busy && message) els.linkState.textContent = message;
  updateTopStatus();
}

function cancelConfirm() {
  clearTimeout(state.confirmTimer);
  state.confirmAction = null;
}

async function load(force = false) {
  state.loading = true;
  cancelConfirm();
  setBanner("");
  render();
  setBusy(true, force ? "Rescanning nearby…" : "Scanning nearby…");
  try {
    const data = await api(force ? "/api/scan" : "/api/session", {});
    state.units = data.states || [];
    if (data.errors && data.errors.length) setBanner(data.errors.join(" · "));
    if (force) toast("Rescan complete");
  } catch (error) {
    state.units = [];
    setBanner(error.message);
  } finally {
    state.loading = false;
    setBusy(false);
    render();
  }
}

async function refreshState() {
  if (state.busy) return;
  setBusy(true, "Refreshing…");
  try {
    const data = await api("/api/state");
    state.units = data.states || [];
    toast("State refreshed from the device");
  } catch (error) {
    setBanner(error.message);
  } finally {
    setBusy(false);
    render();
  }
}

async function setSetting(payload, successMessage) {
  if (state.busy) return;
  setBusy(true, "Applying…");
  try {
    const data = await api("/api/set", { ...payload, macs: targetMacs() });
    state.units = data.states || [];
    toast(successMessage || "Applied · read back from the device");
  } catch (error) {
    setBanner(error.message);
  } finally {
    setBusy(false);
    render();
  }
}

async function findUnit(mac) {
  if (state.busy) return;
  setBusy(true, "Locating…");
  try {
    const data = await api("/api/set", { action: "find", macs: [mac] });
    state.units = data.states || [];
    toast("Locating · the speaker will chime");
  } catch (error) {
    setBanner(error.message);
  } finally {
    setBusy(false);
    render();
  }
}

async function runPair(master, slave) {
  setBusy(true, "Pairing…");
  try {
    const data = await api("/api/pair", { master, slave });
    state.units = data.states || [];
    toast("Stereo paired · confirmed by the device");
  } catch (error) {
    setBanner(error.message);
  } finally {
    setBusy(false);
    render();
  }
}

async function runUngroup(master) {
  setBusy(true, "Ungrouping…");
  try {
    const data = await api("/api/ungroup", { master });
    state.units = data.states || [];
    toast("Stereo ungrouped · read back from the device");
  } catch (error) {
    setBanner(error.message);
  } finally {
    setBusy(false);
    render();
  }
}

function render() {
  cancelConfirm();
  updateTopStatus();
  if (state.loading) {
    renderSkeletons();
    return;
  }
  renderUnits();
  const live = liveUnits();
  const paired = live.some((unit) => unit.stereo && unit.stereo.mode === 1);
  if (paired) state.target = "all";
  renderTarget();
  els.controls.hidden = live.length === 0;
  els.workspaceEmpty.hidden = live.length !== 0;
  els.targetSeg.hidden = live.length < 2 || paired;
  if (live.length) {
    renderControls(live);
    renderStereo(live);
  } else {
    els.targetNote.textContent =
      "Connect a speaker to begin. Settings are applied to every connected unit and read back from the device.";
  }
}

function renderSkeletons() {
  els.units.replaceChildren();
  for (let index = 0; index < 2; index += 1) {
    const unit = document.createElement("div");
    unit.className = "skeleton-unit";
    unit.innerHTML = `
      <div class="sk" style="height:12px;width:52%"></div>
      <div class="sk" style="height:8px;width:70%"></div>
      <div class="sk" style="height:64px;width:44%;margin-top:6px"></div>
      <div class="sk" style="height:44px;margin-top:8px"></div>
      <div class="sk" style="height:9px;width:40%"></div>`;
    els.units.append(unit);
  }
  els.controls.hidden = true;
  els.workspaceEmpty.hidden = true;
  els.targetSeg.hidden = true;
}

function renderUnits() {
  els.units.replaceChildren();
  if (!state.units.length) {
    renderEmpty();
    return;
  }
  [...state.units]
    .sort((left, right) => Number(right.a2dp) - Number(left.a2dp))
    .forEach((unit) => {
      if (unit.error) renderBrokenUnit(unit);
      else renderUnit(unit);
    });
  if (state.units.length === 1 && !state.units[0].error) renderPlaceholder();
}

function renderPlaceholder() {
  const wrap = document.createElement("div");
  wrap.className = "unit-placeholder";
  const dots = document.createElement("div");
  dots.className = "placeholder-dots";
  dots.setAttribute("aria-hidden", "true");
  for (let index = 0; index < 12; index += 1) dots.append(document.createElement("i"));
  const title = document.createElement("h2");
  title.textContent = "Second unit";
  const copy = document.createElement("p");
  copy.textContent =
    "Power on another CMF Speaker S for stereo. Both units must be identical.";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn btn-quiet";
  button.textContent = "Rescan";
  button.addEventListener("click", () => load(true));
  wrap.append(dots, title, copy, button);
  els.units.append(wrap);
}

function renderEmpty() {
  const wrap = document.createElement("div");
  wrap.className = "empty";
  const title = document.createElement("h2");
  title.textContent = "No speakers found";
  const copy = document.createElement("p");
  copy.textContent =
    "Power on a CMF Speaker S and keep it within a few metres. If a phone is connected to it, disconnect Nothing X first.";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn btn-primary";
  button.textContent = "Rescan";
  button.addEventListener("click", () => load(true));
  wrap.append(title, copy, button);
  els.units.append(wrap);
}

function renderBrokenUnit(unit) {
  const wrap = document.createElement("article");
  wrap.className = "unit unit-error";
  const title = document.createElement("h2");
  title.textContent = unit.mac;
  const copy = document.createElement("p");
  copy.className = "note";
  copy.textContent = unit.error;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn btn-quiet";
  button.textContent = "Rescan";
  button.addEventListener("click", () => load(true));
  wrap.append(title, copy, button);
  els.units.append(wrap);
}

function renderUnit(unit) {
  const node = els.unitTemplate.content.firstElementChild.cloneNode(true);
  node.dataset.mac = unit.mac;
  node.querySelector(".unit-name").textContent = unit.name;
  node.querySelector(".unit-mac").textContent = unit.mac;

  const badge = node.querySelector(".unit-badge");
  badge.textContent = unit.a2dp ? "AUDIO" : "CONTROL";
  badge.dataset.a2dp = String(unit.a2dp);
  badge.title = unit.a2dp ? "Receives this laptop's audio" : "Control link only";

  node.querySelector(".battery-num").textContent =
    unit.battery === null || unit.battery === undefined ? "—" : unit.battery;

  const meter = node.querySelector(".battery-meter");
  for (let step = 1; step <= 10; step += 1) {
    const dot = document.createElement("i");
    if (unit.battery !== null && unit.battery !== undefined && step <= Math.round(unit.battery / 10)) {
      dot.className = "on";
      dot.dataset.low = String(unit.battery <= 20);
    }
    meter.append(dot);
  }

  node.querySelector(".meta-fw").textContent = unit.firmware ? `FW ${unit.firmware}` : "FW —";
  node.querySelector(".meta-proto").textContent = unit.protocol ? `PROTO ${unit.protocol}` : "PROTO —";

  const custom = unit.custom || {};
  const matrix = matrixCache.get(unit.mac) || createMatrix();
  matrixCache.set(unit.mac, matrix);
  matrix.dataset.active = String(unit.eq && unit.eq.id === 5);
  node.querySelector(".matrix").replaceWith(matrix);
  node.querySelector(".matrix-state").textContent = unit.eq && unit.eq.id === 5 ? "active" : "stored";

  const chips = node.querySelector(".chips");
  chips.append(
    chip("Night", unit.night ? (unit.night.on ? `${unit.night.minutes} min` : "off") : "—", Boolean(unit.night && unit.night.on)),
    chip("Spatial", unit.spatial === null || unit.spatial === undefined ? "—" : unit.spatial ? "on" : "off", Boolean(unit.spatial)),
    chip("Bass", unit.bass ? (unit.bass.on ? `level ${unit.bass.level}` : "off") : "—", Boolean(unit.bass && unit.bass.on)),
  );

  const find = node.querySelector(".find-btn");
  find.addEventListener("click", () => findUnit(unit.mac));

  node.querySelector(".unit-link").textContent =
    unit.stereo && unit.stereo.mode === 1
      ? unit.stereo.peer
        ? `Paired · ${unit.stereo.peer}`
        : "Paired"
      : "Single";

  els.units.append(node);
  // Two frames: the first paints the attached previous curve, the second starts the sweep.
  requestAnimationFrame(() =>
    requestAnimationFrame(() => updateMatrix(matrix, custom)),
  );
}

function chip(label, value, on) {
  const item = document.createElement("li");
  item.className = "chip";
  item.dataset.on = String(on);
  const name = document.createElement("b");
  name.textContent = label;
  item.append(name, document.createTextNode(` ${value}`));
  return item;
}

function createMatrix() {
  const matrix = document.createElement("div");
  matrix.className = "matrix";
  matrix.setAttribute("aria-hidden", "true");
  for (let row = 0; row < ROWS; row += 1) {
    for (let column = 0; column < COLS; column += 1) {
      const dot = document.createElement("i");
      dot.style.setProperty("--col", String(column));
      matrix.append(dot);
    }
  }
  return matrix;
}

function updateMatrix(matrix, gains) {
  const low = typeof gains.low === "number" ? gains.low : 0;
  const mid = typeof gains.mid === "number" ? gains.mid : 0;
  const high = typeof gains.high === "number" ? gains.high : 0;
  const levels = [];
  for (let column = 0; column < COLS; column += 1) {
    const position = column / (COLS - 1);
    const gain =
      position <= 0.5
        ? low + (mid - low) * (position / 0.5)
        : mid + (high - mid) * ((position - 0.5) / 0.5);
    levels.push(Math.round(((gain + 6) / 12) * (ROWS - 1)));
  }
  const dots = matrix.children;
  for (let row = 0; row < ROWS; row += 1) {
    const fromBottom = ROWS - 1 - row;
    for (let column = 0; column < COLS; column += 1) {
      const dot = dots[row * COLS + column];
      dot.classList.toggle("on", fromBottom === levels[column]);
      dot.classList.toggle("fill", fromBottom < levels[column]);
    }
  }
}

function renderTarget() {
  const live = liveUnits();
  const paired = live.some((unit) => unit.stereo && unit.stereo.mode === 1);
  if (paired) state.target = "all";
  const key = live.map((unit) => unit.mac).join("|");
  if (els.targetSeg.dataset.key !== key) {
    els.targetSeg.replaceChildren();
    if (live.length > 1) {
      els.targetSeg.append(targetButton("all", "Both"));
      live.forEach((unit, index) => {
        els.targetSeg.append(targetButton(unit.mac, `Unit ${index + 1}`, unit.mac));
      });
    }
    els.targetSeg.dataset.key = key;
  }
  if (state.target !== "all" && !live.some((unit) => unit.mac === state.target)) {
    state.target = "all";
  }
  els.targetSeg.hidden = live.length < 2 || paired;
  [...els.targetSeg.querySelectorAll("button")].forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.target === state.target));
  });
}

function targetButton(value, label, title) {
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.target = value;
  button.textContent = label;
  if (title) button.title = title;
  return button;
}

function renderControls(live) {
  const selected =
    state.target === "all" ? live : live.filter((unit) => unit.mac === state.target);
  const unitsSelected = selected.length || 1;

  const eqId = common(selected.map((unit) => (unit.eq ? unit.eq.id : null)));
  els.presets.forEach((button) => {
    const pressed =
      button.dataset.preset === "custom"
        ? eqId === 5
        : PRESET_IDS[button.dataset.preset] === eqId;
    button.setAttribute("aria-pressed", String(pressed));
  });
  els.eqState.textContent =
    eqId === null ? (unitsSelected > 1 ? "Units differ" : "—") : EQ_NAMES[eqId] || "—";

  let mixed = false;
  BANDS.forEach((band) => {
    const values = selected
      .map((unit) => (unit.custom ? unit.custom[band] : null))
      .filter((value) => typeof value === "number");
    if (new Set(values.map((value) => value.toFixed(2))).size > 1) mixed = true;
    const value = values.length ? values[0] : 0;
    const input = els.bandInputs[band];
    if (document.activeElement !== input) input.value = String(value);
    els.bandOut[band].textContent = fmtGain(Number(input.value));
  });

  const stereoPair =
    live.length > 1 && live.some((unit) => unit.stereo && unit.stereo.mode === 1);
  if (mixed) {
    els.targetNote.textContent = "Units differ; showing the first. Applying a value syncs them.";
  } else if (stereoPair) {
    els.targetNote.textContent =
      "Changes apply to the stereo pair and are read back from both units.";
  } else if (unitsSelected === 1) {
    els.targetNote.textContent =
      "Changes apply to this unit and are read back from the device.";
  } else {
    els.targetNote.textContent =
      "Changes apply to both units and are read back from the device.";
  }

  const bassLevel = common(
    selected.map((unit) => (unit.bass ? (unit.bass.on ? unit.bass.level : 0) : null)),
  );
  const shownBass =
    bassLevel === null
      ? selected.find((unit) => unit.bass)?.bass?.level || 0
      : bassLevel;
  els.bassLevels.forEach((button) => {
    button.setAttribute(
      "aria-pressed",
      String(bassLevel !== null && Number(button.dataset.level) === bassLevel),
    );
  });
  els.bassState.textContent =
    bassLevel === null
      ? unitsSelected > 1
        ? "Units differ"
        : "—"
      : shownBass
        ? `Level ${shownBass}`
        : "Off";

  const spatial = common(selected.map((unit) => unit.spatial));
  els.spatial.checked = spatial === true;
  els.spatial.indeterminate = spatial === null && selected.some((unit) => unit.spatial != null);
  els.spatialState.textContent =
    spatial === null ? (unitsSelected > 1 ? "Units differ" : "—") : spatial ? "On" : "Off";

  const nightOn = common(selected.map((unit) => (unit.night ? unit.night.on : null)));
  const nightMinutes = common(selected.map((unit) => (unit.night ? unit.night.minutes : null)));
  els.night.checked = nightOn === true;
  els.night.indeterminate = nightOn === null && selected.some((unit) => unit.night != null);
  els.nightMinutes.disabled = nightOn !== true;
  els.nightMinutes.title = nightOn === true ? "" : "Enable Night mode to set auto-off";
  setNightMinutes(nightMinutes);
  els.nightState.textContent =
    nightOn === null
      ? unitsSelected > 1
        ? "Units differ"
        : "—"
      : nightOn
        ? nightMinutes === null
          ? "On · mixed"
          : `On · ${formatMinutes(nightMinutes)}`
        : "Off";
}

function formatMinutes(minutes) {
  if (!minutes) return "no auto-off";
  return minutes >= 60 && minutes % 60 === 0 ? `${minutes / 60} h` : `${minutes} min`;
}

function setNightMinutes(minutes) {
  const select = els.nightMinutes;
  const mixed = select.querySelector('option[data-mixed="true"]');
  const extra = select.querySelector('option[data-extra="true"]');
  if (minutes === null) {
    if (!mixed) {
      const option = document.createElement("option");
      option.dataset.mixed = "true";
      option.value = "";
      option.textContent = "Mixed";
      select.prepend(option);
    }
    select.value = "";
    return;
  }
  if (mixed) mixed.remove();
  if (extra) extra.remove();
  const known = [...select.options].some((option) => Number(option.value) === minutes);
  if (!known) {
    const option = document.createElement("option");
    option.dataset.extra = "true";
    option.value = String(minutes);
    option.textContent = minutes ? `${minutes} min` : "Off";
    select.append(option);
  }
  select.value = String(minutes);
}

function renderStereo(live) {
  els.stereoBody.replaceChildren();
  const paired = live.find((unit) => unit.stereo && unit.stereo.mode === 1);
  const pairedPeer =
    live.find((unit) => unit.stereo && unit.stereo.mode === 1 && unit.stereo.peer) || paired;
  const master = live.find((unit) => unit.a2dp) || null;
  const slave = master ? live.find((unit) => unit.mac !== master.mac) || null : null;

  if (live.length < 2) {
    els.stereoState.textContent = "Two units needed";
    appendNote("Power on a second CMF Speaker S, then rescan. Stereo needs two identical units.");
    return;
  }

  if (paired) {
    els.stereoState.textContent = "Paired";
    const line = document.createElement("p");
    line.className = "stereo-line";
    line.append(
      document.createTextNode("Stereo with "),
      mono(pairedPeer.stereo.peer || "the other unit"),
      document.createTextNode(". Playback, volume and EQ sync across both units."),
    );
    const button = actionButton("Ungroup", "btn btn-quiet btn-danger", () => {
      handleConfirmClick(
        button,
        "Confirm ungroup",
        "Playback stops being linked; both units return to single mode. Click again to confirm.",
        () => runUngroup((master || pairedPeer).mac),
      );
    });
    els.stereoBody.append(line, button);
    return;
  }

  els.stereoState.textContent = master ? "Ready to pair" : "Audio not connected";
  if (!master) {
    appendNote(
      "Connect this laptop's audio to one unit first (Bluetooth settings), then rescan. The second unit must stay idle.",
    );
    els.stereoBody.append(
      actionButton("Rescan", "btn btn-quiet", () => load(true)),
    );
    return;
  }

  const line = document.createElement("p");
  line.className = "stereo-line";
  line.append(
    document.createTextNode("Master: "),
    mono(master.mac),
    document.createTextNode(" (A2DP). The second unit must be idle."),
  );
  const button = actionButton("Pair stereo", "btn btn-primary", () => {
    handleConfirmClick(
      button,
      "Confirm pair",
      "Audio routing will switch to the paired link. Click again to confirm.",
      () => runPair(master.mac, slave.mac),
    );
  });
  els.stereoBody.append(line, button);
}

function appendNote(text) {
  const note = document.createElement("p");
  note.className = "note";
  note.textContent = text;
  els.stereoBody.append(note);
}

function mono(text) {
  const span = document.createElement("span");
  span.className = "mono";
  span.textContent = text;
  return span;
}

function actionButton(label, className, handler) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.addEventListener("click", handler);
  return button;
}

function startConfirm(button, label, noteText, action) {
  const original = button.textContent;
  state.confirmAction = action;
  button.dataset.confirm = "true";
  button.textContent = label;
  const note = document.createElement("p");
  note.className = "note confirm-note";
  note.textContent = noteText;
  button.after(note);
  clearTimeout(state.confirmTimer);
  state.confirmTimer = setTimeout(() => {
    state.confirmAction = null;
    if (button.isConnected) {
      button.dataset.confirm = "false";
      button.textContent = original;
      note.remove();
    }
  }, 6000);
}

function handleConfirmClick(button, label, noteText, action) {
  if (state.confirmAction) {
    const run = state.confirmAction;
    cancelConfirm();
    run();
  } else {
    startConfirm(button, label, noteText, action);
  }
}

els.refresh.addEventListener("click", refreshState);
els.rescan.addEventListener("click", () => load(true));
els.bannerClose.addEventListener("click", () => setBanner(""));

els.targetSeg.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-target]");
  if (!button || state.busy) return;
  state.target = button.dataset.target;
  render();
});

els.presets.forEach((button) => {
  button.addEventListener("click", () => {
    if (state.busy) return;
    setSetting({ action: "eq", preset: button.dataset.preset });
  });
});

BANDS.forEach((band) => {
  const input = els.bandInputs[band];
  input.addEventListener("input", () => {
    els.bandOut[band].textContent = fmtGain(Number(input.value));
    clearTimeout(state.customTimer);
    state.customTimer = setTimeout(() => {
      if (state.busy) {
        state.customTimer = setTimeout(() => input.dispatchEvent(new Event("input")), 150);
        return;
      }
      const gains = Object.fromEntries(
        BANDS.map((name) => [name, Number(els.bandInputs[name].value)]),
      );
      setSetting({ action: "custom_eq", gains });
    }, 400);
  });
});

els.bassLevels.forEach((button) => {
  button.addEventListener("click", () => {
    if (state.busy) return;
    setSetting({ action: "bass", level: Number(button.dataset.level) });
  });
});

els.spatial.addEventListener("change", () => {
  setSetting({ action: "spatial", on: els.spatial.checked });
});

els.night.addEventListener("change", () => {
  setSetting({
    action: "night",
    on: els.night.checked,
    minutes: Number(els.nightMinutes.value),
  });
});

els.nightMinutes.addEventListener("change", () => {
  if (els.night.checked && els.nightMinutes.value) {
    setSetting({
      action: "night",
      on: true,
      minutes: Number(els.nightMinutes.value),
    });
  }
});

load();
