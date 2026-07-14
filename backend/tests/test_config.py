from app import config

# Mirrors the upstream observability platform's channel list. This is intentionally
# duplicated rather than fetched live (keeps tests fast and offline) — if the
# upstream platform adds a channel, this list AND config.CHANNEL_BASELINES both need
# updating, or this test will catch the same class of bug we shipped once already
# (new channels silently getting "No baseline available" for the LLM).
EXPECTED_CHANNELS = {
    "pos",
    "ecommerce",
    "mobile_wallet",
    "wire_online",
    "wire_branch",
    "wire_loaniq",
    "wire_batch",
    "wire_ivr",
    "ach_batch_file",
    "zelle_mobile",
    "zelle_online",
}


def test_every_known_channel_has_a_baseline():
    missing = EXPECTED_CHANNELS - set(config.CHANNEL_BASELINES.keys())
    assert not missing, f"Channels missing an LLM-grounding baseline: {missing}"


def test_no_stale_baselines_for_removed_channels():
    stale = set(config.CHANNEL_BASELINES.keys()) - EXPECTED_CHANNELS
    assert not stale, f"Baselines exist for channels that no longer exist: {stale}"
