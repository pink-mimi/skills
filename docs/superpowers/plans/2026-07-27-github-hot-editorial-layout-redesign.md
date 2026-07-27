# GitHub Hot Editorial Layout Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained GitHub weekly research and WeChat production pipeline that finds projects which became hot during the last seven days and turns them into an attractive, evidence-backed, mobile-first WeChat audit package without changing the established daily-news column.

**Architecture:** Keep `github-hot-research` platform-neutral and add a focused editorial evidence module beside its existing schema-v2 normalizer. Split GitHub-specific article composition, theme selection, project-image handling, and audit rendering out of the generic WeChat renderer into focused modules; `wechat-content/scripts/run.py` remains the dispatcher and shared output coordinator. Existing daily-news functions and fixtures remain unchanged and serve as regression locks.

**Tech Stack:** Python 3 standard library, Pillow, `unittest`, inline-styled HTML, JSON fixtures, the local Skill validator.

---

## File map

**Create**

- `github-hot-research/scripts/editorial.py` — derive evidence-backed weekly theme, hot reason, use case, editorial summary, opening angles, and closing observations.
- `github-hot-research/tests/test_editorial.py` — focused research/editorial behavior tests.
- `github-hot-research/tests/fixtures/weekly-hot-candidates.json` — 12-candidate seven-day fixture with new breakouts, mature resurging projects, and rejected projects.
- `wechat-content/scripts/github_hot_column.py` — GitHub v2 title, opening, project sections, closing, and review-panel model.
- `wechat-content/scripts/github_hot_visuals.py` — deterministic theme palette and GitHub project-image selection/render metadata.
- `wechat-content/tests/test_github_hot_column.py` — focused copy, layout, evidence, and audit-separation tests.
- `wechat-content/tests/fixtures/github-hot-five-projects-v2.json` — full five-project visual acceptance fixture.

**Modify**

- `github-hot-research/scripts/run.py` — call editorial derivation, enforce weekly-hot and mature-project constraints, validate new fields.
- `github-hot-research/assets/default-config.json` — add weekly-hot evidence and mature-project caps.
- `github-hot-research/references/content-package-v2.md` — document editorial evidence contract.
- `github-hot-research/references/sources-and-risks.md` — document seven-day heat evidence and exclusion rules.
- `github-hot-research/tests/test_skill.py` — keep schema-v2 and selection regression tests.
- `wechat-content/scripts/run.py` — dispatch GitHub v2 through focused modules and record deterministic theme/image data.
- `wechat-content/scripts/rendering.py` — retain shared HTML/cover/news rendering and delegate GitHub v2 behavior.
- `wechat-content/references/github-hot.md` — document the approved editorial-card structure and reader/audit boundary.
- `wechat-content/references/image2-workflow.md` — document official/Image2/local visual hierarchy.
- `wechat-content/tests/test_skill.py` — retain all existing daily-news and shared-output regressions.
- `wechat-content/assets/default-config.json` — add GitHub theme families without changing daily-news configuration.

## Task 1: Preserve and commit the existing schema-v2 foundation

**Files:**

- Modify: `github-hot-research/scripts/run.py`
- Modify: `github-hot-research/assets/default-config.json`
- Modify: `github-hot-research/tests/test_skill.py`
- Modify: `github-hot-research/references/content-package-v2.md`
- Modify: `wechat-content/scripts/run.py`
- Modify: `wechat-content/scripts/rendering.py`
- Modify: `wechat-content/tests/test_skill.py`
- Test: `github-hot-research/tests/test_skill.py`
- Test: `wechat-content/tests/test_skill.py`

- [ ] **Step 1: Inspect the current uncommitted foundation**

Run:

```powershell
git status --short
git diff -- github-hot-research wechat-content
```

Expected: only the already reviewed schema-v2 research, lightweight GitHub rendering, image hierarchy, tests, fixtures, and documentation are present; unrelated user work is not staged.

- [ ] **Step 2: Run the current research regression suite**

