#!/usr/bin/env python3
"""Main script to analyze Playwright test reports with AI."""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

try:
    from .agent import PlaywrightReportAnalyzer
    from .report_injector import PlaywrightReportInjector
    from .report_parser import PlaywrightReportParser
except ImportError:
    # Support direct execution
    sys.path.insert(0, str(Path(__file__).parent))
    from agent import PlaywrightReportAnalyzer
    from report_injector import PlaywrightReportInjector
    from report_parser import PlaywrightReportParser

# Initialize Rich console for pretty output
console = Console()


async def analyze_playwright_report(
    report_path: str = "../playwright-report/index.html",
    context_file: str = "../CONTEXT-TEST.md",
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    inject_insights: bool = True,
) -> None:
    """
    Analyze Playwright test report and inject AI insights.

    Args:
        report_path: Path to the Playwright HTML report
        context_file: Optional context file with application information
        model_name: OpenAI-compatible model name
        api_key: API key for the model
        api_base: Base URL for the API
        inject_insights: Whether to inject insights back into the HTML report
    """
    try:
        # Step 1: Parse the report
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Parsing Playwright report...", total=None)

            parser = PlaywrightReportParser(report_path)
            report = parser.parse()
            progress.update(task, description="Report parsed successfully!")

        # Display basic statistics
        console.print(
            Panel(
                f"[bold green]Test Report Summary[/bold green]\n\n"
                f"Total Tests: {report.total_tests}\n"
                f"Passed: [green]{report.passed}[/green]\n"
                f"Failed: [red]{report.failed}[/red]\n"
                f"Skipped: [yellow]{report.skipped}[/yellow]\n"
                f"Pass Rate: [{'green' if report.pass_rate >= 90 else 'yellow' if report.pass_rate >= 70 else 'red'}]"
                f"{report.pass_rate:.1f}%[/]\n"
                f"Duration: {report.duration_seconds:.2f}s",
                title="📊 Test Results",
                border_style="blue",
            )
        )

        # Step 2: Analyze with AI if there are failures or if explicitly requested
        if report.failed > 0 or report.pass_rate < 100:
            console.print("\n[bold yellow]🤖 Starting AI Analysis...[/bold yellow]\n")

            # Initialize the analyzer
            analyzer = PlaywrightReportAnalyzer(
                model_name=model_name, api_key=api_key, api_base=api_base
            )

            # Check for context file
            context_path = Path(context_file) if context_file else None
            if context_path and not context_path.exists():
                console.print(f"[yellow]⚠️  Context file not found: {context_file}[/yellow]")
                context_path = None

            # Analyze the report
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Analyzing test failures with AI...", total=None)

                insights = await analyzer.analyze(
                    report, str(context_path) if context_path else None
                )

                progress.update(task, description="Analysis complete!")

            # Generate summary
            summary_text = analyzer.generate_summary_text(insights)

            # Display the analysis
            console.print("\n")
            console.print(
                Panel(
                    Markdown(summary_text),
                    title="🤖 AI Test Analysis",
                    border_style="magenta",
                    padding=(1, 2),
                )
            )

            # Step 3: Inject insights into HTML report
            if inject_insights:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task("Injecting insights into HTML report...", total=None)

                    injector = PlaywrightReportInjector(report_path)
                    injector.inject_insights(insights, summary_text)

                    progress.update(task, description="Insights injected successfully!")

                console.print("\n[bold green]✅ Analysis complete![/bold green]")
                console.print(f"[dim]View the enhanced report at: {report_path}[/dim]\n")

            # Save insights to JSON file
            insights_file = Path(report_path).parent / "ai-insights.json"
            import json

            with open(insights_file, "w") as f:
                json.dump(insights.model_dump(mode="json"), f, indent=2, default=str)
            console.print(f"[dim]Insights saved to: {insights_file}[/dim]\n")

        else:
            console.print(
                "\n[bold green]✅ All tests passed! No failures to analyze.[/bold green]\n"
            )

    except FileNotFoundError as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        console.print("[dim]Make sure to run Playwright tests first to generate the report.[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]❌ Unexpected error: {e}[/bold red]")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Analyze Playwright test reports with AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze with default settings (uses .env file)
  python analyze_report.py

  # Specify custom report path
  python analyze_report.py --report ../playwright-report/index.html

  # Use a specific model
  python analyze_report.py --model gpt-4o

  # Use local Ollama model
  python analyze_report.py --model llama3.2 --api-base http://localhost:11434/v1

  # Skip HTML injection (only show analysis)
  python analyze_report.py --no-inject
        """,
    )

    parser.add_argument(
        "--report",
        default="../playwright-report/index.html",
        help="Path to Playwright HTML report (default: ../playwright-report/index.html)",
    )

    parser.add_argument(
        "--context",
        default="../CONTEXT-TEST.md",
        help="Path to context file (default: ../CONTEXT-TEST.md)",
    )

    parser.add_argument(
        "--model",
        default=os.getenv("MODEL_NAME", "Qwen/Qwen3-32B"),
        help="Model name (default: from .env or gpt-4o-mini)",
    )

    parser.add_argument(
        "--api-key", default=os.getenv("OPENAI_API_KEY"), help="API key (default: from .env)"
    )

    parser.add_argument(
        "--api-base",
        default=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
        help="API base URL (default: from .env or OpenAI)",
    )

    parser.add_argument(
        "--no-inject", action="store_true", help="Don't inject insights into HTML report"
    )

    args = parser.parse_args()

    # Check for API key
    if not args.api_key and args.api_base == "https://api.openai.com/v1":
        console.print("[bold red]❌ Error: OpenAI API key is required![/bold red]")
        console.print("[dim]Set OPENAI_API_KEY in .env file or use --api-key argument[/dim]")
        console.print("[dim]Or use a local model with --api-base argument[/dim]")
        sys.exit(1)

    # Display configuration
    console.print(
        Panel(
            f"[bold]Configuration[/bold]\n\n"
            f"Report: {args.report}\n"
            f"Context: {args.context}\n"
            f"Model: {args.model}\n"
            f"API Base: {args.api_base}\n"
            f"Inject Insights: {'Yes' if not args.no_inject else 'No'}",
            title="⚙️  Settings",
            border_style="cyan",
        )
    )

    # Run the analysis
    asyncio.run(
        analyze_playwright_report(
            report_path=args.report,
            context_file=args.context,
            model_name=args.model,
            api_key=args.api_key,
            api_base=args.api_base,
            inject_insights=not args.no_inject,
        )
    )


if __name__ == "__main__":
    main()
