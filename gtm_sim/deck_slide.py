"""Build the "Trained in simulation" results slide in the RelayGTM deck's style.

Reads results/*.json and harbor/jobs, writes ppt/slides/slide6.xml into an
unpacked copy of the deck (slide added beforehand with add_slide.py).

    python -m gtm_sim.deck_slide <unpacked_dir>/ppt/slides/slide6.xml --trained grpo
"""

import argparse
import json
import pathlib
from xml.sax.saxutils import escape

from .dashboard_data import gtmbench, harbor_stats

EMU = 914400
NAVY, PANEL, LINE = "0B1220", "131C2E", "26314A"
INDIGO, WHITE, BODY, MUTED = "6366F1", "FFFFFF", "CBD5E1", "94A3B8"
GOOD, BAD = "34D399", "F87171"

_id = [10]


def nid():
    _id[0] += 1
    return _id[0]


def text_box(x, y, w, h, runs, size=1400, color=BODY, bold=False, align="l", anchor="t"):
    """runs: list of paragraphs, each a str or list of (text, {color,bold,size})."""
    paras = []
    for p in runs:
        segs = [(p, {})] if isinstance(p, str) else p
        rs = "".join(
            f'<a:r><a:rPr lang="en-US" sz="{o.get("size", size)}" b="{1 if o.get("bold", bold) else 0}" dirty="0">'
            f'<a:solidFill><a:srgbClr val="{o.get("color", color)}"/></a:solidFill></a:rPr>'
            f"<a:t>{escape(t)}</a:t></a:r>" for t, o in segs)
        paras.append(f'<a:p><a:pPr algn="{align}"><a:spcAft><a:spcPts val="600"/></a:spcAft></a:pPr>{rs}</a:p>')
    i = nid()
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{i}" name="Text {i}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{int(x*EMU)}" y="{int(y*EMU)}"/><a:ext cx="{int(w*EMU)}" cy="{int(h*EMU)}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="{anchor}"><a:noAutofit/></a:bodyPr>'
            f'<a:lstStyle/>{"".join(paras)}</p:txBody></p:sp>')


def card(x, y, w, h):
    i = nid()
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{i}" name="Card {i}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{int(x*EMU)}" y="{int(y*EMU)}"/><a:ext cx="{int(w*EMU)}" cy="{int(h*EMU)}"/></a:xfrm>'
            f'<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 6000"/></a:avLst></a:prstGeom>'
            f'<a:solidFill><a:srgbClr val="{PANEL}"/></a:solidFill><a:ln w="9525"><a:solidFill><a:srgbClr val="{LINE}"/></a:solidFill></a:ln>'
            f'</p:spPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr lang="en-US"/></a:p></p:txBody></p:sp>')


def table(x, y, colw, rows, header, row_h=0.42):
    """rows: list of lists of (text, color, bold). Drawn as aligned text boxes for exact control."""
    out, cx = [], x
    for j, (htext, w) in enumerate(zip(header, colw)):
        out.append(text_box(cx, y, w, 0.3, [htext], size=1100, color=MUTED, bold=True, align="l" if j == 0 else "r"))
        cx += w
    for i, row in enumerate(rows):
        cx, ry = x, y + 0.38 + i * row_h
        for j, ((t, c, b), w) in enumerate(zip(row, colw)):
            out.append(text_box(cx, ry, w, row_h, [t], size=1500, color=c, bold=b, align="l" if j == 0 else "r"))
            cx += w
    return "".join(out)


def pct(v):
    return f"{v:.0%}"


def delta(a, b, fmt, better_up=True):
    d = b - a
    if fmt == "pct":  # compare the rounded figures the slide shows, so "8% -> 10%" reads +2 pts
        d = (round(b * 100) - round(a * 100)) / 100
    good = (d > 0) == better_up
    if fmt == "pct":
        s = f"{'+' if d > 0 else '−'}{abs(d) * 100:.0f} pts"
    elif fmt == "rel":
        s = f"{'+' if d > 0 else '−'}{abs(d) / a:.0%}" if a else "—"
    else:
        s = f"{'+' if d > 0 else '−'}{abs(d):.0f}"
    return s, (GOOD if good else BAD) if d else MUTED


