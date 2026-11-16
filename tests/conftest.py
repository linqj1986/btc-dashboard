import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def ref():
    """黄金数据集: 原站内嵌 dates/prices/totals/cycleBots/TRIG"""
    with open(ROOT / "reference_data.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def orig_html():
    """黄金页面: 原站抓取的完整 HTML"""
    with open(ROOT / "tests" / "fixtures" / "original.html", encoding="utf-8") as f:
        return f.read()