Run:

```powershell
python -m unittest discover -s github-hot-research/tests -v
```

Expected: `Ran 20 tests` and `OK`.

- [ ] **Step 3: Run the current WeChat regression suite**

Run:

```powershell
python -m unittest discover -s wechat-content/tests -v
```

Expected: `Ran 56 tests` and `OK`.

- [ ] **Step 4: Commit only the schema-v2 foundation**

```powershell
git add github-hot-research wechat-content
git diff --cached --check
git commit -m "feat: add github hot schema v2 foundation"
```

Expected: the design and implementation work begins from a green, recoverable commit; no outputs, credentials, or visual-companion files are included.

## Task 2: Add seven-day heat evidence and breakout selection

**Files:**

- Create: `github-hot-research/tests/test_editorial.py`
- Create: `github-hot-research/tests/fixtures/weekly-hot-candidates.json`
- Create: `github-hot-research/scripts/editorial.py`
- Modify: `github-hot-research/scripts/run.py`
- Modify: `github-hot-research/assets/default-config.json`

- [ ] **Step 1: Write failing heat-window and breakout tests**

Create tests with these concrete behaviors:

```python
class WeeklyHeatTests(unittest.TestCase):
    def test_candidate_requires_heat_evidence_inside_window(self):
        result = editorial.assess_heat(
            {
                "repo": "example/new-tool",
                "created_at": "2026-07-23T08:00:00Z",
                "heat_evidence": [
                    {
                        "kind": "github_trending",
                        "observed_at": "2026-07-24T09:00:00+08:00",
                        "url": "https://github.com/trending",
                    }
                ],
            },
            "2026-07-20T09:00:00+08:00",
            "2026-07-27T09:00:00+08:00",
        )
        self.assertTrue(result["eligible"])
        self.assertEqual(result["heat_class"], "new_breakout")

    def test_old_total_stars_without_weekly_evidence_is_not_hot(self):
        result = editorial.assess_heat(
            {"repo": "example/old", "stars": 90000, "heat_evidence": []},
            "2026-07-20T09:00:00+08:00",
            "2026-07-27T09:00:00+08:00",
        )
        self.assertFalse(result["eligible"])
        self.assertIn("本周热度证据不足", result["rejection_reasons"])

    def test_mature_resurging_projects_are_capped_at_two(self):
        package = build_package_from_fixture("weekly-hot-candidates.json")
        mature = [item for item in package["items"] if item["heat"]["heat_class"] == "mature_resurgence"]
        self.assertLessEqual(len(mature), 2)
        self.assertGreater(len(package["items"]) - len(mature), len(mature))
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
python -m unittest discover -s github-hot-research/tests -p test_editorial.py -v
```

Expected: FAIL because `editorial.py`, `assess_heat`, and the fixture do not exist.

- [ ] **Step 3: Implement the minimal heat assessor**

Create `github-hot-research/scripts/editorial.py` with the public interface:

```python
from datetime import datetime


def parse_time(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def assess_heat(candidate, window_start, window_end):
    start = parse_time(window_start)
    end = parse_time(window_end)
    evidence = [
        row for row in candidate.get("heat_evidence", [])
        if row.get("url")
        and start <= parse_time(row["observed_at"]).astimezone(start.tzinfo) < end
    ]
    created_at = candidate.get("created_at")
    new_in_window = bool(created_at and start <= parse_time(created_at).astimezone(start.tzinfo) < end)
    release_in_window = any(row.get("kind") in {"release", "official_launch"} for row in evidence)
    eligible = bool(evidence)
    heat_class = "new_breakout" if new_in_window else "mature_resurgence" if release_in_window else "weekly_breakout"
    return {
        "eligible": eligible,
        "heat_class": heat_class if eligible else "insufficient",
        "evidence": evidence,
        "rejection_reasons": [] if eligible else ["本周热度证据不足"],
    }
```

Update `default-config.json`:

