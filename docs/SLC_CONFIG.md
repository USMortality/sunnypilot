# SLC JSON Configuration

Optional Speed Limit Control settings can be placed in:

```text
/data/sunnypilot/slc.json
```

The file is JSON, so it cannot contain comments. Restart openpilot after editing if you want the change applied immediately; the config reader also reloads when the file timestamp changes.

## Decision logging

Speed-limit decision logging is enabled by default. Set `"speedLimitDecisionLogging": false`
in the existing config to disable it; the logging switch reloads within five seconds.
This is independent of `tomtomDebugLogging`. It uses normal structured `logMessage`
events and the existing log rotation, without creating additional debug files or
changing speed-limit decisions.

- `slc_observation`: each map publication (normally 1 Hz), including GPS position,
  GPS/localizer validity, road name, TT/OSM provenance, current/upcoming limits,
  distance, cache provenance, confidence, road IDs when available, and up to 64
  speed sections with estimated boundary positions. TomTom fallback status and
  validation reasons are included. Credentials and raw API responses are excluded.
- `slc_decision`: the vehicle-reported and map candidates, message validity and
  age, source-selection policy, chosen source/limit, offset, current-only engagement
  handling, and upcoming-limit qualification/range decisions.
- `slc_application`: engagement auto-acceptance, confirmation or override reason,
  SLC state transitions, cruise setting, accepted SLC target, final planner target,
  and whether SLC actually controls that target. A lower cruise target can still
  win even after SLC accepts a higher limit.
- `slc_cruise_initialization`: configured initial speed, current vehicle speed,
  factory cruise ownership/readout, previous-speed resume, and the SLC target
  available when initializing cruise. This distinguishes a factory 30 km/h
  setting from an SLC-selected 30 km/h target.

Resolver and application events record changes at most twice per second, with a
five-second heartbeat for distance/speed context. Engagement auto-acceptance,
confirmation, and disengagement transitions are recorded immediately. Map-message monotonic timestamps link decisions to their
exact map observations. Application events include the latest resolver event's
timestamp and the current resolver frame, linking selection and application. Other
drive messages provide the raw vehicle, GPS, control, and camera context.
Map positions describe the reported location and estimated road boundaries, not
proof that a camera saw a physical sign. Invalid-message flags are recorded
separately from the existing resolver's selection, including an explicit warning
when an invalid map message is selected.

Export the events from downloaded **full rlogs** (qlogs generally omit `logMessage`):

```sh
python -m openpilot.sunnypilot.tools.slc_decisions /path/to/segment/rlog.zst --output slc-decisions.jsonl
```

Multiple local rlog files are accepted in chronological order. The command writes
JSONL records and prints event/auto-accept counts to stderr. Each record includes
its input filename and both the event's decision timestamp and the containing
drive-log timestamp, so it can be aligned with the rest of the drive offline.

## Engagement

`longitudinalE2EEnabled` controls whether model-predicted acceleration and stop requests participate in longitudinal planning. It defaults to `true`, matching staging behavior. Set it to `false` to use cruise, lead-following MPC, and SLC speed control without the model's experimental acceleration/stop candidate. This leaves Alpha longitudinal, steering/perception, SLC, and configured idle approaches enabled. Model-based traffic-light and stop-sign responses are disabled with this candidate. Existing lead braking and stop requests remain active. The setting reloads with the planner's configuration refresh and is recorded in SLC application events.

In assist mode, enabling longitudinal control automatically accepts a valid current speed limit,
including the configured speed offset, without a confirmation prompt. This also applies when
re-engaging after braking. Upcoming lookahead limits and retained limits without a valid current
reading are not automatically accepted on engagement. Later transitions keep their existing
confirmation behavior. This does not save any location data.

## Example

