# Pool RGB LED — Home Assistant integration

Drive a pool RGB LED that switches modes when power is briefly cut, by
proxying a target relay/light/input_boolean entity in Home Assistant.

The lamp has 11 colors and 7 sequences, advanced by short (<1 s) power
cuts. Two cuts in a row resync the controller and land it on **Blue**
(color 2, the device's "start" position — index 1).

## Install via HACS

1. HACS → Integrations → ⋮ → Custom repositories
2. Add this repo's URL, category **Integration**
3. Install **Pool RGB LED**, restart Home Assistant
4. Settings → Devices & Services → Add Integration → **Pool RGB LED**
5. Configure **either**:
   - a target entity (`light.*`, `switch.*`, or `input_boolean.*`)
     that controls power to the pool LED, **or**
   - a **KNX group address** (e.g. `1/2/3`) — the integration calls
     `knx.send` directly, skipping the entity layer. Recommended on
     KNX setups: less latency jitter, more consistent pulse timing.

   You can fill both — KNX takes precedence when set.

## KNX vs entity-based driving

The lamp's <1 s power-cut window is tight, and Home Assistant's
service-call → entity → integration path adds 15–40 ms of variable
latency per edge. Pointing the integration straight at a 1-bit KNX GA
removes that hop and the entity-state writeback. The mechanical relay is
still the dominant variable, but timing becomes more deterministic.

## Tuning the timings

Three options control the pulse pump (ms):

| Option       | Default | Meaning                                     |
| ------------ | ------- | ------------------------------------------- |
| `pulse_ms`   | 400     | How long power stays off during a cut       |
| `gap_ms`     | 400     | Wait between consecutive cuts in a burst    |
| `settle_ms`  | 1500    | Wait after a burst before another command   |

The hardware specifies that a power cut shorter than 1 second advances
the mode; defaults sit comfortably under that. If your relay is slow,
raise `pulse_ms`. If your lamp misses pulses in a long burst (e.g.
stepping 10 modes forward), raise `gap_ms`.

## Provided services

- `pool_rgb_led.next` — one short pulse, advance one mode
- `pool_rgb_led.set_mode` — step forward until the named mode is active
- `pool_rgb_led.resync` — double-pulse, lands on **Blue**

The integration also creates a `light` entity that exposes all 18 modes
as `effect`s; you can use the standard `light.turn_on` /
`light.turn_off` services with `effect:` set.

## Caveats

- Tracked position is a guess. If you cut power outside Home Assistant,
  call `resync` to re-sync.
- HA service-call latency means the strict <1 s cut window can be tight.
  If a cut runs long, the device sees it as a power-off rather than a
  mode change. Tune `pulse_ms` for your relay.
