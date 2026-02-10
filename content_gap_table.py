import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


THEME_LABELS = {
    "transport": "commute & connectivity",
    "traffic_parking": "traffic/parking realities",
    "cost": "cost considerations",
    "lifestyle": "lifestyle & vibe",
    "daily_life": "day-to-day convenience",
    "safety": "safety angle",
    "decision_frame": "decision framing",
    "comparison": "comparison context",
}


@dataclass(frozen=True)
class ContentGapDeps:
    clean: Callable[[str], str]
    norm_header: Callable[[str], str]
    format_gap_list: Callable[[List[str], int], str]
    source_link: Callable[[str], str]
    section_nodes: Callable[..., List[dict]]
    find_best_bayut_match: Callable[[str, List[dict], float], Optional[dict]]
    missing_faqs_row: Callable[[List[dict], Any, List[dict], Any, str], Optional[dict]]
    dedupe_rows: Callable[[List[dict]], List[dict]]
    coverage_corpus: Callable[[Any, List[dict]], str]
    topic_is_covered: Callable[..., bool]
    is_low_signal_subtopic: Callable[[str], bool]
    subtopic_covered_in_text: Callable[[str, str], bool]
    topic_coverage_ratio: Callable[[str, str], float]
    header_core_tokens: Callable[[str], List[str]]
    high_precision_mode: bool
    missing_header_min_text_coverage: float
    missing_subtopic_min_text_coverage: float


def theme_flags(text: str) -> set:
    t = (text or "").lower()
    flags = set()

    def has_any(words: List[str]) -> bool:
        return any(w in t for w in words)

    if has_any(["metro", "public transport", "commute", "connectivity", "access", "highway", "roads", "bus", "train"]):
        flags.add("transport")
    if has_any(["parking", "traffic", "congestion", "rush hour", "gridlock"]):
        flags.add("traffic_parking")
    if has_any(["cost", "price", "pricing", "expensive", "afford", "budget", "rent", "fees", "charges"]):
        flags.add("cost")
    if has_any(["restaurants", "cafes", "nightlife", "vibe", "atmosphere", "social", "entertainment"]):
        flags.add("lifestyle")
    if has_any(["schools", "nursery", "kids", "family", "clinic", "hospital", "supermarket", "groceries", "pharmacy"]):
        flags.add("daily_life")
    if has_any(["safe", "safety", "security", "crime"]):
        flags.add("safety")
    if has_any(["pros", "cons", "advantages", "disadvantages", "weigh", "consider", "should you", "worth it"]):
        flags.add("decision_frame")
    if has_any(["compare", "comparison", "vs ", "versus", "alternative", "similar to"]):
        flags.add("comparison")

    return flags


def _summarize_missing_section_action(
    deps: ContentGapDeps, subheaders: Optional[List[str]], comp_content: str
) -> str:
    themes = list(theme_flags(comp_content))
    picks = [THEME_LABELS.get(x, x) for x in themes]
    parts = []
    if subheaders:
        sub_list = deps.format_gap_list(subheaders, limit=6)
        if sub_list:
            parts.append(f"Missing subtopics: {sub_list}.")
    if picks:
        theme_list = deps.format_gap_list(picks, limit=4)
        if theme_list:
            parts.append(f"Missing coverage on: {theme_list}.")
    if not parts:
        parts.append("Missing this section.")
    return " ".join(parts)


def _summarize_content_gap_action(deps: ContentGapDeps, comp_content: str, bayut_content: str) -> str:
    comp_flags = theme_flags(comp_content)
    bayut_flags = theme_flags(bayut_content)
    missing = list(comp_flags - bayut_flags)
    missing_human = [THEME_LABELS.get(x, x) for x in missing]
    missing_list = deps.format_gap_list(missing_human, limit=4)
    if missing_list:
        return "Missing depth on: " + missing_list + "."
    return "Missing depth and practical specifics in this section."