```json
{
  "speedLimitLowerLookaheadEnabled": true,
  "speedLimitLookaheadFactorDown": 4.0,
  "speedLimitLookaheadFactorUp": 1.0,
  "speedLimitLowerDecelControlEnabled": true,
  "speedLimitLowerDecelMode": "fixed",
  "speedLimitLowerDecelFixedAccel": -0.05,
  "speedLimitLowerDecelReleaseGapKph": 5.0,
  "speedLimitMaxDecelMps2": -0.5,
  "longitudinalNoLeadDecelMode": "idle",
  "longitudinalNoLeadIdleMinDecelMps2": -0.15,
  "longitudinalNoLeadIdleOverspeedMarginKph": 1.0,
  "longitudinalNoLeadIdleDecelCooldownS": 2.0
}
```

## Keys

`speedLimitLowerLookaheadEnabled`

Enables a separate approach target for upcoming lower speed limits. The enforced limit remains the current limit until the map reports the new zone. When lower-speed-limit decel control is enabled, lookahead can request the configured fixed/dynamic/idle approach before the boundary; it never accepts the upcoming limit early.

Allowed values: `true`, `false`

Default: `false`

`speedLimitLookaheadFactorDown`

Controls how far ahead lower speed limits are considered. The distance is based on speed and this factor. Example: a factor of `4.0` at `100 kph` is roughly `400 m`.

Allowed range: `0.0` to `10.0`

Default: `0.0`

`speedLimitLookaheadFactorUp`

Controls higher-limit anticipation and the upcoming higher-limit display range. A qualified upcoming higher map limit becomes the target within `upcoming limit (km/h) × factor` metres. This permits acceleration before the sign. Set `0.0` to wait for the current limit to change. Source policy still applies, and engagement initially uses the current zone.

Allowed range: `0.0` to `10.0`

Default: `0.0`

`speedLimitLowerDecelControlEnabled`

Enables the special lower-speed-limit decel behavior when lower map lookahead is active. Fixed/dynamic modes require no lead; idle mode also permits a steady, sufficiently distant lead (see below).

Allowed values: `true`, `false`

Default: `false`

`speedLimitLowerDecelMode`

Selects how SLC approaches a lower upcoming speed limit when `speedLimitLowerDecelControlEnabled` is active.

If `longitudinalNoLeadDecelMode` is set to `"idle"`, ordinary no-lead cruise decel will use idle instead of these fixed/dynamic accel requests. In that setup, this key mostly matters only for the dedicated lower-speed-limit lookahead path.

Allowed values:

- `"fixed"`: request the configured `speedLimitLowerDecelFixedAccel` until the release gap is reached.
- `"dynamic"`: calculate decel from current speed, target speed, and remaining distance.
- `"idle"`: request output-layer idle instead of negative accel while above the release gap. Currently implemented for Hyundai CAN-FD SCC output.

Default: `"fixed"`

`speedLimitLowerDecelFixedAccel`

Acceleration request used by `"fixed"` mode. Negative values slow the car. Values closer to `0.0` are gentler.

Allowed range: `-1.2` to `0.0` m/s^2

Default: `-0.05`

`speedLimitLowerDecelReleaseGapKph`

Stops the lower-limit decel override once ego speed is within this margin above the adjusted speed-limit target. Example: with a `50 kph` target and `5.0`, the override releases at `55 kph`. This is a one-time coast release for that target: normal speed control resumes with a temporary ceiling at the approach target plus release gap until the boundary. This prevents accelerating back to the old limit; small speed increases do not re-enter the coast override. Explicit driver cancellation clears the temporary ceiling. The release margin does not change the final cruise target. With a posted `50 kph` limit and a `+1 kph` speed-limit offset, the adjusted target is `51 kph`, so a `5 kph` release margin releases at `56 kph`.

Allowed range: `0.0` to `30.0` kph

Default: `5.0`

`speedLimitMaxDecelMps2`

Caps normal no-lead SLC decel. This does not cap the special lower-limit decel modes while they are active.

Allowed range: `-2.0` to `0.0` m/s^2

Default: `-0.5`

`longitudinalNoLeadDecelMode`

Controls intentional cruise-source decel, outside emergency, lead-braking, and stop cases. Despite its legacy name, idle mode also permits a qualified steady lead under the rules below. It does not idle for small speed-hold corrections.