```json
"weekly_heat": {
  "evidence_minimum": 1,
  "mature_resurgence_maximum": 2,
  "prefer_new_breakouts": true
}
```

Call `assess_heat` before scoring in `run.py`; preserve rejected candidates and combine heat rejection reasons with existing reasons.

- [ ] **Step 4: Run focused and existing research tests**

Run:

```powershell
python -m unittest discover -s github-hot-research/tests -p test_editorial.py -v
python -m unittest discover -s github-hot-research/tests -v
```

Expected: all focused tests and all existing research tests pass.

- [ ] **Step 5: Commit**

```powershell
git add github-hot-research/scripts/editorial.py github-hot-research/scripts/run.py github-hot-research/assets/default-config.json github-hot-research/tests/test_editorial.py github-hot-research/tests/fixtures/weekly-hot-candidates.json
git commit -m "feat: select github projects by weekly heat evidence"
```

## Task 3: Derive evidence-backed weekly editorial material

**Files:**

- Modify: `github-hot-research/scripts/editorial.py`
- Modify: `github-hot-research/scripts/run.py`
- Modify: `github-hot-research/tests/test_editorial.py`
- Modify: `github-hot-research/references/content-package-v2.md`

- [ ] **Step 1: Write failing editorial-evidence tests**

Add:

```python
def test_editorial_material_only_uses_selected_project_evidence(self):
    selected = load_fixture_items()
    material = editorial.derive_weekly_editorial(selected)
    self.assertIn("weekly_theme", material)
    self.assertTrue(material["theme_evidence"])
    allowed = {item["repo"] for item in selected}
    self.assertTrue({row["repo"] for row in material["theme_evidence"]} <= allowed)


def test_no_common_theme_uses_multi_route_mode(self):
    selected = unrelated_selected_items()
    material = editorial.derive_weekly_editorial(selected)
    self.assertEqual(material["opening_mode"], "multiple_routes")
    self.assertEqual(material["weekly_theme"], "")


def test_each_project_has_hot_reason_use_case_and_editorial_summary(self):
    package = build_package_from_fixture("weekly-hot-candidates.json")
    for item in package["items"]:
        self.assertTrue(item["editorial"]["hot_reason"])
        self.assertTrue(item["editorial"]["hot_reason_evidence"])
        self.assertTrue(item["editorial"]["use_case"])
        self.assertGreaterEqual(len(item["editorial"]["summary"]), 40)
        self.assertEqual(len(item["reader_card"]["highlights"]), 3)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m unittest discover -s github-hot-research/tests -p test_editorial.py -v
```

Expected: FAIL because `derive_weekly_editorial` and `item["editorial"]` are missing.

- [ ] **Step 3: Implement deterministic editorial derivation**

Add interfaces:

```python
def project_editorial(candidate, heat):
    card = candidate["reader_card"]
    return {
        "hot_reason": candidate.get("hot_reason", ""),
        "hot_reason_evidence": heat["evidence"],
        "use_case": candidate.get("use_case") or card["summary"],
        "summary": candidate.get("editorial_summary") or card["recommendation"],
    }


def derive_weekly_editorial(selected):
    category_groups = {}
    for item in selected:
        category_groups.setdefault(item["category"], []).append(item)
    dominant = max(category_groups.values(), key=len, default=[])
    has_theme = len(dominant) >= 3
    return {
        "opening_mode": "theme" if has_theme else "multiple_routes",
        "weekly_theme": dominant[0]["category"] if has_theme else "",
        "theme_evidence": [
            {"repo": item["repo"], "hot_reason": item["editorial"]["hot_reason"]}
            for item in dominant
        ] if has_theme else [],
        "title_options": [
            f"这周突然走红的 {len(selected)} 个开源项目",
            f"本周开源坐标：{len(selected)} 个项目正在解决的新问题",
            f"从新爆款到成熟工具：本周值得关注的 {len(selected)} 个项目",
        ],
        "editorial_angles": [item["editorial"]["use_case"] for item in selected[:3]],
        "closing_observations": [item["editorial"]["summary"] for item in selected[:3]],
    }
```

