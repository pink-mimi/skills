import json, subprocess, sys, tempfile, unittest
from pathlib import Path
from PIL import Image

SKILL=Path(__file__).resolve().parents[1]
class WechatContentTests(unittest.TestCase):
    def build(self, fixture, temp):
        result=subprocess.run([sys.executable,str(SKILL/"scripts/run.py"),"all","--input",str(SKILL/"tests/fixtures"/fixture),"--output-root",temp],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        return next(Path(temp).glob(f"wechat/*/*/微信版.html")).parent

    def test_both_column_templates(self):
        with tempfile.TemporaryDirectory() as temp:
            for fixture in ("daily-news-content-package.json","github-hot-content-package.json"):
                result=subprocess.run([sys.executable,str(SKILL/"scripts/run.py"),"all","--input",str(SKILL/"tests/fixtures"/fixture),"--output-root",temp],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(len(list(Path(temp).glob("wechat/*/*/微信版.html"))),2)
            self.assertEqual(len(list(Path(temp).glob("wechat/*/*/images/合并封面.png"))),2)
    def test_rejects_unknown_schema(self):
        bad=SKILL/"tests/fixtures/unknown-schema.json"
        with tempfile.TemporaryDirectory() as temp:
            result=subprocess.run([sys.executable,str(SKILL/"scripts/run.py"),"all","--input",str(bad),"--output-root",temp],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)

    def test_news_uses_news_template_and_embedded_copy_images(self):
        with tempfile.TemporaryDirectory() as temp:
            out=self.build("daily-news-content-package.json",temp)
            page=(out/"微信版.html").read_text(encoding="utf-8")
            article=(out/"公众号成稿.md").read_text(encoding="utf-8")
            self.assertIn("昨日坐标",page)
            self.assertIn("data:image/png;base64,",page)
            self.assertNotIn('src="images/',page)
            self.assertIn("images/新闻-01.png",article)
            self.assertNotIn("images/项目-01.png",article)

    def test_github_uses_project_template(self):
        with tempfile.TemporaryDirectory() as temp:
            out=self.build("github-hot-content-package.json",temp)
            page=(out/"微信版.html").read_text(encoding="utf-8")
            self.assertIn("开源坐标",page)
            self.assertIn("许可证",page)
            self.assertIn("images/项目-01.png",(out/"公众号成稿.md").read_text(encoding="utf-8"))

    def test_cover_is_composed_and_versioned(self):
        with tempfile.TemporaryDirectory() as temp:
            out=self.build("daily-news-content-package.json",temp)
            with Image.open(out/"images/合并封面.png") as combined:
                self.assertEqual(combined.size,(1283,383))
                colors=combined.convert("RGB").getcolors(maxcolors=2_000_000)
                self.assertIsNotNone(colors)
                self.assertGreater(len(colors),20)
            manifest=json.loads((out/"render-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["content_template"],"daily-news")
            self.assertRegex(manifest["template_version"],r"^\d+\.\d+\.\d+$")
            self.assertEqual(manifest["image_mode"],"template_fallback")
if __name__=="__main__": unittest.main()
