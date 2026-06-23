from __future__ import annotations

from pathlib import Path

import yaml

from aegis_redteam.campaigns.models import Campaign


def load_campaign(path: Path | str) -> Campaign:
    campaign_path = Path(path)
    data = yaml.safe_load(campaign_path.read_text(encoding="utf-8"))
    return Campaign.model_validate(data)