The function may normalize source-provided editorial material, but it must not invent a hot reason when the candidate does not provide one. Missing required material downgrades package status to `needs_review`.

- [ ] **Step 4: Validate the schema contract**

Extend `validate_package` so each selected item requires `heat` and `editorial`, and the top level requires `editorial`. Add documentation showing exact keys and the rule that every claim must point to evidence.

- [ ] **Step 5: Run all research tests**

Run:

```powershell
python -m unittest discover -s github-hot-research/tests -v
```

Expected: all tests pass; no WeChat files are created by the research Skill.

- [ ] **Step 6: Commit**

```powershell
git add github-hot-research/scripts/editorial.py github-hot-research/scripts/run.py github-hot-research/tests/test_editorial.py github-hot-research/references/content-package-v2.md
git commit -m "feat: add evidence-backed github editorial material"
```

## Task 4: Create the isolated GitHub WeChat column composer

**Files:**

- Create: `wechat-content/scripts/github_hot_column.py`
- Create: `wechat-content/tests/test_github_hot_column.py`
- Create: `wechat-content/tests/fixtures/github-hot-five-projects-v2.json`
- Modify: `wechat-content/scripts/run.py`
- Modify: `wechat-content/scripts/rendering.py`

- [ ] **Step 1: Write failing article-structure tests**

Create:

```python
class GithubHotColumnTests(unittest.TestCase):
    def test_article_has_dynamic_opening_five_projects_and_reflective_closing(self):
        payload = load_fixture("github-hot-five-projects-v2.json")
        article, title, summary = github_hot_column.build_article(payload)
        self.assertNotEqual(title, "本周 GitHub 热门：5 个值得关注的开源项目")
        self.assertIn(payload["editorial"]["theme_evidence"][0]["repo"], article)
        self.assertEqual(article.count("<!-- github-project:start -->"), 5)
        self.assertIn("最后留一个坐标", article)

    def test_project_uses_approved_editorial_card_order(self):
        article, _, _ = github_hot_column.build_article(load_fixture())
        positions = [
            article.index("为什么这周火"),
            article.index("项目官方资料"),
            article.index("一句话推荐"),
            article.index("适合谁"),
            article.index("上手条件"),
            article.index("项目地址"),
        ]
        self.assertEqual(positions, sorted(positions))

    def test_reader_copy_omits_audit_burden(self):
        article, _, _ = github_hot_column.build_article(load_fixture())
        for phrase in ("未发现明确许可证", "license_status", "verified_at", "内部审核"):
            self.assertNotIn(phrase, article)
```

- [ ] **Step 2: Run and verify RED**

Run:

```powershell
python -m unittest discover -s wechat-content/tests -p test_github_hot_column.py -v
```

Expected: FAIL because the module and five-project fixture do not exist.

- [ ] **Step 3: Implement the focused composer**

Create the public interface:

```python
def build_title(payload):
    editorial = payload["editorial"]
    if editorial["opening_mode"] == "theme":
        return editorial["title_options"][0]
    return f"这周突然走红的 {len(payload['items'])} 个开源项目"


def build_project(item, index):
    card = item["reader_card"]
    edit = item["editorial"]
    metrics = card["metrics"]
    metric_parts = [metrics.get("language"), f"{metrics['stars']:,} Star"]
    if metrics.get("weekly_stars") is not None:
        metric_parts.append(f"本周 +{metrics['weekly_stars']:,}")
    metric_parts.append(f"{metrics['forks']:,} Fork")
    return [
        "<!-- github-project:start -->",
        f"## {index:02d} · {card['category_label']}",
        f"### {card['name']}",
        card["summary"],
        "**为什么这周火？**",
        edit["hot_reason"],
        edit["summary"],
        f"![项目官方资料](images/项目-{index:02d}.png)",
        f"<!-- github-metrics:{'|'.join(filter(None, metric_parts))} -->",
        f"> **一句话推荐**　{card['recommendation']}",
        *[f"- {value}" for value in card["highlights"]],
        f"**适合谁？**　{'、'.join(card['audience'])}",
        f"**上手条件：**　{card['difficulty']['note']}",
        f"**项目地址：** [{item['repo']}]({item['official_url']})",
        "<!-- github-project:end -->",
    ]
```

