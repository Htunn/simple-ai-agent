"""Unit tests for LogAnalyzer."""

import pytest
from src.aiops.log_analyzer import LogAnalyzer, LogAnalysisResult, LogSeverity


class TestLogAnalyzerBasic:
    def setup_method(self):
        self.analyzer = LogAnalyzer()

    def test_clean_log_has_zero_errors(self):
        result = self.analyzer.analyze("pod", "ns", "INFO: server started\nINFO: listening on :8080")
        assert result.error_count == 0
        assert result.detected_patterns == []

    def test_empty_log_returns_valid_result(self):
        result = self.analyzer.analyze("pod", "ns", "")
        assert isinstance(result, LogAnalysisResult)
        assert result.error_count == 0

    def test_result_has_pod_and_namespace(self):
        result = self.analyzer.analyze("my-pod", "my-ns", "INFO ok")
        assert result.pod_name == "my-pod"
        assert result.namespace == "my-ns"

    def test_total_lines_counted(self):
        log = "\n".join([f"line {i}" for i in range(50)])
        result = self.analyzer.analyze("pod", "ns", log)
        assert result.total_lines == 50

    def test_compiled_cache_populated_after_first_call(self):
        LogAnalyzer._compiled = None  # reset cache
        self.analyzer.analyze("pod", "ns", "test")
        assert LogAnalyzer._compiled is not None

    def test_second_call_reuses_cache(self):
        self.analyzer.analyze("pod", "ns", "test")
        cache_before = id(LogAnalyzer._compiled)
        self.analyzer.analyze("pod2", "ns2", "test2")
        assert id(LogAnalyzer._compiled) == cache_before


class TestLogAnalyzerPatterns:
    def setup_method(self):
        self.analyzer = LogAnalyzer()

    def test_oomkill_detected(self):
        result = self.analyzer.analyze("pod", "ns", "out of memory: Kill process 123")
        names = [p.pattern_name for p in result.detected_patterns]
        assert "OOMKill" in names

    def test_oomkill_increases_error_count(self):
        result = self.analyzer.analyze("pod", "ns", "out of memory: Kill process 123")
        assert result.error_count > 0

    def test_oomkill_severity_is_critical(self):
        result = self.analyzer.analyze("pod", "ns", "out of memory: Kill process 123")
        oom = next(p for p in result.detected_patterns if p.pattern_name == "OOMKill")
        assert oom.severity == LogSeverity.CRITICAL

    def test_connection_refused_detected(self):
        result = self.analyzer.analyze("pod", "ns", "Error: connection refused to db:5432")
        names = [p.pattern_name for p in result.detected_patterns]
        assert "Connection Refused" in names

    def test_panic_detected(self):
        result = self.analyzer.analyze("pod", "ns", "panic: runtime error: index out of range")
        names = [p.pattern_name for p in result.detected_patterns]
        assert "Panic" in names

    def test_segfault_detected(self):
        result = self.analyzer.analyze("pod", "ns", "segmentation fault (core dumped)")
        names = [p.pattern_name for p in result.detected_patterns]
        assert "Segfault" in names

    def test_authentication_failed_detected(self):
        result = self.analyzer.analyze("pod", "ns", "authentication failed: invalid token")
        names = [p.pattern_name for p in result.detected_patterns]
        assert "Authentication Failed" in names

    def test_disk_full_detected(self):
        result = self.analyzer.analyze("pod", "ns", "write /var/log: no space left on device")
        names = [p.pattern_name for p in result.detected_patterns]
        assert "Disk Full" in names

    def test_database_error_detected(self):
        result = self.analyzer.analyze("pod", "ns", "SQL error: deadlock detected, retry transaction")
        names = [p.pattern_name for p in result.detected_patterns]
        assert "Database Error" in names

    def test_tls_error_detected(self):
        result = self.analyzer.analyze("pod", "ns", "tls handshake error: x509: certificate verify failed")
        names = [p.pattern_name for p in result.detected_patterns]
        assert "TLS/SSL Error" in names

    def test_multiple_patterns_in_same_log(self):
        log = (
            "out of memory: Kill process 123\n"
            "connection refused to db:5432\n"
            "panic: goroutine stopped\n"
        )
        result = self.analyzer.analyze("pod", "ns", log)
        assert len(result.detected_patterns) >= 3

    def test_pattern_occurrence_count(self):
        log = "\n".join(["connection refused"] * 5)
        result = self.analyzer.analyze("pod", "ns", log)
        conn = next(p for p in result.detected_patterns if p.pattern_name == "Connection Refused")
        assert conn.count == 5

    def test_case_insensitive_matching(self):
        result = self.analyzer.analyze("pod", "ns", "OUT OF MEMORY: KILL PROCESS 999")
        names = [p.pattern_name for p in result.detected_patterns]
        assert "OOMKill" in names

    def test_python_traceback_detected(self):
        log = 'Traceback (most recent call last):\n  File "app.py", line 42\nValueError: bad value'
        result = self.analyzer.analyze("pod", "ns", log)
        names = [p.pattern_name for p in result.detected_patterns]
        assert "Python Traceback" in names


class TestLogAnalyzerTruncation:
    def setup_method(self):
        self.analyzer = LogAnalyzer()

    def test_oversized_log_is_truncated_and_analyzed(self):
        # Build a log well over 10 MB
        big_log = "normal info line\n" * 400_000  # ~6 MB
        extra = "X" * (5 * 1024 * 1024)  # another 5 MB
        result = self.analyzer.analyze("pod", "ns", big_log + extra)
        # Should not raise and should return a valid result
        assert isinstance(result, LogAnalysisResult)
        assert result.total_lines > 0

    def test_small_log_not_truncated(self):
        log = "INFO: started\n" * 10
        result = self.analyzer.analyze("pod", "ns", log)
        assert result.total_lines == 10


class TestLogAnalysisResultMarkdown:
    def test_to_markdown_no_patterns(self):
        from src.aiops.log_analyzer import LogAnalysisResult
        result = LogAnalysisResult(
            pod_name="web", namespace="default",
            total_lines=100, error_count=0, warning_count=0,
            detected_patterns=[], summary="all clear",
            raw_errors=[],
        )
        md = result.to_markdown()
        assert isinstance(md, str)
        assert len(md) > 0

    def test_to_markdown_includes_pattern_names(self):
        from src.aiops.log_analyzer import LogAnalysisResult, LogMatch
        match = LogMatch(
            pattern_name="OOMKill", severity=LogSeverity.CRITICAL,
            matched_lines=["out of memory"], count=3,
        )
        result = LogAnalysisResult(
            pod_name="pod", namespace="ns",
            total_lines=50, error_count=3, warning_count=0,
            detected_patterns=[match], summary="OOMKill detected",
            raw_errors=["out of memory"],
        )
        md = result.to_markdown()
        assert "OOMKill" in md
