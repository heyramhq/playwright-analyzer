"""PydanticAI Agent for analyzing Playwright test reports."""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

try:
    from .report_parser import TestCase, TestReport, TestSuite
except ImportError:
    from report_parser import TestReport

# Load environment variables
load_dotenv()


class TestFailureAnalysis(BaseModel):
    """Analysis of test failures."""

    test_name: str = Field(description="Name of the failed test")
    failure_category: str = Field(
        description="Category of failure (e.g., UI, Network, Timing, Logic)"
    )
    root_cause: str = Field(description="Identified root cause of the failure")
    impact: str = Field(description="Impact level: Critical, High, Medium, Low")
    suggested_fix: str = Field(description="Suggested fix or investigation steps")


class TestInsights(BaseModel):
    """Complete insights from test report analysis."""

    summary: str = Field(description="Executive summary of test results")
    overall_health: str = Field(description="Overall health status: Healthy, Warning, Critical")
    pass_rate: float = Field(description="Pass rate percentage")
    total_tests: int = Field(description="Total number of tests")
    failed_tests: int = Field(description="Number of failed tests")

    failure_analyses: List[TestFailureAnalysis] = Field(
        default_factory=list, description="Detailed analysis of each failure"
    )

    common_patterns: List[str] = Field(
        default_factory=list, description="Common failure patterns identified"
    )

    recommendations: List[str] = Field(
        default_factory=list, description="Priority recommendations for improvement"
    )

    risk_areas: List[str] = Field(
        default_factory=list, description="Areas of code/functionality at risk"
    )

    performance_issues: List[str] = Field(
        default_factory=list, description="Performance-related observations"
    )

    flaky_tests: List[str] = Field(
        default_factory=list, description="Tests that appear to be flaky"
    )

    confidence_score: float = Field(description="Confidence in the analysis (0-100)", ge=0, le=100)

    analysis_timestamp: datetime = Field(
        default_factory=datetime.now, description="Timestamp of analysis"
    )


@dataclass
class TestReportDependencies:
    """Dependencies for the agent."""

    report: TestReport
    context_file: Optional[str] = None