`build_article` uses top-level editorial evidence to generate a theme or multiple-route opening and an evidence-backed closing. It must never import `wechat-article-writer`.

- [ ] **Step 4: Dispatch only GitHub v2 to the new composer**

In `run.py`, use:

```python
if payload["content_type"] == "github-hot" and payload.get("schema_version") == 2:
    article, title, summary = github_hot_column.build_article(payload)
else:
    article, title, summary = rendering.build_article(payload)
```

Remove the old GitHub-v2 composer from `rendering.py`; leave daily-news and legacy GitHub v1 behavior unchanged.

- [ ] **Step 5: Run focused and full WeChat tests**

Run:

```powershell
python -m unittest discover -s wechat-content/tests -p test_github_hot_column.py -v
python -m unittest discover -s wechat-content/tests -v
```

Expected: all focused tests pass and all existing daily-news/shared tests remain green.

- [ ] **Step 6: Commit**

```powershell
git add wechat-content/scripts/github_hot_column.py wechat-content/scripts/run.py wechat-content/scripts/rendering.py wechat-content/tests/test_github_hot_column.py wechat-content/tests/fixtures/github-hot-five-projects-v2.json
git commit -m "feat: add github editorial card column"
```

## Task 5: Add deterministic theme families and project visual hierarchy

**Files:**

- Create: `wechat-content/scripts/github_hot_visuals.py`
- Modify: `wechat-content/assets/default-config.json`
- Modify: `wechat-content/scripts/run.py`
- Modify: `wechat-content/scripts/rendering.py`
- Modify: `wechat-content/tests/test_github_hot_column.py`

- [ ] **Step 1: Write failing theme and image tests**

Add:

```python
def test_theme_is_selected_from_content_and_is_repeatable(self):
    payload = load_fixture()
    first = github_hot_visuals.select_theme(payload, CONFIG["github_themes"])
    second = github_hot_visuals.select_theme(payload, CONFIG["github_themes"])
    self.assertEqual(first, second)
    self.assertEqual(first["family"], "ai_automation")


def test_image_priority_is_official_then_image2_then_local(self):
    official = choose_project_image(item(), approved_official(), valid_image2())
    generated = choose_project_image(item_without_approved(), None, valid_image2())
    local = choose_project_image(item_without_approved(), None, None)
    self.assertEqual(
        [official["mode"], generated["mode"], local["mode"]],
        ["official_verified", "live_image2", "local_project_visual"],
    )


def test_every_project_has_exactly_one_body_image(self):
    result = build_fixture_package()
    self.assertEqual(len(result["project_images"]), len(result["items"]))
    self.assertEqual(len({row["rank"] for row in result["project_images"]}), len(result["items"]))
```

- [ ] **Step 2: Run and verify RED**

Run:

```powershell
python -m unittest discover -s wechat-content/tests -p test_github_hot_column.py -v
```

Expected: FAIL because `github_hot_visuals` and theme configuration do not exist.

- [ ] **Step 3: Implement theme selection**

Add config:

```json
"github_themes": {
  "ai_automation": {"primary": "#102A43", "accent": "#1FB6C9", "background": "#F5FAFD"},
  "developer_tools": {"primary": "#102A43", "accent": "#1FA87A", "background": "#F5FBF8"},
  "creative_tools": {"primary": "#102A43", "accent": "#F28C45", "background": "#FFF9F4"},
  "systems_data": {"primary": "#243746", "accent": "#D99A2B", "background": "#FFFAF0"},
  "mixed_default": {"primary": "#102A43", "accent": "#2D9B72", "background": "#F7FBF9"}
}
```