This is the broader gas-car test mode. If `"idle"` behaves well, it can replace most fixed/dynamic decel tuning for no-lead slowdowns.
Pressing accel/resume or increasing the cruise target clears idle and blocks it briefly so the controller sends an active non-idle output again. Lowering the set speed while temporarily overriding with the accelerator preserves that slowdown target until control resumes; idle is always blocked while a pedal is pressed, and full disengagement clears the target.
If SLC is enforcing the current adjusted speed limit and the car is more than `longitudinalNoLeadIdleOverspeedMarginKph` above it, idle is blocked so normal decel/braking can control downhill overspeed. After this happens, idle stays blocked for `longitudinalNoLeadIdleDecelCooldownS` seconds to avoid rapid idle/brake toggling near the limit.

Allowed values:

- `"normal"`: keep normal planner/controller acceleration requests, including negative decel.
- `"idle"`: when SLC lowers the target or the driver manually lowers the cruise set speed, request output-layer idle instead of negative accel. Currently implemented for Hyundai CAN-FD SCC output.

Default: `"normal"`

`longitudinalNoLeadIdleMinDecelMps2`

Minimum requested decel needed before `longitudinalNoLeadDecelMode: "idle"` activates. Small negative accel requests stay in normal control; stronger intentional no-lead decel requests use idle.

Example: with `-0.15`, a request of `-0.05` stays normal, while a request of `-0.20` uses idle.

Allowed range: `-1.2` to `0.0` m/s^2

Default: `-0.15`

`longitudinalNoLeadIdleOverspeedMarginKph`

Extra speed above the adjusted current speed limit before idle is blocked and normal decel/braking is used. This avoids switching out of idle for tiny speed noise around the target.

Allowed range: `0.0` to `10.0` kph

Default: `1.0`

`longitudinalNoLeadIdleDecelCooldownS`

How long idle stays blocked after current-limit overspeed decel is needed. Higher values reduce idle/brake flicker near the limit.

Allowed range: `0.0` to `10.0` seconds

Default: `2.0`

## Legacy Keys

The old keys are still accepted as fallbacks:

- `lookaheadLowerLimits` -> `speedLimitLowerLookaheadEnabled`
- `lookaheadSpeedFactorDown` -> `speedLimitLookaheadFactorDown`
- `lookaheadSpeedFactorUp` -> `speedLimitLookaheadFactorUp`
- `lookaheadSpeedFactor` -> fallback for both lookahead factors
- `noBrakeForSpeedLimit` -> `speedLimitLowerDecelControlEnabled`
- `noBrakeMode` -> `speedLimitLowerDecelMode`
- `noBrakeAccel` -> `speedLimitLowerDecelFixedAccel`
- `noBrakeReleaseGapKph` -> `speedLimitLowerDecelReleaseGapKph`
- `speedLimitMaxDecel` -> `speedLimitMaxDecelMps2`

Prefer the explicit keys for new configs.

## Idle with a lead and recovery

Both the dedicated lower-limit `"idle"` approach and manual set-speed reductions with `longitudinalNoLeadDecelMode: "idle"` can coast with a lead after two seconds of stable readings. Both detected leads must satisfy all of these initial conservative thresholds:

- Distance at least `95%` of the personality follow distance (`T_FOLLOW × v_ego`, minimum `6 m`), so a lead at normal following distance qualifies.
- Relative speed at least `-0.2 m/s` (no appreciable closing).
- Lead acceleration at least `-0.2 m/s²` (no appreciable slowing).
- No abrupt distance drop of more than `0.5 m` between planner updates.

Every new lead appearance restarts the two-second qualification period. A lead that simply departs does not restart it. Before entry, hard lead-planner braking (`≤ -0.4 m/s²`) blocks idle immediately, while a smaller request (`< -0.15 m/s²`) must persist for about `0.2 s`. Brief unsafe entry readings block idle immediately but only restart qualification after `0.25 s`.

