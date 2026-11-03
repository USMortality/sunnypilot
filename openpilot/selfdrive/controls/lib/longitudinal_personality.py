from openpilot.cereal import log


LONGITUDINAL_PERSONALITY_ORDER = (
  int(log.LongitudinalPersonality.aggressive),
  int(log.LongitudinalPersonality.moderate),
  int(log.LongitudinalPersonality.standard),
  int(log.LongitudinalPersonality.relaxed),
)
LONGITUDINAL_PERSONALITY_TO_BUTTON = {value: index for index, value in enumerate(LONGITUDINAL_PERSONALITY_ORDER)}


def personality_to_gap_bars(personality):
  raw = personality.raw if hasattr(personality, 'raw') else int(personality)
  return LONGITUDINAL_PERSONALITY_TO_BUTTON[raw] + 1


def next_personality(personality):
  raw = personality.raw if hasattr(personality, 'raw') else int(personality)
  index = LONGITUDINAL_PERSONALITY_TO_BUTTON.get(raw, 0)
  return LONGITUDINAL_PERSONALITY_ORDER[(index + 1) % len(LONGITUDINAL_PERSONALITY_ORDER)]
