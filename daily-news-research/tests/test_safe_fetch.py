import importlib.util
import gzip
import unittest
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("safe_fetch",SKILL/"scripts/safe_fetch.py")
safe_fetch=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(safe_fetch)


class SafeFetchTests(unittest.TestCase):
    def test_validate_url_allows_public_https(self):
        result=safe_fetch.validate_url("https://www.gov.cn/zhengce/",resolver=lambda host:["93.184.216.34"])
        self.assertEqual(result.scheme,"https")

    def test_validate_url_rejects_private_and_metadata_addresses(self):
        for url,address in (
            ("http://localhost/a","127.0.0.1"),
            ("https://intranet.example/a","10.0.0.8"),
            ("https://metadata.example/a","169.254.169.254"),
            ("file:///etc/passwd","127.0.0.1"),
        ):
            with self.subTest(url=url):
                with self.assertRaises(safe_fetch.UnsafeUrlError):
                    safe_fetch.validate_url(url,resolver=lambda host,value=address:[value])

    def test_http_requires_explicit_source_allowance(self):
        with self.assertRaises(safe_fetch.UnsafeUrlError):
            safe_fetch.validate_url("http://www.people.com.cn/rss.xml",resolver=lambda host:["93.184.216.34"])
        safe_fetch.validate_url("http://www.people.com.cn/rss.xml",allow_http=True,resolver=lambda host:["93.184.216.34"])

    def test_fetch_limits_response_size_and_reports_status(self):
        class Response:
            status=200
            headers={"Content-Type":"text/html"}
            url="https://www.gov.cn/a"
            def read(self,size=-1): return b"123456789"
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def geturl(self): return self.url
        result=safe_fetch.fetch(
            {"url":"https://www.gov.cn/a","max_response_bytes":4,"canonical_domains":["gov.cn"]},
            opener=lambda request,timeout:Response(),resolver=lambda host:["93.184.216.34"])
        self.assertEqual(result.status,"blocked")
        self.assertIn("响应体",result.error)

    def test_fetch_maps_rate_limit_and_timeout(self):
        class HttpError(Exception):
            code=429
        limited=safe_fetch.fetch(
            {"url":"https://www.gov.cn/a","canonical_domains":["gov.cn"]},
            opener=lambda request,timeout:(_ for _ in ()).throw(HttpError()),resolver=lambda host:["93.184.216.34"])
        timed=safe_fetch.fetch(
            {"url":"https://www.gov.cn/a","canonical_domains":["gov.cn"]},
            opener=lambda request,timeout:(_ for _ in ()).throw(TimeoutError()),resolver=lambda host:["93.184.216.34"])
        self.assertEqual(limited.status,"rate_limited")
        self.assertEqual(timed.status,"timeout")

    def test_redirect_target_is_revalidated(self):
        class Response:
            status=200
            headers={"Content-Type":"text/html"}
            def read(self,size=-1): return b"ok"
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def geturl(self): return "http://127.0.0.1/internal"
        result=safe_fetch.fetch(
            {"url":"https://www.gov.cn/a","canonical_domains":["gov.cn"]},
            opener=lambda request,timeout:Response(),
            resolver=lambda host:["127.0.0.1"] if host=="127.0.0.1" else ["93.184.216.34"])
        self.assertEqual(result.status,"blocked")

    def test_gzip_response_is_decompressed_before_parsing(self):
        payload=gzip.compress(b"<html><body>news</body></html>")
        class Response:
            status=200
            headers={"Content-Type":"text/html","Content-Encoding":"gzip"}
            def read(self,size=-1): return payload
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def geturl(self): return "https://www.mem.gov.cn/gk/"
        result=safe_fetch.fetch({"url":"https://www.mem.gov.cn/gk/","canonical_domains":["mem.gov.cn"]},opener=lambda request,timeout:Response(),resolver=lambda host:["93.184.216.34"])
        self.assertEqual(result.payload,b"<html><body>news</body></html>")


if __name__=="__main__":
    unittest.main()
