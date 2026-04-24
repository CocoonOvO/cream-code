from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


class PricingModel(Protocol):
    """定价模型协议"""
    def get_price(self, model: str, tokens: int, is_output: bool) -> float: ...


class DefaultPricingModel:
    """默认定价模型（美元/百万tokens）"""
    PRICES = {
        "claude-3-5-sonnet": {"input": 3, "output": 15},
        "claude-3-5-haiku": {"input": 0.8, "output": 4},
        "gpt-4o": {"input": 2.5, "output": 10},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
        "default": {"input": 1, "output": 4},
    }
    
    def get_price(self, model: str, tokens: int, is_output: bool) -> float:
        tier = self.PRICES.get(model, self.PRICES["default"])
        price_per_million = tier["output"] if is_output else tier["input"]
        return (tokens / 1_000_000) * price_per_million


@dataclass
class CostRecord:
    """成本记录"""
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    session_id: str | None = None


class BudgetExceededError(Exception):
    """预算超限错误"""
    pass


class CostTracker:
    """
    成本追踪器
    记录 Token 使用量、成本，按会话和模型统计
    """
    
    def __init__(
        self,
        pricing_model: PricingModel | None = None,
        monthly_budget: float | None = None,
        session_budget: float | None = None,
    ):
        self._pricing = pricing_model or DefaultPricingModel()
        self._monthly_budget = monthly_budget
        self._session_budget = session_budget
        
        self._monthly_usage: float = 0.0
        self._session_usage: float = 0.0
        self._records: list[CostRecord] = []
    
    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        session_id: str | None = None,
    ) -> CostRecord:
        """记录一次 API 调用"""
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        
        record = CostRecord(
            timestamp=datetime.now(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            session_id=session_id,
        )
        
        self._records.append(record)
        self._monthly_usage += cost
        if session_id:
            self._session_usage += cost
        
        return record
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        input_cost = self._pricing.get_price(model, input_tokens, is_output=False)
        output_cost = self._pricing.get_price(model, output_tokens, is_output=True)
        return input_cost + output_cost
    
    def get_total_cost(self) -> float:
        return self._monthly_usage
    
    def get_session_cost(self, session_id: str) -> float:
        return sum(r.cost for r in self._records if r.session_id == session_id)
    
    def check_budget(self) -> tuple[bool, str]:
        """检查是否超过预算，返回 (是否允许, 原因)"""
        if self._monthly_budget and self._monthly_usage >= self._monthly_budget:
            return False, f"Monthly budget exceeded: ${self._monthly_usage:.4f} >= ${self._monthly_budget}"
        if self._session_budget and self._session_usage >= self._session_budget:
            return False, f"Session budget exceeded: ${self._session_usage:.4f} >= ${self._session_budget}"
        return True, ""
    
    def reset_session(self) -> None:
        self._session_usage = 0.0
    
    def reset_monthly(self) -> None:
        self._monthly_usage = 0.0
        self._records.clear()
    
    def get_usage_summary(self) -> dict:
        """获取使用摘要"""
        total_input = sum(r.input_tokens for r in self._records)
        total_output = sum(r.output_tokens for r in self._records)
        return {
            "total_cost": self._monthly_usage,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "record_count": len(self._records),
        }
