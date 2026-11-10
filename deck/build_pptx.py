# Databricks notebook source
# Build "Pinecrest Care Coordinator" as an editable PPTX (native text, shapes and charts; imports
# cleanly into Google Slides). Every number comes from a file in evidence/ — see the notes on
# each slide for the source. Runs on serverless; output goes to a UC volume.

# COMMAND ----------

# MAGIC %pip install -q python-pptx==1.0.2

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import shutil

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

OUT = "/Volumes/users/narasimha_kamathardi/pinecrest_artifacts/Pinecrest Care Coordinator.pptx"

INK = RGBColor(0x14, 0x24, 0x2B)      # near-black navy for text
NAVY = RGBColor(0x1B, 0x2F, 0x38)
PAPER = RGBColor(0xFA, 0xF9, 0xF6)
RED = RGBColor(0xE8, 0x3A, 0x22)
GREY = RGBColor(0x6E, 0x77, 0x7C)
RULE = RGBColor(0xDD, 0xDA, 0xD3)
PALE = RGBColor(0xC9, 0xCF, 0xD2)     # de-emphasised bars
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Arial"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
LM = Inches(0.85)                      # left margin
CW = Inches(13.333 - 1.7)              # content width


def T(slide, x, y, w, h, paras, size=16, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.1):
    """Text box. paras: str | list[str | list[(text, overrides)]]."""
    tf = slide.shapes.add_textbox(x, y, w, h).text_frame
    tf.word_wrap, tf.vertical_anchor = True, anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, para in enumerate(paras if isinstance(paras, list) else [paras]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment, p.line_spacing = align, spacing
        for txt, o in ([(para, {})] if isinstance(para, str) else para):
            r = p.add_run()
            r.text = txt
            f = r.font
            f.name, f.size, f.bold, f.italic = FONT, Pt(o.get("size", size)), o.get("bold", bold), o.get("italic", False)
            f.color.rgb = o.get("color", color)
        p.space_after = Pt(o.get("after", 8)) if isinstance(para, list) else Pt(8)
    return tf


def rect(slide, x, y, w, h, fill, line=None):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = fill
    if line:
        s.line.color.rgb, s.line.width = line, Pt(0.75)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    return s


def hline(slide, x, y, w, color=RULE, weight=0.75):
    ln = slide.shapes.add_connector(1, x, y, x + w, y)
    ln.line.color.rgb, ln.line.width = color, Pt(weight)


def page(slide, n, dark=False):
    """Slide chrome: section label top-left, page number bottom-right, thin rule."""
    c = RGBColor(0x8C, 0x9A, 0xA1) if dark else GREY
    T(slide, LM, Inches(7.0), Inches(6), Inches(0.25), "Pinecrest Care Coordinator", 10, c)
    T(slide, Inches(11.5), Inches(7.0), Inches(0.98), Inches(0.25), f"{n:02d}", 10, c, align=PP_ALIGN.RIGHT)


def heading(slide, label, title, dark=False):
    T(slide, LM, Inches(0.55), CW, Inches(0.3), label.upper(), 11, RED, True)
    T(slide, LM, Inches(0.85), Inches(11.0), Inches(1.3), title, 30, WHITE if dark else INK, True, spacing=1.05)


def bar_chart(slide, x, y, w, h, cats, series, colors, horizontal=True, pct=True, legend=False, max_v=None, gap=60):
    data = CategoryChartData()
    data.categories = cats
    for name, vals in series:
        data.add_series(name, vals)
    kind = XL_CHART_TYPE.BAR_CLUSTERED if horizontal else XL_CHART_TYPE.COLUMN_CLUSTERED
    ch = slide.shapes.add_chart(kind, x, y, w, h, data).chart
    ch.font.name, ch.font.size, ch.font.color.rgb = FONT, Pt(12), INK
    ch.has_legend = legend
    if legend:
        ch.legend.position, ch.legend.include_in_layout = XL_LEGEND_POSITION.TOP, False
        ch.legend.font.size = Pt(12)
    va, ca = ch.value_axis, ch.category_axis
    va.visible, va.has_major_gridlines = False, False
    va.minimum_scale = 0
    if max_v:
        va.maximum_scale = max_v
    ca.format.line.color.rgb = RULE
    ca.tick_labels.font.size = Pt(12)
    if horizontal:
        ca.reverse_order = True
    plot = ch.plots[0]
    plot.gap_width, plot.overlap = gap, (-10 if len(series) > 1 else 0)
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format, dl.number_format_is_linked = ('0.0"%"' if pct else "0"), False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size, dl.font.bold = Pt(12), True
    for si, s in enumerate(plot.series):
        s.format.fill.solid()
        cs = colors[si]
        if isinstance(cs, list):     # per-point colours (highlight)
            s.format.fill.fore_color.rgb = cs[0]
            for pi, c in enumerate(cs):
                pt = s.points[pi]
                pt.format.fill.solid(); pt.format.fill.fore_color.rgb = c
        else:
            s.format.fill.fore_color.rgb = cs
    return ch


def notes(slide, txt):
    slide.notes_slide.notes_text_frame.text = txt


# ── 1. Title ──────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, prs.slide_width, prs.slide_height, NAVY)
rect(s, LM, Inches(1.0), Inches(0.5), Inches(0.06), RED)
T(s, LM, Inches(1.25), Inches(8), Inches(0.3), "PINECREST HEALTH  ·  QUALITY & CARE MANAGEMENT", 11, RGBColor(0xAF, 0xBC, 0xC2), True)
T(s, LM, Inches(2.6), Inches(10.5), Inches(2.0), "Calling the right patients first", 50, WHITE, True, spacing=1.0)
T(s, LM, Inches(3.75), Inches(9.5), Inches(1.2),
  "A readmission worklist that ranks every discharge by predicted risk, explains why, and records what "
  "the care team did about it.", 19, RGBColor(0xC6, 0xD2, 0xD7), spacing=1.25)
hline(s, LM, Inches(6.2), CW, RGBColor(0x33, 0x4D, 0x58))
T(s, LM, Inches(6.4), Inches(7), Inches(0.3), "Narasimha Kamathardi  ·  November 2026", 12, RGBColor(0xAF, 0xBC, 0xC2))
T(s, Inches(6.5), Inches(6.4), Inches(5.98), Inches(0.3), "Pinecrest Health is fictional. All data is synthetic.", 12,
  RGBColor(0xAF, 0xBC, 0xC2), align=PP_ALIGN.RIGHT)
notes(s, "This is a working build on Databricks, not a concept. Pinecrest Health is a fictional three-hospital system "
         "and every record is synthetic, generated with a fixed seed so the results are reproducible.")

# ── 2. Who owns the problem ───────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK); rect(s, 0, 0, prs.slide_width, prs.slide_height, PAPER)
heading(s, "The problem", "One in seven patients comes back within 30 days. Three executives feel it differently.")
owners = [("Chief Quality Officer", "Sponsor", "Owns the 30-day readmission rate and the CMS HRRP penalty that follows it. "
           "Reports both to the board.", "14.7%", "readmission rate today"),
          ("CFO", "Funds it", "Carries the penalty as budget risk (up to 3% of Medicare reimbursement) and absorbs "
           "~$15K for every avoidable second stay.", "$15K", "per avoidable readmission"),
          ("VP of Care Management", "Runs it", "Has a fixed team of coordinators who can call a fraction of each day's "
           "discharges, and today work the list without a ranking.", "6,013", "discharges in the data")]
colw = Inches(3.65); gap = Inches(0.33)
for i, (role, tag, body, num, numlbl) in enumerate(owners):
    x = LM + i * (colw + gap)
    hline(s, x, Inches(2.45), colw, INK, 1.5)
    T(s, x, Inches(2.6), colw, Inches(0.3), tag.upper(), 10, RED, True)
    T(s, x, Inches(2.9), colw, Inches(0.5), role, 21, INK, True)
    T(s, x, Inches(3.45), colw, Inches(1.6), body, 14, GREY, spacing=1.3)
    T(s, x, Inches(5.05), colw, Inches(0.8), num, 40, INK, True)
    T(s, x, Inches(5.8), colw, Inches(0.3), numlbl, 12, GREY)
notes(s, "Naming the owners matters because each one measures success differently: the CQO on the rate and penalty, "
         "the CFO on avoided cost, the VP of Care Management on what the team can actually get through. "
         "Source for 14.7% and 6,013: evidence/07_deck_figures.md. $15K and 3% are industry figures, not from the data.")

# ── 3. Where readmissions come from ───────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK); rect(s, 0, 0, prs.slide_width, prs.slide_height, PAPER)
heading(s, "What the data says", "A missed follow-up visit is the gap the care team can close.")
T(s, LM, Inches(2.25), Inches(5.4), Inches(0.3), "30-day readmission rate by discharge disposition", 13, INK, True)
bar_chart(s, LM - Inches(0.1), Inches(2.55), Inches(5.6), Inches(2.9),
          ["Left against advice", "Skilled nursing", "Home health", "Home"], [("Readmitted", (26.2, 18.1, 13.4, 13.4))],
          [[RED, PALE, PALE, PALE]], max_v=32)
T(s, Inches(6.95), Inches(2.25), Inches(5.4), Inches(0.3), "…and by whether a follow-up visit was booked", 13, INK, True)
bar_chart(s, Inches(6.85), Inches(2.55), Inches(5.6), Inches(1.9),
          ["No follow-up booked", "Follow-up booked"], [("Readmitted", (19.2, 11.8))], [[RED, PALE]], max_v=32)
T(s, Inches(6.95), Inches(4.6), Inches(5.4), Inches(1.0),
  [[("2,324", {"bold": True}), (" discharges left without a follow-up visit. Their readmission rate is ", {}),
    ("1.6×", {"bold": True}), (" that of patients who had one booked.", {})]], 14, GREY, spacing=1.3)
hline(s, LM, Inches(5.9), CW)
T(s, LM, Inches(6.05), CW, Inches(0.6),
  "Disposition is decided at discharge. Booking the follow-up is something a coordinator can still do the next morning.",
  15, INK, True)
notes(s, "Two cuts of the raw outcomes, before any model. Left-against-advice patients are readmitted at 26%, twice the "
         "rate of those sent home. Patients without a follow-up are at 19% versus 12%. That second gap is actionable. "
         "Source: evidence/07_deck_figures.md.")

# ── 4. Today vs with the worklist ─────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK); rect(s, 0, 0, prs.slide_width, prs.slide_height, PAPER)
heading(s, "What changes for the coordinator", "Same team, same morning. A different first call.")
rows = [("Who to call first", "Alphabetical discharge list", "Ranked by predicted 30-day risk"),
        ("Why this patient", "Coordinator reads the chart", "Two-line explanation from the patient's own notes"),
        ("What to do", "Decided from experience", "Recommended action per patient, editable"),
        ("Record of the call", "Free text, if anything", "Approved action saved with approver and time")]
cx = [LM, LM + Inches(3.2), LM + Inches(7.4)]
T(s, cx[1], Inches(2.3), Inches(4), Inches(0.3), "TODAY", 11, GREY, True)
T(s, cx[2], Inches(2.3), Inches(4.2), Inches(0.3), "WITH THE WORKLIST", 11, RED, True)
for i, (a, b, c) in enumerate(rows):
    y = Inches(2.7) + i * Inches(0.95)
    hline(s, LM, y, CW)
    T(s, cx[0], y + Inches(0.22), Inches(3.0), Inches(0.5), a, 16, INK, True)
    T(s, cx[1], y + Inches(0.22), Inches(4.0), Inches(0.5), b, 16, GREY)
    T(s, cx[2], y + Inches(0.22), Inches(4.2), Inches(0.5), c, 16, INK)
hline(s, LM, Inches(2.7) + 4 * Inches(0.95), CW)
notes(s, "This is the workflow change in plain terms. Nothing here replaces the coordinator's judgment: the action is "
         "a suggestion they can edit, and nothing is written until they approve it.")

# ── 5. How it's built ─────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK); rect(s, 0, 0, prs.slide_width, prs.slide_height, PAPER)
heading(s, "How it's built", "Six Databricks stages over one dataset, each reading the previous stage's output.")
stages = [("Lakeflow", "Ingest + clean", "pc_bronze_* → pc_silver_* → pc_gold_*"),
          ("Unity Catalog", "Govern", "PHI tags, masks, lineage"),
          ("ML", "Predict", "pc_readmission_risk_model @champion"),
          ("Lakebase", "Serve", "pc_risk_worklist, care_actions"),
          ("Genie", "Ask", "Pinecrest Readmission Insights"),
          ("Databricks App", "Act", "pinecrest-care-coordinator")]
bw = Inches(1.78); bg = Inches(0.19)
for i, (name, verb, obj) in enumerate(stages):
    x = LM + i * (bw + bg); y = Inches(2.55)
    rect(s, x, y, bw, Inches(2.25), WHITE, RULE)
    rect(s, x, y, bw, Inches(0.06), RED)
    T(s, x + Inches(0.18), y + Inches(0.25), bw - Inches(0.3), Inches(0.3), f"{i + 1}  {verb.upper()}", 10, RED, True)
    T(s, x + Inches(0.18), y + Inches(0.55), bw - Inches(0.3), Inches(0.7), name, 17, INK, True)
    T(s, x + Inches(0.18), y + Inches(1.3), bw - Inches(0.3), Inches(0.9), obj, 11, GREY, spacing=1.25)
    if i < 5:
        T(s, x + bw - Inches(0.02), y + Inches(0.95), bg + Inches(0.04), Inches(0.3), "›", 20, RED, True, align=PP_ALIGN.CENTER)
T(s, LM, Inches(5.2), CW, Inches(1.3),
  [[("Raw files land in a Unity Catalog volume. ", {"bold": True, "color": INK}),
    ("The pipeline cleans them, the model scores the gold table, Lakebase serves the scores to the app in "
     "milliseconds, Genie answers questions on the same tables, and the coordinator's approval is written back "
     "to Lakebase. One permission model covers all of it.", {})]], 15, GREY, spacing=1.35)
notes(s, "Each box names the real object in the workspace, so this maps one-to-one to the repo folders 01 to 06. "
         "The integration point to stress: every stage consumes the previous stage's output; nothing is copied out.")

# ── 6. Data you can trust ─────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK); rect(s, 0, 0, prs.slide_width, prs.slide_height, PAPER)
heading(s, "Data quality and governance", "Bad rows stop at the pipeline. Patient identity stays masked.")
flow = [("6,038", "raw discharges ingested"), ("−25", "rejected: invalid length of stay"), ("6,013", "clean discharges in gold")]
for i, (n, l) in enumerate(flow):
    x = LM + i * Inches(2.0)
    T(s, x, Inches(2.4), Inches(1.9), Inches(0.7), n, 34, RED if n.startswith("−") else INK, True)
    T(s, x, Inches(3.1), Inches(1.8), Inches(0.6), l, 12, GREY, spacing=1.25)
T(s, LM, Inches(3.95), Inches(5.6), Inches(1.4),
  "The 25 bad rows were planted on purpose. A Lakeflow expectation caught exactly those 25, and the event log "
  "records it.", 14, GREY, spacing=1.35)
# masking illustration
mx = Inches(7.15)
T(s, mx, Inches(2.4), Inches(5.3), Inches(0.3), "SAME ROW, TWO READERS", 11, RED, True)
for j, (who, name, phone) in enumerate([("Care team", "Mateo Chen", "555-656-8462"), ("Everyone else", "***MASKED***", "***MASKED***")]):
    y = Inches(2.8) + j * Inches(0.75)
    rect(s, mx, y, Inches(5.3), Inches(0.62), WHITE, RULE)
    T(s, mx + Inches(0.2), y, Inches(1.6), Inches(0.62), who, 13, GREY, True, anchor=MSO_ANCHOR.MIDDLE)
    T(s, mx + Inches(1.85), y, Inches(1.7), Inches(0.62), "PC-00001", 13, INK, anchor=MSO_ANCHOR.MIDDLE)
    T(s, mx + Inches(3.0), y, Inches(2.2), Inches(0.62), f"{name}  ·  {phone}", 13, INK if j == 0 else RED, j == 1,
      anchor=MSO_ANCHOR.MIDDLE)
T(s, mx, Inches(4.45), Inches(5.3), Inches(1.2),
  "Name, phone and ZIP are tagged phi in Unity Catalog. A column mask returns the real value only to the care-team "
  "group. Lineage from raw file to scored table is captured automatically.", 14, GREY, spacing=1.35)
notes(s, "Left: the pipeline's data-quality expectation, with counts from evidence/01. Right: the mask function from "
         "evidence/02. The masked row illustrates what the function returns for a user outside the care-team group.")

# ── 7. The model ──────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK); rect(s, 0, 0, prs.slide_width, prs.slide_height, PAPER)
heading(s, "The model", "Half of the High-risk group was readmitted. One in seventeen of the Low group was.")
T(s, LM, Inches(2.25), Inches(7), Inches(0.3), "30-day readmission rate by risk tier: predicted vs actual", 13, INK, True)
bar_chart(s, LM - Inches(0.1), Inches(2.5), Inches(7.4), Inches(3.6), ["High (253)", "Medium (375)", "Low (1,372)"],
          [("Predicted", (48.4, 21.3, 6.8)), ("Actual", (51.0, 21.9, 5.8))], [PALE, RED], horizontal=False, legend=True,
          max_v=60, gap=80)
T(s, LM, Inches(6.15), Inches(7.2), Inches(0.5),
  "Each patient's latest discharge. Includes rows used in training; held-out metrics are on the right.", 11, GREY)
sx = Inches(8.75)
for i, (n, l) in enumerate([("3.34×", "readmission rate in the top 10% the model flags, vs average (held-out)"),
                            ("0.779", "test AUC on a held-out quarter of discharges"),
                            ("v1", "registered in Unity Catalog as @champion; scores all 2,000 patients")]):
    y = Inches(2.35) + i * Inches(1.3)
    hline(s, sx, y, Inches(3.75))
    T(s, sx, y + Inches(0.12), Inches(3.75), Inches(0.6), n, 30, RED if i == 0 else INK, True)
    T(s, sx, y + Inches(0.7), Inches(3.75), Inches(0.6), l, 12, GREY, spacing=1.25)
notes(s, "The predicted and actual bars sit close together, so the scores can be read as probabilities. The headline "
         "for operations is lift: calling the top decile first reaches patients 3.3 times as likely to be readmitted. "
         "Sources: evidence/03 (held-out metrics) and evidence/07 (tier rates).")

# ── 8. Genie ──────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK); rect(s, 0, 0, prs.slide_width, prs.slide_height, PAPER)
heading(s, "Genie", "The quality team asks in plain English and gets the answer from the governed tables.")
qa = [("How many high-risk patients does each facility have?", "Main 91  ·  North 89  ·  Valley 73"),
      ("Which facility had the highest COPD readmission rate?", "Pinecrest North, 20.8% (58 of 279)"),
      ("Which high-risk patients have no follow-up visit scheduled?", "PC-01684 first, at 0.91 predicted risk"),
      ("What is the average predicted risk by discharge disposition?", "Left against advice 0.29  ·  Home 0.13")]
for i, (q, a) in enumerate(qa):
    y = Inches(2.4) + i * Inches(0.98)
    hline(s, LM, y, CW)
    T(s, LM, y + Inches(0.25), Inches(6.6), Inches(0.6), f"“{q}”", 15, INK, True)
    T(s, LM + Inches(7.0), y + Inches(0.25), Inches(4.6), Inches(0.6), a, 15, RED, True)
hline(s, LM, Inches(2.4) + 4 * Inches(0.98), CW)
T(s, LM, Inches(6.45), CW, Inches(0.4), "Asked through the Genie Conversation API; the generated SQL for each answer is in evidence/05.", 11, GREY)
notes(s, "Four real questions with real answers. The third one ties Genie back to the patient on the next slide.")

# ── 9. One patient ────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK); rect(s, 0, 0, prs.slide_width, prs.slide_height, PAPER)
heading(s, "One patient, end to end", "PC-01684: heart failure, sent to skilled nursing, no follow-up booked.")
steps = [("Ingested", "raw file → gold"), ("Governed", "name, phone masked"), ("Scored", "0.91 → High"),
         ("Surfaced", "Genie lists first"), ("Served", "~4 ms from Lakebase"), ("Approved", "written to care_actions")]
sw = CW / 6
line = rect(s, LM + int(sw / 2), Inches(2.62), int(sw * 5), Inches(0.03), RED)
for i, (a, b) in enumerate(steps):
    cx0 = LM + int(i * sw)
    dot = s.shapes.add_shape(MSO_SHAPE.OVAL, cx0 + int(sw / 2) - Inches(0.11), Inches(2.52), Inches(0.22), Inches(0.22))
    dot.fill.solid(); dot.fill.fore_color.rgb = RED; dot.line.fill.background()
    T(s, cx0, Inches(2.9), int(sw), Inches(0.3), a, 14, INK, True, align=PP_ALIGN.CENTER)
    T(s, cx0, Inches(3.22), int(sw), Inches(0.4), b, 12, GREY, align=PP_ALIGN.CENTER)
rect(s, LM, Inches(4.0), CW, Inches(2.55), WHITE, RULE)
rect(s, LM, Inches(4.0), Inches(0.06), Inches(2.55), RED)
T(s, LM + Inches(0.35), Inches(4.18), Inches(6), Inches(0.3), "WHAT THE COORDINATOR SAW (APP LOG, VERBATIM EXCERPT)", 10, RED, True)
T(s, LM + Inches(0.35), Inches(4.5), CW - Inches(0.7), Inches(2.0),
  [[("Barriers to follow-up: ", {"bold": True}),
    ("transportation to a follow-up visit isn't arranged yet (per the daughter), and the patient reports that the cost "
     "of the inhaler and copays is a barrier.", {})],
   [("First action: ", {"bold": True}),
    ("schedule the follow-up visit within 7 days and book it together with transportation. Coordinate with the "
     "daughter and the skilled nursing facility, and flag the cost concerns for financial or medication assistance.", {})],
   [("Approved by the coordinator · saved as action c3c92782 · read back from Lakebase", {"size": 12, "color": GREY})]],
  14, INK, spacing=1.3)
notes(s, "This is the integration proof. The explanation is the model's actual output in the app log, grounded in the "
         "patient's two coordinator notes. The approval was read back from the Lakebase care_actions table. "
         "Source: evidence/06_app_execution.md.")

# ── 10. Value ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, prs.slide_width, prs.slide_height, NAVY)
heading(s, "What it's worth", "For the CQO and CFO: each point of readmission rate is about $3M a year.", dark=True)
eq = [("20,000", "discharges a year"), ("× 1 pt", "lower readmission rate"), ("= 200", "readmissions avoided"),
      ("× $15K", "per second stay"), ("= $3M", "avoided cost per year")]
for i, (n, l) in enumerate(eq):
    x = LM + i * Inches(2.33)
    T(s, x, Inches(2.5), Inches(2.3), Inches(0.8), n, 34, RED if i == 4 else WHITE, True)
    T(s, x, Inches(3.25), Inches(2.2), Inches(0.4), l, 12, RGBColor(0xAF, 0xBC, 0xC2))
T(s, LM, Inches(3.85), CW, Inches(0.4),
  "Illustrative figures for a mid-size system, not from the synthetic data. HRRP penalty relief, the CFO's other "
  "exposure, comes on top.", 12, RGBColor(0x8C, 0x9A, 0xA1))
hline(s, LM, Inches(4.55), CW, RGBColor(0x33, 0x4D, 0x58))
plan = [("90-day pilot", "CHF and COPD discharges at all three hospitals: the two highest-rate conditions in the data."),
        ("CQO scorecard", "Weekly: readmission rate on the pilot cohort and the share of High-risk patients with a follow-up booked within 7 days."),
        ("Keep it current", "Retrain monthly from the same pipeline; promote a new version only if it beats @champion.")]
pw = Inches(3.65)
for i, (h, b) in enumerate(plan):
    x = LM + i * (pw + Inches(0.33))
    T(s, x, Inches(4.8), pw, Inches(0.35), h, 16, WHITE, True)
    T(s, x, Inches(5.2), pw, Inches(1.3), b, 13, RGBColor(0xC6, 0xD2, 0xD7), spacing=1.3)
notes(s, "The arithmetic is deliberately simple so a finance audience can check it. The pilot measure is the one the "
         "CQO already reports, plus a leading indicator the care team controls: follow-ups booked within a week.")

# ── page chrome ───────────────────────────────────────────────────────────────────────────
for i, sl in enumerate(prs.slides, start=1):
    if i > 1:
        page(sl, i, dark=(i == len(prs.slides)))

prs.save("/tmp/deck.pptx")  # volumes do not support the random-access writes zip needs
shutil.copy("/tmp/deck.pptx", OUT)
print("saved", OUT, "slides:", len(prs.slides))
