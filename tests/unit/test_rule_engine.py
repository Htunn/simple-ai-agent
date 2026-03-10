"""Unit tests for AIOps Rule Engine."""

import pytest
from src.aiops.rule_engine import Rule, RuleCondition, RuleEngine


# ── Rule.matches() ────────────────────────────────────────────────────────────

class TestRuleMatches:
    def _make_crash_event(self, namespace="default", severity="critical"):
        return {
            "event_type": "crash_loop",
            "severity": severity,
            "namespace": namespace,
            "resource_name": "my-pod",
        }

    def test_matching_event_returns_true(self):
        rule = Rule(
            id="r1", name="test", condition=RuleCondition.CRASH_LOOP,
            playbook_id="p1",
        )
        assert rule.matches(self._make_crash_event()) is True

    def test_wrong_event_type_returns_false(self):
        rule = Rule(
            id="r1", name="test", condition=RuleCondition.OOM_KILLED,
            playbook_id="p1",
        )
        assert rule.matches(self._make_crash_event()) is False

    def test_disabled_rule_never_matches(self):
        rule = Rule(
            id="r1", name="test", condition=RuleCondition.CRASH_LOOP,
            playbook_id="p1", enabled=False,
        )
        assert rule.matches(self._make_crash_event()) is False

    def test_namespace_filter_matching(self):
        rule = Rule(
            id="r1", name="test", condition=RuleCondition.CRASH_LOOP,
            playbook_id="p1", namespace_filter="^production$",
        )
        assert rule.matches(self._make_crash_event(namespace="production")) is True

    def test_namespace_filter_not_matching(self):
        rule = Rule(
            id="r1", name="test", condition=RuleCondition.CRASH_LOOP,
            playbook_id="p1", namespace_filter="^production$",
        )
        assert rule.matches(self._make_crash_event(namespace="staging")) is False

    def test_namespace_filter_regex(self):
        rule = Rule(
            id="r1", name="test", condition=RuleCondition.CRASH_LOOP,
            playbook_id="p1", namespace_filter="prod.*",
        )
        assert rule.matches(self._make_crash_event(namespace="production-blue")) is True
        assert rule.matches(self._make_crash_event(namespace="staging")) is False

    def test_severity_filter_matching(self):
        rule = Rule(
            id="r1", name="test", condition=RuleCondition.CRASH_LOOP,
            playbook_id="p1", severity_filter="critical",
        )
        assert rule.matches(self._make_crash_event(severity="critical")) is True

    def test_severity_filter_not_matching(self):
        rule = Rule(
            id="r1", name="test", condition=RuleCondition.CRASH_LOOP,
            playbook_id="p1", severity_filter="critical",
        )
        assert rule.matches(self._make_crash_event(severity="warning")) is False

    def test_no_severity_filter_matches_any_severity(self):
        rule = Rule(
            id="r1", name="test", condition=RuleCondition.CRASH_LOOP,
            playbook_id="p1",
        )
        assert rule.matches(self._make_crash_event(severity="warning")) is True
        assert rule.matches(self._make_crash_event(severity="info")) is True

    def test_empty_namespace_in_event_skips_filter(self):
        """If the event has no namespace, namespace_filter should not exclude it."""
        rule = Rule(
            id="r1", name="test", condition=RuleCondition.CRASH_LOOP,
            playbook_id="p1", namespace_filter="production",
        )
        event = {"event_type": "crash_loop", "severity": "critical"}
        assert rule.matches(event) is True

    def test_namespace_and_severity_both_must_match(self):
        rule = Rule(
            id="r1", name="test", condition=RuleCondition.CRASH_LOOP,
            playbook_id="p1",
            namespace_filter="production",
            severity_filter="critical",
        )
        assert rule.matches(self._make_crash_event(namespace="production", severity="critical")) is True
        assert rule.matches(self._make_crash_event(namespace="staging", severity="critical")) is False
        assert rule.matches(self._make_crash_event(namespace="production", severity="warning")) is False