def build_content_gap_rows_header_first(
    bayut_nodes: List[dict],
    bayut_fr: Any,
    comp_nodes: List[dict],
    comp_fr: Any,
    comp_url: str,
    deps: ContentGapDeps,
    max_missing_headers: Optional[int] = None,
) -> List[dict]:
    rows_map: Dict[str, dict] = {}
    source = deps.source_link(comp_url)

    def add_row(header: str, parts: List[str]):
        if not header or not parts:
            return
        key = deps.norm_header(header) + "||" + deps.norm_header(re.sub(r"<[^>]+>", "", source))
        if key not in rows_map:
            rows_map[key] = {"Headers": header, "DescriptionParts": [], "Source": source}
        for p in parts:
            p = deps.clean(p)
            if not p:
                continue
            if not p.endswith("."):
                p = p + "."
            if p not in rows_map[key]["DescriptionParts"]:
                rows_map[key]["DescriptionParts"].append(p)

    def children_map(child_sections: List[dict]) -> Dict[str, List[dict]]:
        cmap: Dict[str, List[dict]] = {}
        for sec in child_sections:
            parent = sec.get("parent_h2") or ""
            pk = deps.norm_header(parent)
            if not pk:
                continue
            cmap.setdefault(pk, []).append(sec)
        return cmap

    def child_headers(cmap: Dict[str, List[dict]], parent_header: str) -> List[str]:
        pk = deps.norm_header(parent_header)
        return [c.get("header", "") for c in cmap.get(pk, [])]

    def combined_h2_content(h2_header: str, h2_list: List[dict], cmap: Dict[str, List[dict]]) -> str:
        pk = deps.norm_header(h2_header)
        h2_content = ""
        for h2 in h2_list:
            if deps.norm_header(h2.get("header", "")) == pk:
                h2_content = h2.get("content", "")
                break
        child_content = " ".join(c.get("content", "") for c in cmap.get(pk, []))
        return deps.clean(" ".join([h2_content, child_content]))

    def missing_children(
        comp_children: List[str],
        bayut_children: List[str],
        bayut_text: str,
        bayut_global_text: str,
    ) -> List[str]:
        missing = []
        child_section_objs = [{"header": h} for h in bayut_children if deps.clean(h)]
        for ch in comp_children:
            if deps.high_precision_mode and deps.is_low_signal_subtopic(ch):
                continue
            if deps.topic_is_covered(
                ch,
                child_section_objs,
                bayut_text,
                min_header_score=0.73,
                min_text_coverage=deps.missing_subtopic_min_text_coverage,
            ):
                continue
            if deps.subtopic_covered_in_text(ch, bayut_text):
                continue
            if deps.high_precision_mode:
                cov_all = deps.topic_coverage_ratio(ch, bayut_global_text)
                toks = deps.header_core_tokens(ch)
                if toks:
                    if len(toks) <= 2 and cov_all >= 1.0:
                        continue
                    if len(toks) > 2 and cov_all >= deps.missing_subtopic_min_text_coverage:
                        continue
            missing.append(ch)
        return missing

    def depth_gap_summary(comp_text: str, bayut_text: str) -> str:
        c_txt = deps.clean(comp_text or "")
        b_txt = deps.clean(bayut_text or "")
        if len(c_txt) < 140:
            return ""
        if len(c_txt) < (1.30 * max(len(b_txt), 1)):
            return ""
        comp_flags = theme_flags(c_txt)
        bayut_flags = theme_flags(b_txt)
        if len(comp_flags - bayut_flags) < 1 and len(c_txt) < 650:
            return ""
        return _summarize_content_gap_action(deps, c_txt, b_txt)

    bayut_secs = deps.section_nodes(bayut_nodes, levels=(2, 3, 4))
    comp_secs = deps.section_nodes(comp_nodes, levels=(2, 3, 4))

    bayut_h2 = [s for s in bayut_secs if s["level"] == 2]
    bayut_child_sections = [s for s in bayut_secs if s["level"] >= 3]
    comp_h2 = [s for s in comp_secs if s["level"] == 2]
    comp_children_all = [s for s in comp_secs if s["level"] >= 3]

    bayut_children_map = children_map(bayut_child_sections)
    comp_children_map = children_map(comp_children_all)
    bayut_global_text = deps.coverage_corpus(bayut_fr, bayut_nodes)

    for cs in comp_h2:
        comp_header = cs.get("header", "")
        comp_children = child_headers(comp_children_map, comp_header)
        comp_text = combined_h2_content(comp_header, comp_h2, comp_children_map) or cs.get("content", "")

        m = deps.find_best_bayut_match(comp_header, bayut_h2, min_score=0.73)
        if not m:
            if deps.high_precision_mode and deps.topic_is_covered(
                comp_header,
                bayut_h2 + bayut_child_sections,
                bayut_global_text,
                min_header_score=0.73,
                min_text_coverage=deps.missing_header_min_text_coverage,
            ):
                continue
            desc = _summarize_missing_section_action(deps, comp_children, comp_text)
            add_row(comp_header, [desc])
            continue

        bayut_header = m["bayut_section"]["header"]
        bayut_child_headers = child_headers(bayut_children_map, bayut_header)
        bayut_text = combined_h2_content(bayut_header, bayut_h2, bayut_children_map)
        missing_sub = missing_children(comp_children, bayut_child_headers, bayut_text, bayut_global_text)

        parts = []
        if missing_sub:
            sub_list = deps.format_gap_list(missing_sub, limit=6)
            if sub_list:
                parts.append(f"Missing subtopics: {sub_list}.")

        depth_note = depth_gap_summary(comp_text, bayut_text)
        if depth_note:
            parts.append(depth_note)

        if parts:
            add_row(comp_header, parts)

    comp_h2_norms = {deps.norm_header(h.get("header", "")) for h in comp_h2}
    for cs in comp_children_all:
        parent = cs.get("parent_h2") or ""
        if parent and deps.norm_header(parent) in comp_h2_norms:
            continue
        m = deps.find_best_bayut_match(cs["header"], bayut_child_sections + bayut_h2, min_score=0.73)
        if m:
            continue
        if deps.high_precision_mode and deps.topic_is_covered(
            cs["header"],
            bayut_child_sections + bayut_h2,
            bayut_global_text,
            min_header_score=0.73,
            min_text_coverage=deps.missing_subtopic_min_text_coverage,
        ):
            continue
        desc = _summarize_missing_section_action(deps, None, cs.get("content", ""))
        add_row(cs["header"], [desc])

    rows = []
    for r in rows_map.values():
        desc = " ".join(r.get("DescriptionParts", [])).strip()
        rows.append({"Headers": r.get("Headers", ""), "Description": desc, "Source": r.get("Source", "")})

    if max_missing_headers and len(rows) > max_missing_headers:
        rows = rows[:max_missing_headers]

    faq_row = deps.missing_faqs_row(bayut_nodes, bayut_fr, comp_nodes, comp_fr, comp_url)
    if faq_row:
        rows.append(faq_row)

    return deps.dedupe_rows(rows)
