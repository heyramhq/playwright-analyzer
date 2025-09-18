"""HTML Report Injector - Adds AI insights to Playwright reports."""

from pathlib import Path

from jinja2 import Template

try:
    from .agent import TestInsights
except ImportError:
    from agent import TestInsights


class PlaywrightReportInjector:
    """Injects AI-generated insights into Playwright HTML reports."""

    def __init__(self, report_path: str = "playwright-report/index.html"):
        self.report_path = Path(report_path)
        self.backup_path = self.report_path.with_suffix(".backup.html")

    def inject_insights(self, insights: TestInsights, markdown_summary: str) -> None:
        """Inject AI insights into the Playwright report."""
        if not self.report_path.exists():
            raise FileNotFoundError(f"Report file not found: {self.report_path}")

        # Create backup
        self._create_backup()

        # Read the original report
        with open(self.report_path, encoding="utf-8") as f:
            html_content = f.read()

        # Generate the insights HTML
        insights_html = self._generate_insights_html(insights, markdown_summary)

        # Inject into the report
        modified_html = self._inject_html(html_content, insights_html)

        # Write back the modified report
        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write(modified_html)

        print(f"✅ Insights injected into {self.report_path}")

    def _create_backup(self) -> None:
        """Create a backup of the original report."""
        if self.report_path.exists():
            import shutil

            shutil.copy2(self.report_path, self.backup_path)
            print(f"📁 Backup created: {self.backup_path}")

    def _generate_insights_html(self, insights: TestInsights, markdown_summary: str) -> str:
        """Generate HTML for the insights section."""
        template_str = """
<div id="ai-insights-container" style="
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem;
    margin: 2rem auto;
    border-radius: 12px;
    max-width: 1200px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    position: relative;
    overflow: hidden;
">
    <div style="position: absolute; top: 0; right: 0; opacity: 0.1; font-size: 200px; transform: rotate(-15deg);">
        🤖
    </div>

    <div style="position: relative; z-index: 1;">
        <h2 style="margin: 0 0 1rem 0; font-size: 2rem; display: flex; align-items: center; gap: 0.5rem;">
            🤖 AI Test Analysis
            <span style="
                background: {{ 'red' if insights.overall_health == 'Critical' else 'orange' if insights.overall_health == 'Warning' else '#4ade80' }};
                padding: 0.25rem 0.75rem;
                border-radius: 20px;
                font-size: 0.875rem;
                font-weight: 500;
            ">{{ insights.overall_health }}</span>
        </h2>

        <div style="
            background: rgba(255,255,255,0.95);
            color: #333;
            padding: 1.5rem;
            border-radius: 8px;
            margin-top: 1rem;
        ">
            <div style="
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin-bottom: 1.5rem;
            ">
                <div style="text-align: center; padding: 1rem; background: #f3f4f6; border-radius: 8px;">
                    <div style="font-size: 2rem; font-weight: bold; color: {{ '#ef4444' if insights.pass_rate < 70 else '#f59e0b' if insights.pass_rate < 90 else '#10b981' }};">
                        {{ "%.1f"|format(insights.pass_rate) }}%
                    </div>
                    <div style="color: #666; font-size: 0.875rem;">Pass Rate</div>
                </div>
                <div style="text-align: center; padding: 1rem; background: #f3f4f6; border-radius: 8px;">
                    <div style="font-size: 2rem; font-weight: bold; color: #333;">
                        {{ insights.total_tests }}
                    </div>
                    <div style="color: #666; font-size: 0.875rem;">Total Tests</div>
                </div>
                <div style="text-align: center; padding: 1rem; background: #f3f4f6; border-radius: 8px;">
                    <div style="font-size: 2rem; font-weight: bold; color: #ef4444;">
                        {{ insights.failed_tests }}
                    </div>
                    <div style="color: #666; font-size: 0.875rem;">Failed</div>
                </div>
                <div style="text-align: center; padding: 1rem; background: #f3f4f6; border-radius: 8px;">
                    <div style="font-size: 2rem; font-weight: bold; color: #6b7280;">
                        {{ "%.0f"|format(insights.confidence_score) }}%
                    </div>
                    <div style="color: #666; font-size: 0.875rem;">Confidence</div>
                </div>
            </div>

            <div style="
                background: #f9fafb;
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 1.5rem;
                border-left: 4px solid #667eea;
            ">
                <h3 style="margin: 0 0 0.5rem 0; color: #333; font-size: 1.125rem;">Summary</h3>
                <p style="margin: 0; color: #666; line-height: 1.6;">{{ insights.summary }}</p>
            </div>

            {% if insights.failure_analyses %}
            <details style="margin-bottom: 1.5rem;">
                <summary style="
                    cursor: pointer;
                    padding: 0.75rem;
                    background: #fee2e2;
                    border-radius: 8px;
                    font-weight: 600;
                    color: #991b1b;
                    user-select: none;
                ">
                    ⚠️ Failure Analysis ({{ insights.failure_analyses|length }} failures)
                </summary>
                <div style="margin-top: 1rem;">
                    {% for analysis in insights.failure_analyses %}
                    <div style="
                        background: white;
                        border: 1px solid #e5e7eb;
                        border-radius: 8px;
                        padding: 1rem;
                        margin-bottom: 0.75rem;
                    ">
                        <h4 style="margin: 0 0 0.5rem 0; color: #333; font-size: 1rem;">
                            {{ analysis.test_name }}
                            <span style="
                                background: {{ '#ef4444' if analysis.impact == 'Critical' else '#f59e0b' if analysis.impact == 'High' else '#3b82f6' }};
                                color: white;
                                padding: 0.125rem 0.5rem;
                                border-radius: 12px;
                                font-size: 0.75rem;
                                margin-left: 0.5rem;
                            ">{{ analysis.impact }}</span>
                        </h4>
                        <div style="color: #666; font-size: 0.875rem; line-height: 1.5;">
                            <p><strong>Category:</strong> {{ analysis.failure_category }}</p>
                            <p><strong>Root Cause:</strong> {{ analysis.root_cause }}</p>
                            <p><strong>Fix:</strong> {{ analysis.suggested_fix }}</p>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </details>
            {% endif %}

            {% if insights.recommendations %}
            <details style="margin-bottom: 1.5rem;">
                <summary style="
                    cursor: pointer;
                    padding: 0.75rem;
                    background: #dbeafe;
                    border-radius: 8px;
                    font-weight: 600;
                    color: #1e40af;
                    user-select: none;
                ">
                    💡 Recommendations
                </summary>
                <div style="margin-top: 1rem; padding: 0 1rem;">
                    <ol style="margin: 0; padding-left: 1.5rem; color: #666;">
                        {% for rec in insights.recommendations %}
                        <li style="margin-bottom: 0.5rem; line-height: 1.5;">{{ rec }}</li>
                        {% endfor %}
                    </ol>
                </div>
            </details>
            {% endif %}

            {% if insights.common_patterns %}
            <details style="margin-bottom: 1.5rem;">
                <summary style="
                    cursor: pointer;
                    padding: 0.75rem;
                    background: #fef3c7;
                    border-radius: 8px;
                    font-weight: 600;
                    color: #92400e;
                    user-select: none;
                ">
                    🔍 Common Patterns
                </summary>
                <div style="margin-top: 1rem; padding: 0 1rem;">
                    <ul style="margin: 0; padding-left: 1.5rem; color: #666;">
                        {% for pattern in insights.common_patterns %}
                        <li style="margin-bottom: 0.5rem; line-height: 1.5;">{{ pattern }}</li>
                        {% endfor %}
                    </ul>
                </div>
            </details>
            {% endif %}

            {% if insights.flaky_tests %}
            <details style="margin-bottom: 1.5rem;">
                <summary style="
                    cursor: pointer;
                    padding: 0.75rem;
                    background: #f3e8ff;
                    border-radius: 8px;
                    font-weight: 600;
                    color: #6b21a8;
                    user-select: none;
                ">
                    🎲 Flaky Tests Detected
                </summary>
                <div style="margin-top: 1rem; padding: 0 1rem;">
                    <ul style="margin: 0; padding-left: 1.5rem; color: #666;">
                        {% for test in insights.flaky_tests %}
                        <li style="margin-bottom: 0.5rem; line-height: 1.5;">{{ test }}</li>
                        {% endfor %}
                    </ul>
                </div>
            </details>
            {% endif %}

            <div style="
                margin-top: 1.5rem;
                padding-top: 1rem;
                border-top: 1px solid #e5e7eb;
                color: #9ca3af;
                font-size: 0.75rem;
                text-align: right;
            ">
                Analysis performed at {{ insights.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S') }}
                | Powered by AI with {{ "%.0f"|format(insights.confidence_score) }}% confidence
            </div>
        </div>
    </div>
</div>

<script>
// Add interactivity
document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('ai-insights-container');
    if (container) {
        // Smooth scroll to insights
        const scrollButton = document.createElement('button');
        scrollButton.innerHTML = '🤖 View AI Insights';
        scrollButton.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 24px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 1000;
            transition: transform 0.2s;
        `;
        scrollButton.onmouseover = () => scrollButton.style.transform = 'scale(1.05)';
        scrollButton.onmouseout = () => scrollButton.style.transform = 'scale(1)';
        scrollButton.onclick = () => container.scrollIntoView({ behavior: 'smooth', block: 'start' });
        document.body.appendChild(scrollButton);
    }
});
</script>
"""

        template = Template(template_str)
        return template.render(insights=insights)

    def _inject_html(self, original_html: str, insights_html: str) -> str:
        """Inject the insights HTML into the report."""
        # Find a good injection point - after the main header or before the first test suite
        injection_point = None

        # Try to find the main content area
        markers = [
            "</header>",
            '<div class="test-file-list">',
            '<div id="app">',
            "<body>",
        ]

        for marker in markers:
            if marker in original_html:
                injection_point = original_html.find(marker) + len(marker)
                break

        if injection_point:
            # Inject the insights HTML
            modified_html = (
                original_html[:injection_point]
                + "\n"
                + insights_html
                + "\n"
                + original_html[injection_point:]
            )
        else:
            # Fallback: inject before closing body tag
            modified_html = original_html.replace("</body>", insights_html + "\n</body>")

        return modified_html

    def restore_backup(self) -> None:
        """Restore the original report from backup."""
        if self.backup_path.exists():
            import shutil

            shutil.copy2(self.backup_path, self.report_path)
            print(f"✅ Original report restored from {self.backup_path}")