# ── RuleEngine ────────────────────────────────────────────────────────────────

class TestRuleEngine:
    def test_default_rules_loaded_on_init(self):
        engine = RuleEngine()
        rules = engine.list_rules()
        assert len(rules) == len(RuleEngine.DEFAULT_RULES)

    def test_default_rule_ids_present(self):
        engine = RuleEngine()
        ids = {r.id for r in engine.list_rules()}
        assert "rule-001" in ids  # CrashLoop
        assert "rule-002" in ids  # OOMKill

    def test_add_rule(self):
        engine = RuleEngine()
        before = len(engine.list_rules())
        engine.add_rule(Rule(id="custom-1", name="Custom", condition=RuleCondition.CRASH_LOOP, playbook_id="pb"))
        assert len(engine.list_rules()) == before + 1

    def test_add_rule_overwrites_existing_id(self):
        engine = RuleEngine()
        engine.add_rule(Rule(id="rule-001", name="Overwritten", condition=RuleCondition.OOM_KILLED, playbook_id="new-pb"))
        overwritten = next(r for r in engine.list_rules() if r.id == "rule-001")
        assert overwritten.name == "Overwritten"
        assert len(engine.list_rules()) == len(RuleEngine.DEFAULT_RULES)

    def test_remove_rule_returns_true(self):
        engine = RuleEngine()
        result = engine.remove_rule("rule-001")
        assert result is True
        assert all(r.id != "rule-001" for r in engine.list_rules())

    def test_remove_nonexistent_rule_returns_false(self):
        engine = RuleEngine()
        result = engine.remove_rule("does-not-exist")
        assert result is False

    def test_evaluate_returns_matching_rules(self):
        engine = RuleEngine()
        event = {"event_type": "crash_loop", "severity": "critical", "namespace": "default", "resource_name": "web"}
        matches = engine.evaluate(event)
        assert len(matches) == 1
        rule, playbook_id = matches[0]
        assert playbook_id == "crash_loop_remediation"

    def test_evaluate_no_match_returns_empty(self):
        engine = RuleEngine()
        event = {"event_type": "unknown_event_type", "severity": "info"}
        matches = engine.evaluate(event)
        assert matches == []

    def test_evaluate_disabled_rule_not_returned(self):
        engine = RuleEngine()
        engine.add_rule(Rule(
            id="rule-disabled-test",
            name="Disabled Test Rule",
            condition=RuleCondition.CRASH_LOOP,
            playbook_id="disabled_pb",
            enabled=False,
        ))
        event = {"event_type": "crash_loop", "severity": "critical", "namespace": "default"}
        matches = engine.evaluate(event)
        assert all(r.id != "rule-disabled-test" for r, _ in matches)

    def test_evaluate_multiple_rules_can_match(self):
        engine = RuleEngine()
        # Add a second crash_loop rule without severity filter
        engine.add_rule(Rule(
            id="rule-extra",
            name="Extra CrashLoop",
            condition=RuleCondition.CRASH_LOOP,
            playbook_id="extra_playbook",
        ))
        event = {"event_type": "crash_loop", "severity": "critical", "namespace": "default"}
        matches = engine.evaluate(event)
        playbook_ids = [pb for _, pb in matches]
        assert "crash_loop_remediation" in playbook_ids
        assert "extra_playbook" in playbook_ids

    def test_evaluate_returns_correct_playbook_id(self):
        engine = RuleEngine()
        event = {"event_type": "oom_killed", "severity": "critical", "namespace": "default"}
        matches = engine.evaluate(event)
        assert len(matches) == 1
        assert matches[0][1] == "oom_kill_remediation"

    def test_rule_condition_enum_values(self):
        assert RuleCondition.CRASH_LOOP.value == "crash_loop"
        assert RuleCondition.OOM_KILLED.value == "oom_killed"
        assert RuleCondition.NOT_READY_NODE.value == "not_ready_node"
        assert RuleCondition.REPLICATION_FAILURE.value == "replication_failure"