Implement:

```python
def select_theme(payload, families):
    categories = [item.get("category", "") for item in payload["items"]]
    family = (
        "ai_automation" if sum("ai" in value for value in categories) >= 3
        else "developer_tools" if sum(value in {"developer-tools", "terminal", "infrastructure"} for value in categories) >= 3
        else "creative_tools" if sum(value in {"design", "audio", "video"} for value in categories) >= 3
        else "systems_data" if sum(value in {"security", "data", "system"} for value in categories) >= 3
        else "mixed_default"
    )
    return {"family": family, **families[family]}
```

Move the current official/Image2/local selection logic from `run.py` into `github_hot_visuals.py`. The local fallback mode is renamed `local_project_visual` and must render a visually finished project card rather than a blank placeholder.

- [ ] **Step 4: Record actual visual decisions**

Write `github_theme`, palette, per-project image mode, source, fallback reason, and audit-only license/use status into `render-manifest.json`. Do not expose those audit keys inside `wechat-content`.

- [ ] **Step 5: Run focused and full tests**

Run:

```powershell
python -m unittest discover -s wechat-content/tests -p test_github_hot_column.py -v
python -m unittest discover -s wechat-content/tests -v
```

Expected: all tests pass and daily-news weekday themes remain unchanged.

- [ ] **Step 6: Commit**

```powershell
git add wechat-content/scripts/github_hot_visuals.py wechat-content/assets/default-config.json wechat-content/scripts/run.py wechat-content/scripts/rendering.py wechat-content/tests/test_github_hot_column.py
git commit -m "feat: add adaptive github visual themes"
```

## Task 6: Build the external GitHub editorial audit panel

**Files:**

- Modify: `wechat-content/scripts/github_hot_column.py`
- Modify: `wechat-content/scripts/rendering.py`
- Modify: `wechat-content/tests/test_github_hot_column.py`

- [ ] **Step 1: Write failing audit-boundary tests**

Add:

```python
def test_full_audit_is_before_copy_region(self):
    page = build_html_from_fixture()
    before, copy = page.split('id="wechat-content"', 1)
    self.assertIn("本期主题证据", before)
    self.assertIn("未入选项目", before)
    self.assertIn("许可证核验", before)
    self.assertIn("图片审核", before)
    for phrase in ("license_status", "verified_at", "内部风险", "淘汰原因"):
        self.assertNotIn(phrase, copy)


def test_needs_review_can_copy_but_is_not_publish_ready(self):
    page, manifest = build_needs_review_fixture()
    self.assertIn("复制正文（发布前需核验）", page)
    self.assertTrue(manifest["copy_allowed"])
    self.assertFalse(manifest["publish_ready"])
```

- [ ] **Step 2: Run and verify RED**

Run:

```powershell
python -m unittest discover -s wechat-content/tests -p test_github_hot_column.py -v
```

Expected: FAIL because theme evidence and the complete audit model are not rendered.

- [ ] **Step 3: Implement the audit model and HTML**

Add:

```python
def build_audit_model(payload, project_images):
    return {
        "selection": payload["selection"],
        "theme": payload["editorial"],
        "projects": [
            {
                "repo": item["repo"],
                "verification": item["verification"],
                "heat": item["heat"],
                "image": project_images[index],
            }
            for index, item in enumerate(payload["items"])
        ],
        "rejected": [
            item for item in payload["candidates"] if not item.get("selected", False)
        ],
    }
```

Render this model in an `<aside data-role="github-editor-review-panel">` before the article. Escape every value with `html.escape`. Do not reuse the model when building reader Markdown.

- [ ] **Step 4: Run all WeChat tests**

Run:

```powershell
python -m unittest discover -s wechat-content/tests -v
```

Expected: all tests pass, including existing copy-button and daily-news review-panel tests.

- [ ] **Step 5: Commit**