def sponsors_xml(page: str, cost: float) -> str:
    """The "Built with" slide: sponsor cards for Tenki and Band, then a row of open-source credits."""
    shapes = [
        text_box(0.7, 0.5, 12.0, 0.4, ["BUILT WITH"], size=1400, color=INDIGO, bold=True),
        text_box(0.7, 1.0, 12.0, 0.95, ["Thanks to the tools that made it possible."], size=3200, color=WHITE, bold=True),
    ]
    for x, name, desc in [
        (0.7, "Tenki", f"Every training reward was scored in Tenki sandboxes, and the Harbor benchmark gave each "
                       f"prospect its own Tenki VM: 303 sandboxes for ${cost:.2f}."),
        (6.8, "Band", "We built the trained agent as a Band agent: mention @gtm-gym in a room, it drafts the "
                      "outreach, and a person approves or rejects it."),
    ]:
        shapes += [card(x, 2.05, 5.85, 2.1),
                   text_box(x + 0.3, 2.3, 5.3, 0.7, [name], size=4000, color=WHITE, bold=True),
                   text_box(x + 0.3, 3.15, 5.3, 1.2, [desc], size=1600, color=BODY)]
    shapes.append(text_box(0.7, 4.6, 6.0, 0.3, ["ALSO BUILT ON"], size=1200, color=MUTED, bold=True))
    x, y = 0.7, 5.0
    for name in ["Qwen3", "Hugging Face TRL", "PEFT", "PyTorch", "Harbor", "GTM-Bench by Blackpearl", "Claude"]:
        w = 0.45 + 0.09 * len(name)
        if x + w > 12.65:
            x, y = 0.7, y + 0.65
        shapes += [card(x, y, w, 0.5), text_box(x, y, w, 0.5, [name], size=1400, color=WHITE, bold=True,
                                                align="ctr", anchor="ctr")]
        x += w + 0.18
    shapes += [text_box(0.7, 7.05, 8.0, 0.3, ["RelayGTM  •  Demo build — fictional data only, no real outreach sent"],
                        size=1100, color=MUTED),
               text_box(12.13, 7.05, 0.5, 0.3, [page], size=1100, color=MUTED, align="r")]
    return slide_xml(shapes)


