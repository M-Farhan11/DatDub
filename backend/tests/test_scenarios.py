"""F7: scenario injection, ground truth and precise expected-violation attribution."""

import pytest
from fastapi.testclient import TestClient

from app.engine import generator
from app.engine.scenarios import inject
from app.main import app
from app.schemas import ScenarioProposal, ScenarioSelection
from app.templates import ecommerce, finance
from app.validation.checks import build_report

client = TestClient(app)


def _sel(sid, kind, table, column=None, rule_id=None, count=5) -> ScenarioSelection:
    return ScenarioSelection(
        proposal=ScenarioProposal(id=sid, kind=kind, table=table, column=column, rule_id=rule_id, title=sid),
        count=count,
    )


def _run(schema, selections, n=300, seed=3):
    root = generator.topological_order(schema)[0].name
    tables = generator.generate(schema, {root: n}, seed=seed)
    truth, expected = inject(schema, tables, selections, seed)
    return tables, truth, build_report(schema, tables, truth, expected)


def _check(report, table, name_start):
    return next(c for c in report.checks if c.table == table and c.name.startswith(name_start))


def test_three_selected_scenarios_give_exactly_those_records_and_pass_as_expected():
    """TASKS F7 acceptance, through the API."""
    body = {
        "schema": finance.build().model_dump(by_alias=True),
        "rows": {"customers": 300},
        "seed": 11,
        "scenarios": [
            _sel("s1", "rule_violation", "payments", rule_id="r3", count=4).model_dump(),
            _sel("s2", "null_burst", "customers", column="email", count=6).model_dump(),
            _sel("s3", "duplicate_record", "payments", count=3).model_dump(),
        ],
    }
    r = client.post("/api/generate", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    truth = {g["scenario_id"]: g for g in data["ground_truth"]}
    assert list(truth) == ["s1", "s2", "s3"]
    assert [len(truth[s]["affected_ids"]) for s in ("s1", "s2", "s3")] == [4, 6, 3]
    # the three scenarios touch distinct rows
    pay_ids = truth["s1"]["affected_ids"] + truth["s3"]["affected_ids"]
    assert len(set(pay_ids)) == len(pay_ids)

    report = data["report"]
    assert report["overall"] == "PASS", [c for c in report["checks"] if c["status"] == "FAIL"]
    by_name = {(c["table"], c["name"].split(":")[0]): c for c in report["checks"]}
    assert by_name[("payments", "Rule r3")]["expected_violations"] == 4
    assert by_name[("customers", "Types & nullability")]["expected_violations"] == 6
    page = client.get(f"/api/datasets/{data['dataset_id']}/tables/payments", params={"limit": 1}).json()
    assert page["total"] == data["row_counts"]["payments"]  # duplicates are stored with the dataset


@pytest.mark.parametrize("build", [finance.build, ecommerce.build])
def test_every_mock_proposal_injects_cleanly(build):
    schema = build()
    proposals = client.post("/api/scenarios/propose", json={"schema": schema.model_dump(by_alias=True)}).json()["proposals"]
    assert {p["kind"] for p in proposals} == {"rule_violation", "null_burst", "extreme_value", "boundary_date", "duplicate_record"}
    selections = [ScenarioSelection(proposal=ScenarioProposal(**p), count=p["suggested_count"]) for p in proposals]
    _, truth, report = _run(schema, selections)
    assert len(truth) == len(proposals) and all(g.affected_ids for g in truth)
    assert report.overall == "PASS", [c for c in report.checks if c.status == "FAIL"]
    assert sum(c.expected_violations for c in report.checks) > 0


def test_each_rule_kind_can_be_violated_and_is_attributed():
    schema = finance.build()
    for rule in schema.rules:
        _, truth, report = _run(schema, [_sel("s1", "rule_violation", rule.table, rule_id=rule.id, count=5)])
        c = _check(report, rule.table, f"Rule {rule.id}:")
        assert c.expected_violations == 5, (rule.id, c)
        assert report.overall == "PASS", (rule.id, [x for x in report.checks if x.status == "FAIL"])


def test_changed_line_items_are_expected_on_the_parent_invoice():
    schema = finance.build()
    _, _, report = _run(schema, [_sel("s1", "extreme_value", "invoice_items", column="unit_price", count=5)])
    assert _check(report, "invoices", "Rule r1:").expected_violations >= 1
    assert report.overall == "PASS"

    _, _, report = _run(schema, [_sel("s1", "duplicate_record", "invoice_items", count=5)])
    assert _check(report, "invoices", "Rule r1:").expected_violations >= 1
    assert report.overall == "PASS"


def test_duplicates_get_new_keys_and_only_unique_columns_clash():
    schema = finance.build()
    tables, truth, report = _run(schema, [_sel("s1", "duplicate_record", "customers", count=4)])
    ids = truth[0].affected_ids
    cust = tables["customers"]
    assert len(cust) == 304 and cust["customer_id"].is_unique
    assert set(ids) <= set(cust["customer_id"])
    assert _check(report, "customers", "PK uniqueness").expected_violations == 0
    assert _check(report, "customers", "Unique (email)").expected_violations == 8  # copies + originals
    assert report.overall == "PASS"


def test_unrelated_corruption_on_an_injected_row_still_fails():
    schema = finance.build()
    tables, truth, _ = _run(schema, [_sel("s1", "rule_violation", "payments", rule_id="r3", count=3)])
    pay = tables["payments"]
    victim = pay.index[pay["payment_id"] == truth[0].affected_ids[0]][0]
    pay["method"] = pay["method"].astype(object)
    pay.loc[victim, "method"] = None
    report = build_report(schema, tables, truth, {("payments", "rule:r3"): set(truth[0].affected_ids)})
    assert _check(report, "payments", "Types & nullability").status == "FAIL"


def test_injection_is_deterministic():
    schema = finance.build()
    sels = [_sel("s1", "boundary_date", "invoices", column="due_date"), _sel("s2", "null_burst", "customers", column="phone")]
    a, ta, _ = _run(schema, sels, seed=4)
    b, tb, _ = _run(schema, sels, seed=4)
    assert [g.affected_ids for g in ta] == [g.affected_ids for g in tb]
    assert a["invoices"].equals(b["invoices"])


def test_boundary_dates_are_real_boundaries():
    schema = finance.build()
    tables, truth, report = _run(schema, [_sel("s1", "boundary_date", "invoices", column="due_date", count=12)])
    inv = tables["invoices"].set_index("invoice_id").loc[truth[0].affected_ids, "due_date"]
    ok = (inv.dt.is_month_end | inv.dt.is_year_start | (inv.dt.year <= 1900) | (inv.dt.year >= 2099)
          | ((inv.dt.month == 2) & (inv.dt.day == 29)))
    assert ok.all()
    assert report.overall == "PASS"


def test_invalid_scenarios_are_rejected_at_generate():
    schema = finance.build().model_dump(by_alias=True)
    for sel in (
        _sel("s1", "null_burst", "customers", column="customer_id"),  # key
        _sel("s1", "extreme_value", "customers", column="email"),  # not numeric
        _sel("s1", "rule_violation", "payments", rule_id="r99"),
        _sel("s1", "boundary_date", "ghosts", column="x"),
    ):
        r = client.post("/api/generate", json={"schema": schema, "rows": {"customers": 10}, "scenarios": [sel.model_dump()]})
        assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_schema", r.text