class PlaywrightReportAnalyzer:
    """Agent for analyzing Playwright test reports."""

    def __init__(self, model_name: str = None, api_key: str = None, api_base: str = None):
        """Initialize the analyzer with model configuration."""
        self.model_name = model_name or os.getenv("MODEL_NAME", "gpt-4o-mini")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_base = api_base or os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        # Initialize the OpenAI model
        self.model = OpenAIModel(
            self.model_name,
            provider=OpenAIProvider(
                api_key=self.api_key,
                base_url=self.api_base if self.api_base != "https://api.openai.com/v1" else None,
            ),
        )

        # Create the agent with structured output
        self.agent = Agent(
            self.model,
            output_type=TestInsights,
            deps_type=TestReportDependencies,
            system_prompt=self._get_system_prompt(),
        )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """You are an expert test automation engineer specializing in Playwright testing and failure analysis.
        Your task is to analyze test reports and provide actionable insights.

        When analyzing test failures:
        1. Identify the root cause based on error messages, stack traces, and test context
        2. Categorize failures (UI issues, timing/flakiness, network problems, logic errors, etc.)
        3. Assess the impact and severity
        4. Provide specific, actionable recommendations
        5. Identify patterns across multiple failures
        6. Note performance issues (slow tests, timeouts)



        Provide clear, concise, and actionable insights that help developers quickly fix issues."""

    async def analyze(self, report: TestReport, context_file: str = None) -> TestInsights:
        """Analyze the test report and generate insights."""
        # Load additional context if provided
        context_content = None
        if context_file and os.path.exists(context_file):
            with open(context_file) as f:
                context_content = f.read()

        # Prepare the prompt with test data
        prompt = self._create_analysis_prompt(report, context_content)

        # Run the agent
        deps = TestReportDependencies(report=report, context_file=context_content)
        result = await self.agent.run(prompt, deps=deps)
        return result.output

    def _create_analysis_prompt(self, report: TestReport, context: Optional[str]) -> str:
        """Create a detailed prompt for the agent."""
        prompt_parts = [
            f"Analyze this Playwright test report with {report.total_tests} total tests:",
            f"- Passed: {report.passed} ({report.pass_rate:.1f}%)",
            f"- Failed: {report.failed}",
            f"- Skipped: {report.skipped}",
            f"- Flaky: {report.flaky}",
            f"- Duration: {report.duration_seconds:.2f} seconds",
            "",
        ]

        if report.failed_tests:
            prompt_parts.append("Failed Tests Details:")
            for test in report.failed_tests[:10]:  # Limit to first 10 failures
                prompt_parts.append(f"\nTest: {test.full_title}")
                prompt_parts.append(f"File: {test.file}:{test.line}")
                prompt_parts.append(f"Duration: {test.duration}ms")
                if test.retry_count > 0:
                    prompt_parts.append(f"Retries: {test.retry_count}")
                if test.error_message:
                    # Truncate long error messages
                    error_msg = test.error_message[:500]
                    if len(test.error_message) > 500:
                        error_msg += "... (truncated)"
                    prompt_parts.append(f"Error: {error_msg}")
                if test.steps:
                    prompt_parts.append("Failed at steps:")
                    for step in test.steps[-3:]:  # Last 3 steps
                        if step.get("error"):
                            prompt_parts.append(f"  - {step['title']}: FAILED")
                        else:
                            prompt_parts.append(f"  - {step['title']}: OK")

        # Add test suite summary
        prompt_parts.append("\nTest Suite Performance:")
        for suite in report.test_suites:
            if suite.failed > 0:
                prompt_parts.append(
                    f"- {suite.file}: {suite.failed}/{suite.total_tests} failed "
                    f"({suite.pass_rate:.1f}% pass rate, {suite.duration}ms)"
                )

        # Add context if available
        if context:
            prompt_parts.append("\nApplication Context:")
            # Truncate context if too long
            context_excerpt = context[:2000]
            if len(context) > 2000:
                context_excerpt += "\n... (context truncated)"
            prompt_parts.append(context_excerpt)

        prompt_parts.append("\nProvide a comprehensive analysis of these test results.")

        return "\n".join(prompt_parts)

    def generate_summary_text(self, insights: TestInsights) -> str:
        """Generate a human-readable summary from insights."""
        lines = [
            "# Test Report Analysis",
            f"*Generated: {insights.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}*",
            f"*Confidence: {insights.confidence_score:.1f}%*",
            "",
            "## Summary",
            insights.summary,
            "",
            f"## Overall Health: {insights.overall_health}",
            f"- **Pass Rate**: {insights.pass_rate:.1f}%",
            f"- **Total Tests**: {insights.total_tests}",
            f"- **Failed Tests**: {insights.failed_tests}",
            "",
        ]

        if insights.failure_analyses:
            lines.extend(["## Failure Analysis", ""])
            for analysis in insights.failure_analyses:
                lines.extend(
                    [
                        f"### {analysis.test_name}",
                        f"- **Category**: {analysis.failure_category}",
                        f"- **Root Cause**: {analysis.root_cause}",
                        f"- **Impact**: {analysis.impact}",
                        f"- **Suggested Fix**: {analysis.suggested_fix}",
                        "",
                    ]
                )

        if insights.common_patterns:
            lines.extend(
                [
                    "## Common Patterns",
                    *[f"- {pattern}" for pattern in insights.common_patterns],
                    "",
                ]
            )

        if insights.recommendations:
            lines.extend(
                [
                    "## Recommendations",
                    *[f"{i + 1}. {rec}" for i, rec in enumerate(insights.recommendations)],
                    "",
                ]
            )

        if insights.risk_areas:
            lines.extend(["## Risk Areas", *[f"- {risk}" for risk in insights.risk_areas], ""])

        if insights.performance_issues:
            lines.extend(
                [
                    "## Performance Issues",
                    *[f"- {issue}" for issue in insights.performance_issues],
                    "",
                ]
            )

        if insights.flaky_tests:
            lines.extend(
                ["## Flaky Tests Detected", *[f"- {test}" for test in insights.flaky_tests], ""]
            )

        return "\n".join(lines)