def slide_xml(shapes) -> str:
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{NAVY}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
            '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
            + "".join(shapes) +
            '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--trained", default="grpo", help="results/<name>.json of the presented model")
    ap.add_argument("--harbor-trained", default="grpo-run3")
    ap.add_argument("--gtmbench-trained", default="grpo-run3")
    ap.add_argument("--cost", type=float, required=True, help="total Tenki spend in USD")
    ap.add_argument("--page", default="6")
    ap.add_argument("--sponsors", action="store_true", help="write the Built with slide instead")
    args = ap.parse_args()
    if args.sponsors:
        pathlib.Path(args.out).write_text(sponsors_xml(args.page, args.cost))
        print(f"wrote {args.out}: sponsors slide")
        return

    b = json.loads(pathlib.Path("results/baseline.json").read_text())
    t = json.loads(pathlib.Path(f"results/{args.trained}.json").read_text())
    hb_b, hb_t, hb_o = harbor_stats("base"), harbor_stats(args.harbor_trained), harbor_stats("oracle")
    gb_b, gb_t = gtmbench("base"), gtmbench(args.gtmbench_trained)
    feat = lambda r, k: r["message_feature_rates"].get(k, 0)

    main_rows = []
    for label, a, c, fmt, up in [
        ("Expected meetings booked", b["expected_meetings"], t["expected_meetings"], "rel", True),
        ("Wasted sends to bad-fit leads", b["wasted_sends_on_bad_fit"], t["wasted_sends_on_bad_fit"], "int", False),
        ("Qualification accuracy", b["qualification_accuracy"], t["qualification_accuracy"], "pct", True),
        ("Reply rate on good-fit leads", b["reply_rate_on_good_fit"], t["reply_rate_on_good_fit"], "pct", True),
        ("Uses the prospect's buying signal", feat(b, "uses_signal"), feat(t, "uses_signal"), "pct", True),
        ("Messages with made-up figures", feat(b, "unsupported_claim"), feat(t, "unsupported_claim"), "pct", False),
    ]:
        show = (lambda v: f"{v:.1f}") if fmt == "rel" else (lambda v: f"{v:.0f}") if fmt == "int" else pct
        d, col = delta(a, c, fmt, up)
        main_rows.append([(label, BODY, False), (show(a), MUTED, False), (show(c), WHITE, True), (d, col, True)])

    bench_rows = []
    if hb_b and hb_t and hb_o:
        bench_rows.append([("Harbor · mean reward", BODY, False), (f"{hb_b['reward']:.2f}", MUTED, False),
                           (f"{hb_t['reward']:.2f}", WHITE, True), (f"{hb_o['reward']:.2f}", MUTED, False)])
        bench_rows.append([("Harbor · qualification", BODY, False), (pct(hb_b["qual"]), MUTED, False),
                           (pct(hb_t["qual"]), WHITE, True), (pct(hb_o["qual"]), MUTED, False)])
    if gb_b and gb_t:
        bench_rows.append([("GTM-Bench ICP (1–5)", BODY, False), (f"{gb_b:.2f}", MUTED, False),
                           (f"{gb_t:.2f}", WHITE, True), ("5.00", MUTED, False)])

    shapes = [
        text_box(0.7, 0.5, 12.0, 0.4, ["GTM GYM RESULTS"], size=1400, color=INDIGO, bold=True),
        text_box(0.7, 1.0, 12.0, 0.95, [f"Trained in our simulator, a 0.6B agent books "
                                         f"{t['expected_meetings'] / b['expected_meetings'] - 1:.0%} more meetings."],
                 size=3200, color=WHITE, bold=True),
        card(0.7, 2.05, 6.95, 3.7),
        text_box(0.95, 2.2, 6.5, 0.35, ["Held-out eval · 200 unseen prospects"], size=1300, color=WHITE, bold=True),
        table(0.95, 2.6, [3.4, 0.95, 0.95, 1.2], main_rows, ["", "Base", "Trained", "Change"]),
        card(7.85, 2.05, 4.85, 3.7),
        text_box(8.1, 2.2, 4.4, 0.35, ["External checks"], size=1300, color=WHITE, bold=True),
        table(8.1, 2.6, [2.25, 0.7, 0.8, 0.7], bench_rows, ["", "Base", "Trained", "Ceiling"]),
        text_box(8.1, 4.4, 4.4, 1.3, [
            "Harbor: 30 held-out prospects as Harbor tasks, each graded in its own Tenki VM; ceiling = rule-based oracle.",
            "GTM-Bench: 24 real seller prompts (Blackpearl), scored with its ICP judge rubric. A transfer test, not a leaderboard entry."],
                 size=1050, color=MUTED),
        text_box(0.7, 5.95, 12.0, 0.45, [
            "Qwen3-0.6B + LoRA, GRPO (TRL) on a MacBook M4 Pro; simulated buyers with hidden persona preferences score every draft "
            f"inside Tenki sandboxes. Total Tenki spend ${args.cost:.2f}. Fictional prospects only; no real outreach sent."], size=1100, color=MUTED),
        text_box(0.7, 7.05, 8.0, 0.3, ["RelayGTM  •  Demo build — fictional data only, no real outreach sent"],
                 size=1100, color=MUTED),
        text_box(12.13, 7.05, 0.5, 0.3, [args.page], size=1100, color=MUTED, align="r"),
    ]
    xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
           'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
           f'<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{NAVY}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
           '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
           + "".join(shapes) +
           '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')
    pathlib.Path(args.out).write_text(xml)
    print(f"wrote {args.out}: {len(main_rows)} eval rows, {len(bench_rows)} benchmark rows")


if __name__ == "__main__":
    main()