```powershell
git add wechat-content/scripts/github_hot_column.py wechat-content/scripts/rendering.py wechat-content/tests/test_github_hot_column.py
git commit -m "feat: separate github editorial audit from reader copy"
```

## Task 7: Prevent template repetition and preserve graceful fallback

**Files:**

- Modify: `wechat-content/scripts/github_hot_column.py`
- Modify: `wechat-content/scripts/run.py`
- Modify: `wechat-content/tests/test_github_hot_column.py`

- [ ] **Step 1: Write failing repetition and fallback tests**

Add:

```python
def test_two_issues_do_not_reuse_identical_opening_or_closing(self):
    current = load_fixture()
    history = {
        "opening_hashes": [hash_text("old opening")],
        "closing_hashes": [hash_text("old closing")],
    }
    article = github_hot_column.build_article(current, history=history)[0]
    self.assertNotIn("old opening", article)
    self.assertNotIn("old closing", article)


def test_missing_common_theme_uses_multiple_routes_copy(self):
    payload = load_unrelated_fixture()
    article, title, _ = github_hot_column.build_article(payload)
    self.assertIn("几条不同路线", article)
    self.assertNotIn("共同趋势是", article)
```

- [ ] **Step 2: Run and verify RED**

Run:

```powershell
python -m unittest discover -s wechat-content/tests -p test_github_hot_column.py -v
```

Expected: FAIL because history-aware variant selection is absent.

- [ ] **Step 3: Implement deterministic variant selection**

Add:

```python
import hashlib


def hash_text(value):
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def choose_variant(candidates, rejected_hashes):
    for value in candidates:
        if hash_text(value) not in set(rejected_hashes):
            return value
    return candidates[-1]
```

Generate at least three evidence-equivalent opening and closing candidates from the structured editorial material, then choose the first hash not present in recent history. Persist only hashes and package IDs, not reader data. If all candidates repeat, use the final neutral variant.

- [ ] **Step 4: Run all WeChat tests**

Run:

```powershell
python -m unittest discover -s wechat-content/tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add wechat-content/scripts/github_hot_column.py wechat-content/scripts/run.py wechat-content/tests/test_github_hot_column.py
git commit -m "feat: vary github openings and closings by issue"
```

## Task 8: Update self-contained Skill documentation

**Files:**

- Modify: `github-hot-research/SKILL.md`
- Modify: `github-hot-research/README.md`
- Modify: `github-hot-research/references/content-package-v2.md`
- Modify: `github-hot-research/references/sources-and-risks.md`
- Modify: `wechat-content/SKILL.md`
- Modify: `wechat-content/references/github-hot.md`
- Modify: `wechat-content/references/image2-workflow.md`
- Test: `github-hot-research/tests/test_skill.py`
- Test: `wechat-content/tests/test_skill.py`

- [ ] **Step 1: Add failing documentation assertions**

Require the documentation to contain:

```python
for phrase in (
    "连续 7 天",
    "本周热度证据",
    "新爆款",
    "成熟项目最多 2 个",
    "为什么这周火",
):
    self.assertIn(phrase, research_docs)

for phrase in (
    "编辑卡片式",
    "动态开头",
    "动态结尾",
    "品牌稳定、主题半动态",
    "不依赖 wechat-article-writer",
):
    self.assertIn(phrase, wechat_docs)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m unittest discover -s github-hot-research/tests -v
python -m unittest discover -s wechat-content/tests -v
```

Expected: documentation assertions fail before the references are updated.

- [ ] **Step 3: Update documentation with exact runtime behavior**

Document:

- seven-day heat evidence and mature-project cap;
- evidence-backed editorial fields;
- dynamic title/opening/closing and no-common-theme fallback;
- approved reader project order;
- reader/audit separation;
- deterministic adaptive palettes;
- official/Image2/local image hierarchy;
- self-contained operation without `wechat-article-writer`;
- local audit-package-only boundary.

- [ ] **Step 4: Run both suites**

Run:

