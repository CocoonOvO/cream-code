from __future__ import annotations

import pytest
from datetime import datetime
from creamcode.cost import (
    CostTracker,
    CostRecord,
    BudgetExceededError,
    DefaultPricingModel,
)


class TestDefaultPricingModel:
    def test_get_price_known_model_input(self):
        pricing = DefaultPricingModel()
        cost = pricing.get_price("claude-3-5-sonnet", 1_000_000, is_output=False)
        assert cost == 3.0

    def test_get_price_known_model_output(self):
        pricing = DefaultPricingModel()
        cost = pricing.get_price("claude-3-5-sonnet", 1_000_000, is_output=True)
        assert cost == 15.0

    def test_get_price_unknown_model(self):
        pricing = DefaultPricingModel()
        cost = pricing.get_price("unknown-model", 1_000_000, is_output=False)
        assert cost == 1.0

    def test_get_price_partial_tokens(self):
        pricing = DefaultPricingModel()
        cost = pricing.get_price("gpt-4o-mini", 100_000, is_output=False)
        assert cost == 0.015


class TestCostRecord:
    def test_cost_record_creation(self):
        record = CostRecord(
            timestamp=datetime.now(),
            model="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            cost=0.003,
        )
        assert record.model == "gpt-4o"
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.cost == 0.003


class TestCostTracker:
    def test_record_and_get_total_cost(self):
        tracker = CostTracker()
        tracker.record("claude-3-5-sonnet", 1_000_000, 500_000)
        assert tracker.get_total_cost() == 10.5

    def test_record_with_session(self):
        tracker = CostTracker()
        tracker.record("gpt-4o", 100_000, 50_000, session_id="session-1")
        assert tracker.get_session_cost("session-1") > 0

    def test_get_usage_summary(self):
        tracker = CostTracker()
        tracker.record("claude-3-5-sonnet", 1_000_000, 500_000)
        summary = tracker.get_usage_summary()
        assert summary["total_input_tokens"] == 1_000_000
        assert summary["total_output_tokens"] == 500_000
        assert summary["record_count"] == 1

    def test_check_budget_no_exceed(self):
        tracker = CostTracker(monthly_budget=100.0)
        allowed, _ = tracker.check_budget()
        assert allowed is True

    def test_check_budget_exceed_monthly(self):
        tracker = CostTracker(monthly_budget=0.001)
        tracker.record("claude-3-5-sonnet", 1_000_000, 500_000)
        allowed, reason = tracker.check_budget()
        assert allowed is False
        assert "Monthly budget exceeded" in reason

    def test_check_budget_exceed_session(self):
        tracker = CostTracker(session_budget=0.001)
        tracker.record("claude-3-5-sonnet", 1_000_000, 500_000, session_id="session-1")
        allowed, reason = tracker.check_budget()
        assert allowed is False
        assert "Session budget exceeded" in reason

    def test_reset_session(self):
        tracker = CostTracker(session_budget=10.0)
        tracker.record("claude-3-5-sonnet", 1_000_000, 500_000, session_id="session-1")
        tracker.reset_session()
        assert tracker.get_session_cost("session-1") > 0

    def test_reset_monthly(self):
        tracker = CostTracker(monthly_budget=100.0)
        tracker.record("claude-3-5-sonnet", 1_000_000, 500_000)
        tracker.reset_monthly()
        assert tracker.get_total_cost() == 0.0
        assert len(tracker._records) == 0


class TestBudgetExceededError:
    def test_budget_exceeded_error(self):
        error = BudgetExceededError("Budget exceeded")
        assert str(error) == "Budget exceeded"
