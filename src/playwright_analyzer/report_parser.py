"""Playwright Report Parser - Extracts test results from HTML reports."""

import base64
import io
import json
import re
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup


@dataclass
class TestCase:
    """Represents a single test case."""

    title: str
    full_title: str
    file: str
    line: int
    status: str  # passed, failed, skipped, timedOut
    duration: int  # milliseconds
    error_message: Optional[str] = None
    error_stack: Optional[str] = None
    retry_count: int = 0
    annotations: List[str] = None
    steps: List[Dict[str, Any]] = None
    attachments: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.annotations is None:
            self.annotations = []
        if self.steps is None:
            self.steps = []
        if self.attachments is None:
            self.attachments = []


@dataclass
class TestSuite:
    """Represents a test suite (file)."""

    file: str
    title: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration: int
    test_cases: List[TestCase]

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100


@dataclass
class TestReport:
    """Complete test report summary."""

    total_tests: int
    passed: int
    failed: int
    skipped: int
    flaky: int
    duration: int  # milliseconds
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    test_suites: List[TestSuite]
    failed_tests: List[TestCase]
    config: Dict[str, Any]

    @property
    def pass_rate(self) -> float:
        """Calculate overall pass rate."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return self.duration / 1000.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return asdict(self)


class PlaywrightReportParser:
    """Parser for Playwright HTML reports."""

    def __init__(self, report_path: str = "playwright-report/index.html"):
        self.report_path = Path(report_path)
        self.raw_data = None
        self.files_data = []
        self.soup = None

    def parse(self) -> TestReport:
        """Parse the Playwright report and extract test results."""
        if not self.report_path.exists():
            raise FileNotFoundError(f"Report Paraser Report file not found: {self.report_path}")

        with open(self.report_path, encoding="utf-8") as f:
            html_content = f.read()

        self.soup = BeautifulSoup(html_content, "lxml")

        # Extract the JSON data embedded in the HTML
        self.raw_data, self.files_data = self._extract_json_data()
        if not self.raw_data:
            raise ValueError("Could not extract test data from report")

        return self._build_report()

    def _extract_json_data(self) -> Optional[Dict]:
        """Extract embedded JSON data from Playwright HTML report."""
        # Playwright embeds the test data in a script tag
        script_tags = self.soup.find_all("script")
        for script in script_tags:
            if (
                script.string
                and hasattr(script, "attrs")
                and script.attrs.get("id") == "playwrightReportBase64"
            ):
                # Extract base64 encoded data
                match = re.search(
                    r"data:application/zip;base64,([A-Za-z0-9+/=\s]+)", script.string, re.DOTALL
                )
                if match:
                    base64_data = match.group(1)
                    try:
                        # Decode base64 and extract ZIP content
                        zip_data = base64.b64decode(base64_data)
                        with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_file:
                            # Look for report.json in the ZIP
                            test_report, files_data = None, []
                            for file_name in zip_file.namelist():
                                if file_name.endswith("report.json") or "report.json" in file_name:
                                    json_data = zip_file.read(file_name).decode("utf-8")
                                    test_report = json.loads(json_data)
                                else:
                                    # open each file and parse it as json save it to debug files for inspection with indentation
                                    json_data = zip_file.read(file_name).decode("utf-8")
                                    try:
                                        parsed_data = json.loads(json_data)
                                        files_data.append((file_name, parsed_data))
                                    except json.JSONDecodeError:
                                        print(f"Failed to parse JSON from {file_name}")
                            return test_report, files_data

                    except Exception as e:
                        print(f"Error extracting ZIP data: {e}")
                        print(f"Base64 data length: {len(base64_data)}")
                        print(f"First 100 chars of base64: {base64_data[:100]}")
                        # Fallback: try treating as plain JSON
                        raise None

        return None

    def _build_report(self) -> TestReport:
        """Build TestReport from raw JSON data."""
        stats = self.raw_data.get("stats", {})
        config = self.raw_data.get("config", {})

        # Parse test suites and cases
        test_suites = []
        all_failed_tests = []

        # Handle new format with 'files' instead of 'suites'
        for file_data in self.raw_data.get("files", []):
            suite = self._parse_file_suite(file_data)
            test_suites.append(suite)
            all_failed_tests.extend([tc for tc in suite.test_cases if tc.status == "failed"])

        # Parse timestamps - handle both number and ISO string formats
        start_time = None
        end_time = None

        if "startTime" in self.raw_data:
            start_time_val = self.raw_data["startTime"]
            if isinstance(start_time_val, (int, float)):
                # Timestamp in milliseconds
                start_time = datetime.fromtimestamp(start_time_val / 1000)
            else:
                # ISO string format
                start_time = datetime.fromisoformat(str(start_time_val).replace("Z", "+00:00"))

        # Calculate end time from start time + duration if not provided
        end_time = start_time
        duration = self.raw_data.get("duration", 0)
        if start_time and duration:
            from datetime import timedelta

            end_time = start_time + timedelta(milliseconds=duration)

        return TestReport(
            total_tests=stats.get("total", 0),
            passed=stats.get("expected", 0),
            failed=stats.get("unexpected", 0),
            skipped=stats.get("skipped", 0),
            flaky=stats.get("flaky", 0),
            duration=int(duration),
            start_time=start_time,
            end_time=end_time,
            test_suites=test_suites,
            failed_tests=all_failed_tests,
            config=config,
        )

    def _parse_file_suite(self, file_data: Dict) -> TestSuite:
        """Parse a test file as a suite from new JSON format."""
        test_cases = []
        passed = failed = skipped = 0
        total_duration = 0

        # Parse all tests in this file
        for test_data in file_data.get("tests", []):
            test_case = self._parse_new_test_case(test_data)
            test_cases.append(test_case)

            if test_case.status == "passed":
                passed += 1
            elif test_case.status == "failed":
                failed += 1
            elif test_case.status == "skipped":
                skipped += 1

            total_duration += test_case.duration

        # Use file stats if available, otherwise calculate
        file_stats = file_data.get("stats", {})

        return TestSuite(
            file=file_data.get("fileName", ""),
            title=file_data.get("fileName", "").replace(".spec.ts", "").replace("/", " › "),
            total_tests=file_stats.get("total", len(test_cases)),
            passed=file_stats.get("expected", passed),
            failed=file_stats.get("unexpected", failed),
            skipped=file_stats.get("skipped", skipped),
            duration=total_duration,
            test_cases=test_cases,
        )

    def _parse_suite(self, suite_data: Dict) -> TestSuite:
        """Parse a test suite from raw data."""
        test_cases = []
        passed = failed = skipped = 0
        total_duration = 0

        # Recursively parse test cases
        for spec in suite_data.get("specs", []):
            test_case = self._parse_test_case(spec, suite_data)
            test_cases.append(test_case)

            if test_case.status == "passed":
                passed += 1
            elif test_case.status == "failed":
                failed += 1
            elif test_case.status == "skipped":
                skipped += 1

            total_duration += test_case.duration

        # Parse nested suites
        for nested_suite in suite_data.get("suites", []):
            nested = self._parse_suite(nested_suite)
            test_cases.extend(nested.test_cases)
            passed += nested.passed
            failed += nested.failed
            skipped += nested.skipped
            total_duration += nested.duration

        return TestSuite(
            file=suite_data.get("file", ""),
            title=suite_data.get("title", ""),
            total_tests=len(test_cases),
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration=total_duration,
            test_cases=test_cases,
        )

    def _parse_test_case(self, spec_data: Dict, suite_data: Dict) -> TestCase:
        """Parse a single test case."""
        # Get test results
        tests = spec_data.get("tests", [])
        if not tests:
            return TestCase(
                title=spec_data.get("title", ""),
                full_title=f"{suite_data.get('title', '')} › {spec_data.get('title', '')}",
                file=spec_data.get("file", suite_data.get("file", "")),
                line=spec_data.get("line", 0),
                status="skipped",
                duration=0,
            )

        # Use the last test result (in case of retries)
        test = tests[-1]
        results = test.get("results", [])

        if not results:
            return TestCase(
                title=spec_data.get("title", ""),
                full_title=f"{suite_data.get('title', '')} › {spec_data.get('title', '')}",
                file=spec_data.get("file", suite_data.get("file", "")),
                line=spec_data.get("line", 0),
                status="skipped",
                duration=0,
            )

        # Get the final result
        result = results[-1]

        # Extract error information if failed
        error_message = None
        error_stack = None
        if result.get("status") == "failed" and result.get("error"):
            error = result.get("error", {})
            error_message = error.get("message", "")
            error_stack = error.get("stack", "")

        # Extract steps
        steps = []
        for step in result.get("steps", []):
            steps.append(
                {
                    "title": step.get("title", ""),
                    "duration": step.get("duration", 0),
                    "error": step.get("error"),
                }
            )

        # Extract attachments
        attachments = []
        for attachment in result.get("attachments", []):
            attachments.append(
                {
                    "name": attachment.get("name", ""),
                    "path": attachment.get("path", ""),
                    "contentType": attachment.get("contentType", ""),
                }
            )

        return TestCase(
            title=spec_data.get("title", ""),
            full_title=f"{suite_data.get('title', '')} › {spec_data.get('title', '')}",
            file=spec_data.get("file", suite_data.get("file", "")),
            line=spec_data.get("line", 0),
            status=result.get("status", "unknown"),
            duration=result.get("duration", 0),
            error_message=error_message,
            error_stack=error_stack,
            retry_count=len(results) - 1,
            annotations=spec_data.get("annotations", []),
            steps=steps,
            attachments=attachments,
        )

    def _parse_new_test_case(self, test_data: Dict) -> TestCase:
        """Parse a single test case from new JSON format."""
        location = test_data.get("location", {})
        test_id = test_data.get("testId", "")
        file_id = test_id.split("-")[0]
        results = None
        for file_name, file_data in self.files_data:
            if file_name.startswith(file_id):
                detailed_tests_data = file_data.get("tests", [])
                for test in detailed_tests_data:
                    if test.get("testId") == test_id:
                        results = test.get("results", [])
                        break

        # Map outcomes to status
        outcome_to_status = {
            "expected": "passed",
            "unexpected": "failed",
            "skipped": "skipped",
            "flaky": "passed",  # Flaky tests eventually pass
        }

        status = outcome_to_status.get(test_data.get("outcome", "unknown"), "unknown")

        # Extract error information from results if failed
        error_message = None
        error_stack = None
        attachments = []
        steps = []

        if results:
            result = results[0]  # Take first result
            # Get attachments
            for attachment in result.get("attachments", []):
                attachments.append(
                    {
                        "name": attachment.get("name", ""),
                        "path": attachment.get("path", ""),
                        "contentType": attachment.get("contentType", ""),
                    }
                )

            # Get error info if present
            if "errors" in result and len(result["errors"]) > 0:
                error = result.get("errors", [{}])[0]
                error_message = error.get("message", "")
                error_stack = error.get("codeframe", "")

        # Create full title from path
        path = test_data.get("path", [])
        title = test_data.get("title", "")
        if path:
            full_title = " › ".join(path + [title])
        else:
            full_title = title

        return TestCase(
            title=title,
            full_title=full_title,
            file=location.get("file", ""),
            line=location.get("line", 0),
            status=status,
            duration=test_data.get("duration", 0),
            error_message=error_message,
            error_stack=error_stack,
            retry_count=len(results) - 1 if results else 0,
            annotations=test_data.get("annotations", []),
            steps=steps,
            attachments=attachments,
        )

    def get_failure_patterns(self) -> Dict[str, List[TestCase]]:
        """Group failures by error patterns."""
        report = self.parse()
        patterns = {}

        for test in report.failed_tests:
            if test.error_message:
                # Extract key error patterns
                error_key = self._extract_error_pattern(test.error_message)
                if error_key not in patterns:
                    patterns[error_key] = []
                patterns[error_key].append(test)

        return patterns

    def _extract_error_pattern(self, error_message: str) -> str:
        """Extract a normalized error pattern from error message."""
        # Remove specific values but keep the error type
        patterns = [
            (r"timeout \d+ms", "timeout"),
            (r"expected.*to be visible", "visibility assertion failed"),
            (r"expected.*to contain", "content assertion failed"),
            (r"locator.*not found", "element not found"),
            (r"click.*failed", "click failed"),
            (r"navigation.*failed", "navigation failed"),
        ]

        for pattern, replacement in patterns:
            if re.search(pattern, error_message, re.IGNORECASE):
                return replacement

        # Return first line of error as fallback
        return error_message.split("\n")[0][:100]