```powershell
python -m unittest discover -s github-hot-research/tests -v
python -m unittest discover -s wechat-content/tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add github-hot-research/SKILL.md github-hot-research/README.md github-hot-research/references github-hot-research/tests/test_skill.py wechat-content/SKILL.md wechat-content/references wechat-content/tests/test_skill.py
git commit -m "docs: document github editorial production workflow"
```

## Task 9: Full visual acceptance, regression, and Skill validation

**Files:**

- Test: `github-hot-research/tests/`
- Test: `wechat-content/tests/`
- Verify: `github-hot-research/`
- Verify: `wechat-content/`
- Generate from: `wechat-content/tests/fixtures/github-hot-five-projects-v2.json`

- [ ] **Step 1: Run the complete research suite**

Run:

```powershell
python -m unittest discover -s github-hot-research/tests -v
```

Expected: every research and editorial test passes.

- [ ] **Step 2: Run the complete WeChat suite**

Run:

```powershell
python -m unittest discover -s wechat-content/tests -v
```

Expected: every GitHub, shared, and daily-news regression test passes.

- [ ] **Step 3: Run both Skill validators**

Run with the workspace Python and local PyYAML path:

```powershell
$py='C:\Users\11046\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$validator='E:\codex-config\skills\.system\skill-creator\scripts\quick_validate.py'
$yaml='E:\mm\wxgzh\.validation-tools\pyyaml'
& $py -X utf8 -c "import sys,runpy; sys.path.insert(0,r'$yaml'); sys.argv=[r'$validator',r'E:\mm\wxgzh\skills-repo\github-hot-research']; runpy.run_path(r'$validator',run_name='__main__')"
& $py -X utf8 -c "import sys,runpy; sys.path.insert(0,r'$yaml'); sys.argv=[r'$validator',r'E:\mm\wxgzh\skills-repo\wechat-content']; runpy.run_path(r'$validator',run_name='__main__')"
```

Expected: `Skill is valid!` twice.

- [ ] **Step 4: Run syntax and diff checks**

Run:

```powershell
python -X utf8 -c "from pathlib import Path; files=list(Path('github-hot-research/scripts').glob('*.py'))+list(Path('wechat-content/scripts').glob('*.py')); [compile(p.read_text(encoding='utf-8'),str(p),'exec') for p in files]; print('Python syntax OK')"
git diff --check
git status --short
```

Expected: `Python syntax OK`, no diff-check errors, and only intended source/test/doc changes.

- [ ] **Step 5: Generate the five-project visual audit package**

Run:

```powershell
python wechat-content/scripts/run.py all `
  --input wechat-content/tests/fixtures/github-hot-five-projects-v2.json `
  --output-root E:\mm\test-skill\news\outputs
```

Expected: a local `微信版.html`, `公众号成稿.md`, covers, overview, five project images, ending image, audit report, and `render-manifest.json`. The command must not upload or publish anything.

- [ ] **Step 6: Perform manual visual checks**

Confirm:

- the title describes this fixture rather than package mechanics;
- the opening uses fixture evidence and creates reading motivation;
- all five projects follow the approved order and have comfortable spacing;
- no license/audit burden appears in the reader copy;
- images, captions, palette, data badges, highlights, and address are readable on mobile;
- the closing reflects the fixture and is not a generic invitation;
- copying `wechat-content` into the WeChat editor retains inline styles and images;
- the external audit panel contains all verification and image provenance.

- [ ] **Step 7: Commit final verification-only adjustments**

If manual review requires a bounded polish change, first add a failing regression test, implement the minimal fix, rerun Tasks 9.1—9.4, then commit:

```powershell
git add github-hot-research wechat-content
git commit -m "fix: polish github hot visual acceptance"
```

If no adjustment is required, do not create an empty commit.

- [ ] **Step 8: Final repository audit**

Run:

```powershell
git log --oneline -10
git status --short
git diff --check
```

Expected: implementation commits are present, the worktree is clean except for explicitly preserved user files, and no push, upload, or publication occurred.