When N starts, save each present lead's time gap (`dRel / vEgo`). Keep those baselines fixed throughout the coasting episode, even if the gap opens or ego slows. Normal control resumes when either lead's time gap falls to `90%` of its saved value or less: an entry gap of `2.5 s` releases at `2.25 s`. A minimum physical gap of `6 m` remains enforced. Measured deceleration (including coasting or hybrid regeneration), relative speed, lead acceleration, and ordinary MPC gap corrections do not independently cancel an active N request. The red acceleration bar displays measured acceleration, so it may remain red while N is active.

A new lead, invalid lead data, stale inputs, stop requests, FCW, forced deceleration, pedal input, and experimental control still block idle. A breached gap requires fresh qualification before another episode. The planner publishes its saved entry gaps through controls to CAN output, so both layers use exactly the same baselines. CAN independently rechecks both raw leads against those baselines; a rejection remains blocked until the planner's idle request clears. Missing or malformed baselines cannot enable idle at CAN output.

The existing speed-limit release behavior is retained: the lookahead approach releases at the target speed plus the configured release gap, and a current-limit drop that requires deceleration blocks idle. Manual cruise reductions also release at their target plus the configured gap. For example, reducing cruise from `40` to `20 kph` can coast until `22 kph` with a `2 kph` release gap, then normal control finishes the slowdown.

Accel/resume cancels the current lower-limit approach until a new approach/target. The controller continues updating its engagement state during idle, and stale plans cannot keep commanding idle. These checks address software paths that can suppress acceleration; actual Hyundai SCC recovery after `ACCMode=0` still needs validation on supported hardware using recorded CAN/control data.

## Rapid limit changes and car-first selection

Car-first prefers the car's current limit. Higher map anticipation follows source policy and cannot override an available car limit in car-first mode.

Upcoming map limits are tracked before they enter the configured lookahead range. A candidate qualifies after fresh map messages span at least 1.5 seconds with the same limit and a consistent approaching boundary. Distance is checked against estimated travel between observations (15 m tolerance); a changed limit, missing candidate, stale map, or observation gap over 2.5 seconds restarts qualification. Before qualification, a distance jump restarts the candidate. After qualification, one plausible forward distance outlier (up to 30 m from estimated travel) is tolerated to prevent higher-limit anticipation from flickering; a second inconsistent observation restarts qualification. Re-reading the same message cannot qualify it. Qualification gates lower-limit approaches and higher-limit anticipation independently of current-limit observations.

Once qualified and inside the configured lower lookahead range, the upcoming limit supplies a separate approach target and distance. It does not replace the enforced current limit or trigger early acceptance. There is no braking-distance or imminent-boundary bypass of qualification. Missing, stale, changed, or passed upcoming boundaries clear the approach. Lower enforced limits change when the selected source reports a new current limit, subject to GPS/map accuracy and publication timing. Higher limits can apply early within the configured up lookahead range after boundary qualification. For lower limits, an estimated upcoming distance reaching zero alone does not change the enforced limit.

The approach uses its own offset-adjusted target for coast release. Idle/N can operate when cruise ties the current SLC limit, but cannot override inactive SLC, a lower cruise target, SCC control, current-limit overspeed deceleration, or the existing lead/pedal/safety gates. Higher lookahead permits early acceleration after qualification when its factor is greater than zero.

An approach first detected below its target plus release gap waits until deceleration is needed; it is not considered completed merely because the car was already slow. Once armed above that threshold, reaching the release gap releases coast once and holds the release speed until the current-limit transition. Driver cancellation also prevents arming, and a released approach cannot re-arm from speed noise until a new approach begins.

The feed currently exposes only one upcoming limit and its distance, without a road or boundary ID. Distance progression is an approximation of boundary identity, and fresh publications can still contain cached upstream map data. This does not validate OSM correctness or retain a confirmed entry after it disappears. TomTom separately suppresses higher-limit islands of at most 75 m bounded by the same lower limit within the validated route. Multiple upcoming segments, explicit boundary IDs, and upstream observation timestamps would allow stronger validation later.
