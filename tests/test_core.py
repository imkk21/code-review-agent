from core.diff_parser import parse_diff
from core.static_analysis import analyze_file

def test_parse_diff():
    diff_text = """diff --git a/test.py b/test.py
new file mode 100644
index 0000000..e69de29
--- /dev/null
+++ b/test.py
@@ -0,0 +1,3 @@
+print("Hello World")
+api_key = "12345"
+return
"""
    files = parse_diff(diff_text)
    assert len(files) == 1
    assert files[0]["file_path"] == "test.py"
    assert files[0]["is_new"] is True
    assert files[0]["added_lines"] == [1, 2, 3]

def test_analyze_file_vulnerable():
    code = """
# Dangerous code
API_KEY = "KGAT_ea34dc35c5f3e3fef822bcbb14944036"
def test(items=[]):
    eval("1+1")
"""
    findings = analyze_file(code, "test.py")
    rule_ids = [f["rule_id"] for f in findings]
    assert "SEC-001" in rule_ids      # Hardcoded Secret
    assert "STYLE-001" in rule_ids    # Mutable Default
    assert "SEC-003" in rule_ids      # Dangerous Eval

def test_analyze_file_clean():
    code = """
# Safe code
API_KEY = os.environ.get("API_KEY")
# Avoid using eval() here
def test(items=None):
    if items is None:
        items = []
"""
    findings = analyze_file(code, "test.py")
    assert len(findings) == 0
