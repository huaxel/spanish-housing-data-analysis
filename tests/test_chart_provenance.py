"""Provenance is derived from live queries and pinned inputs, not copied claims."""

import csv
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import export_chart_provenance as ep  # noqa: E402

PANEL = """<EvidencePanel data={q} chart="demo-chart"
 columns={["code", "value"]} files={["data/raw/input.json"]}
 definition="Definition" coverage="Coverage" />"""
PAGE = "```sql q\nselect 1\n```\n" + PANEL


def fixture_manifest():
    return {
        "snapshot_date": "2026-10-10",
        "sha256": {"data/raw/input.json": "a" * 64},
        "sources": {
            "data/raw/input.json": {
                "publisher": "Official publisher",
                "accessed": "2026-10-08",
                "url": "https://example.org/input.json",
            }
        },
    }


def panels(text=PAGE):
    return ep.declarations({"evidence/pages/demo.md": text})


def test_metadata_selects_only_referenced_pins_and_preserves_actual_access_date():
    manifest = fixture_manifest()
    manifest["sha256"]["data/raw/unrelated.json"] = "b" * 64
    data = ep.metadata(manifest, panels())
    assert set(data["sources"]) == {"data/raw/input.json"}
    assert data["sources"]["data/raw/input.json"]["accessed"] == "2026-10-08"
    assert data["snapshot_date"] == "2026-10-10"  # not the observation year or input date
    assert "rows" not in data and "claims" not in data


@pytest.mark.parametrize(
    "old,new",
    [
        ("data={q}", "data={unknown}"),
        ('definition="Definition"', ""),
        ('coverage="Coverage"', ""),
        ('["code", "value"]', '["code", "code"]'),
        ('["data/raw/input.json"]', '["../private.json"]'),
        ('["data/raw/input.json"]', '["data/raw/../private.json"]'),
        ('chart="demo-chart"', 'chart="other-chart"'),
    ],
)
def test_invalid_or_unbound_panel_declarations_fail(old, new):
    with pytest.raises(ValueError):
        panels(PAGE.replace(old, new))


def test_duplicate_chart_ids_fail():
    with pytest.raises(ValueError, match="Duplicate"):
        panels(PAGE + PANEL)


def test_missing_or_malformed_pin_and_unsafe_source_urls_fail():
    manifest = fixture_manifest()
    manifest["sha256"].clear()
    with pytest.raises(ValueError, match="pin"):
        ep.metadata(manifest, panels())
    manifest = fixture_manifest()
    manifest["sources"]["data/raw/input.json"]["url"] = "javascript:alert(1)"
    with pytest.raises(ValueError, match="HTTPS"):
        ep.metadata(manifest, panels())


def test_missing_access_date_is_not_invented_and_ine_api_is_linked():
    manifest = fixture_manifest()
    manifest["sources"]["data/raw/input.json"] = {
        "operation": "ECP",
        "api": "wstempus/DATOS_TABLA/60131",
    }
    source = ep.metadata(manifest, panels())["sources"]["data/raw/input.json"]
    assert source["accessed"] is None
    assert source["publisher"] == "INE · ECP"
    assert source["url"] == "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/60131"


def test_generated_metadata_is_exact_and_check_is_readonly(tmp_path, monkeypatch):
    page = tmp_path / "evidence/pages/demo.md"
    page.parent.mkdir(parents=True)
    page.write_text(PAGE)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(fixture_manifest()))
    output = tmp_path / "generated.json"
    monkeypatch.setattr(ep, "ROOT", tmp_path)
    monkeypatch.setattr(ep, "PAGES", page.parent)
    monkeypatch.setattr(ep, "MANIFEST", manifest)
    monkeypatch.setattr(ep, "OUTPUT", output)
    monkeypatch.setattr(sys, "argv", ["export_chart_provenance.py"])
    ep.main()
    before = output.read_bytes()
    monkeypatch.setattr(sys, "argv", ["export_chart_provenance.py", "--check"])
    ep.main()
    assert output.read_bytes() == before
    changed = fixture_manifest()
    changed["sha256"]["data/raw/input.json"] = "b" * 64
    manifest.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="stale"):
        ep.main()


def test_every_key_chart_has_an_adjacent_panel_bound_to_its_actual_query():
    counts = []
    for route in ("reportaje", "perfil", "deficit", "comparar-municipios"):
        text = (ROOT / f"evidence/pages/{route}.md").read_text()
        charts = re.findall(r"<(?:LineChart|BarChart|AreaMap)\b.*?/>", text, re.S)
        paired = re.findall(
            r"<(?:LineChart|BarChart|AreaMap)\b.*?/>\s*(<EvidencePanel\b.*?/>)",
            text,
            re.S,
        )
        assert len(charts) == len(paired)
        for chart, panel in zip(charts, paired, strict=True):
            assert re.search(r"data=\{(\w+)\}", chart)[1] == re.search(r"data=\{(\w+)\}", panel)[1]
        counts.append(len(charts))
    assert counts == [9, 3, 2, 1]
    assert ep.OUTPUT.read_text() == ep.generate()


def run_js(body):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node unavailable; export helpers are also exercised by the browser smoke")
    module = (ROOT / "evidence/components/evidence-data.js").as_uri()
    result = subprocess.run(
        [
            node,
            "--input-type=module",
            "-e",
            f"import {{selectRows,asCsv}} from '{module}';\n" + body,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_downloads_keep_null_zero_codes_precision_and_escape_csv():
    result = run_js("""
      const rows=selectRows([
        {code:'01001',value:null,name:'A, "B"\\nC',ignored:99},
        {code:'05002',value:0,name:'=1+1',ignored:99},
        {code:'28079',value:-1.23456789,name:'Normal',ignored:99}
      ],['code','value','name']);
      console.log(JSON.stringify({rows,csv:asCsv(rows,['code','value','name'])}));
    """)
    assert result["rows"][0] == {"code": "01001", "value": None, "name": 'A, "B"\nC'}
    assert result["rows"][1]["value"] == 0
    assert result["rows"][2]["value"] == -1.23456789
    parsed = list(csv.reader(io.StringIO(result["csv"].lstrip("\ufeff"))))
    assert parsed[0] == ["code", "value", "name"]
    assert parsed[1] == ["01001", "", 'A, "B"\nC']
    assert parsed[2] == ["05002", "0", "'=1+1"]
    assert parsed[3][1] == "-1.23456789"


def test_downloads_reject_unknown_columns_duplicates_and_nonfinite_values():
    assert run_js("""
      const failed=[];
      const cases=[[[{x:1}],['unknown']],[[{x:1}],['x','x']],[[{x:Infinity}],['x']]];
      for (const [rows,columns] of cases) {
        try {selectRows(rows,columns);failed.push(false);} catch {failed.push(true);}
      }
      console.log(JSON.stringify(failed));
    """) == [True, True, True]


def test_regional_population_panel_pins_direct_ccaa_and_national_padron_inputs():
    page = (ROOT / "evidence/pages/reportaje.md").read_text()
    panel = next(
        p for p in panels_for_reportaje(page) if p["chart"] == "reportaje-stock-territorios"
    )
    assert {
        "data/raw/padron_ccaa.json",
        "data/raw/padron_provincia.json",
        "data/raw/ecp_pob_ccaa.json",
    } <= set(panel["files"])


def panels_for_reportaje(text):
    return ep.declarations({"evidence/pages/reportaje.md": text})
