from __future__ import annotations

from pathlib import Path

from aegis_redteam.campaigns.models import Campaign
from aegis_redteam.yaml_utils import load_yaml_model


def load_campaign(path: Path | str) -> Campaign:
    return load_yaml_model(path, Campaign, "campaign")
