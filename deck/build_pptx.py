# Databricks notebook source
# Build the Pinecrest Care Coordinator deck as an editable PPTX (native text boxes + shapes,
# Google Slides friendly). Same content as deck/deck.html. Output goes to a UC volume.

# COMMAND ----------

# MAGIC %pip install -q python-pptx==1.0.2

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

OUT = "/Volumes/users/narasimha_kamathardi/pinecrest_artifacts/Pinecrest Care Coordinator.pptx"
NAVY, CREAM, RED, WHITE = RGBColor(0x1B, 0x2F, 0x38), RGBColor(0xF7, 0xF6, 0xF2), RGBColor(0xFF, 0x36, 0x21), RGBColor(0xFF, 0xFF, 0xFF)
MUTED, LINE, CARD_DK, SOFT = RGBColor(0x6B, 0x73, 0x78), RGBColor(0xE3, 0xE1, 0xDB), RGBColor(0x24, 0x41, 0x4D), RGBColor(0xC6, 0xD2, 0xD7)
FONT = "Arial"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
L, R = Inches(0.9), Inches(13.333 - 0.9)
W = R - L


def bg(slide, color):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = color


def text(slide, x, y, w, h, runs, size=16, color=None, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    """runs: str, or list of paragraphs; each paragraph is a str or list of (text, {overrides})."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        for t, o in ([(para, {})] if isinstance(para, str) else para):
            r = p.add_run()
            r.text = t
            r.font.name = FONT
            r.font.size = Pt(o.get("size", size))
            r.font.bold = o.get("bold", bold)
            r.font.italic = o.get("italic", False)
            r.font.color.rgb = o.get("color", color or NAVY)
        p.space_after = Pt(o.get("space", 6)) if para else Pt(6)
    return tb


def box(slide, x, y, w, h, fill, line=None, radius=True):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, x, y, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line:
        s.line.color.rgb = line
        s.line.width = Pt(1)
    else:
        s.line.fill.background()
    if radius:
        s.adjustments[0] = 0.08
    s.shadow.inherit = False
    return s


def header(slide, kicker, title_parts, dark=False):
    text(slide, L, Inches(0.6), W, Inches(0.3), kicker.upper(), 12, RED, True)
    text(slide, L, Inches(0.95), Inches(11.2), Inches(1.4),
         [[(t, {"color": RED if hot else (WHITE if dark else NAVY)}) for t, hot in title_parts]], 32, bold=True)


def footer(slide, left, right, dark=False):
    c = RGBColor(0x9F, 0xB0, 0xB8) if dark else MUTED
    text(slide, L, Inches(6.95), Inches(6.5), Inches(0.3), left, 11, c)
    text(slide, Inches(6.9), Inches(6.95), Inches(5.53), Inches(0.3), right, 11, c, align=PP_ALIGN.RIGHT)


def stat_cards(slide, y, cards, dark=False, h=Inches(1.55)):
    gap = Inches(0.2)
    cw = int((W - gap * (len(cards) - 1)) / len(cards))
    for i, (lbl, big, sub, hot) in enumerate(cards):
        x = L + i * (cw + gap)
        box(slide, x, y, cw, h, CARD_DK if dark else WHITE, RED if hot else (None if dark else LINE))
        lc = RED if hot else (RGBColor(0xFF, 0x7A, 0x66) if dark else MUTED)
        text(slide, x + Inches(0.25), y + Inches(0.2), cw - Inches(0.5), Inches(0.3), lbl.upper(), 11, lc, True)
        text(slide, x + Inches(0.25), y + Inches(0.48), cw - Inches(0.5), Inches(0.6), big, 34,
             RED if hot else (WHITE if dark else NAVY), True)
        text(slide, x + Inches(0.25), y + Inches(1.1), cw - Inches(0.5), Inches(0.35), sub, 12,
             SOFT if dark else MUTED, True)


def notes(slide, s):
    slide.notes_slide.notes_text_frame.text = s


EV = "github.com/naradbx-dsa-blaze/pinecrest-readmission-journey"

# 1 — title -----------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, NAVY)
box(s, L, Inches(0.72), Inches(0.6), Inches(0.06), RED, radius=False)
text(s, L + Inches(0.8), Inches(0.6), Inches(8), Inches(0.3), "PINECREST HEALTH · CARE COORDINATION", 12, RED, True)
hexagon = s.shapes.add_shape(MSO_SHAPE.HEXAGON, Inches(9.9), Inches(0.9), Inches(2.4), Inches(2.1))
hexagon.fill.background(); hexagon.line.color.rgb = RED; hexagon.line.width = Pt(1.5); hexagon.rotation = 90
text(s, L, Inches(4.0), Inches(11.5), Inches(1.1), "Pinecrest Care Coordinator", 54, WHITE, True)
text(s, L, Inches(5.15), Inches(10.3), Inches(0.9),
     "Ranking 30-day readmission risk and turning it into an approved care action — one governed data "
     "journey on Databricks, from raw files to the app.", 18, SOFT)
footer(s, "Narasimha Kamathardi · Fictional hospital system, synthetic data", "November 2026", dark=True)
notes(s, "Pinecrest Health is a fictional three-hospital system and every record in this build is synthetic. "
         "The goal: help care coordinators decide which discharged patients to call first, and record what they did.")

# 2 — problem ---------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, CREAM)
header(s, "The problem", [("Coordinators can only call a fraction of discharged patients — ", False),
                          ("today they don't know who to call first.", True)])
stat_cards(s, Inches(2.35), [("Hospitals", "3", "Pinecrest Main, North, Valley", False),
                             ("Discharges in dataset", "6,013", "after data-quality checks", False),
                             ("30-day readmission rate", "14.7%", "about 1 in 7 come back", False),
                             ("Penalty exposure", "HRRP", "CMS readmission penalties", True)])
box(s, L, Inches(4.3), Inches(6.4), Inches(1.6), NAVY)
text(s, L + Inches(0.3), Inches(4.5), Inches(5.8), Inches(1.3),
     [[("SO WHAT", {"size": 11, "color": RGBColor(0xFF, 0x7A, 0x66)})],
      [("Every avoidable readmission costs a second stay plus Medicare penalty risk — and coordinators work "
        "the list without knowing who matters most.", {"size": 16, "color": WHITE})]], bold=True)
text(s, Inches(7.6), Inches(4.4), Inches(4.8), Inches(1.5),
     [[("THE REAL QUESTION", {"size": 11, "color": MUTED})],
      [("\"Which of today's discharges is most likely to come back, why — and what do we do first?\"", {"size": 19})]],
     bold=True)
footer(s, "Pinecrest Care Coordinator", "Fictional hospital system · synthetic data")
notes(s, "The dataset covers 6,013 clean discharges across three hospitals with a 14.7% readmission rate. "
         "The problem isn't knowing that readmissions are high — it's prioritising a limited outreach team.")

# 3 — architecture ----------------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, CREAM)
header(s, "How it's built", [("Six stages, ", False), ("one journey", True),
                             (" — every stage reads what the previous one produced.", False)])
steps = [("01", "Lakeflow", "Auto Loader ingests raw CSV/JSON from a Unity Catalog volume into bronze → silver → gold, with data-quality expectations."),
         ("02", "Unity Catalog", "PHI tags, column masks on name and phone, business comments and automatic lineage."),
         ("03", "ML", "Gradient-boosted readmission model, tracked in MLflow, registered in UC as champion, scores every patient."),
         ("04", "Lakebase", "Risk worklist and notes synced from UC into Postgres, plus a writable care_actions table."),
         ("05", "Genie", "Natural-language questions over the same governed gold tables."),
         ("06", "Databricks App", "Worklist, AI explanation (Claude via a serving endpoint), approve → write back to Lakebase.")]
gap = Inches(0.15); cw = int((W - gap * 5) / 6)
for i, (n, t, d) in enumerate(steps):
    x = L + i * (cw + gap); y = Inches(2.3)
    box(s, x, y, cw, Inches(2.5), WHITE, LINE)
    box(s, x, y, cw, Inches(0.07), RED, radius=False)
    text(s, x + Inches(0.17), y + Inches(0.25), cw - Inches(0.34), Inches(0.3), n + (" →" if i < 5 else ""), 12, RED)
    text(s, x + Inches(0.17), y + Inches(0.55), cw - Inches(0.34), Inches(0.4), t, 17, NAVY, True)
    text(s, x + Inches(0.17), y + Inches(1.0), cw - Inches(0.34), Inches(1.45), d, 12, RGBColor(0x3D, 0x4A, 0x50))
box(s, L, Inches(5.15), W, Inches(0.75), NAVY)
text(s, L + Inches(0.3), Inches(5.15), W - Inches(0.6), Inches(0.75),
     "One platform, one permission model — raw file, model score, served row and approved action are all governed by Unity Catalog.",
     15, WHITE, True, anchor=MSO_ANCHOR.MIDDLE)
footer(s, "Pinecrest Care Coordinator", EV)
notes(s, "Walk left to right: the same records flow through all six stages. Nothing is copied out of the platform; "
         "each stage's output is the next stage's input, and Unity Catalog governs all of it.")

# 4 — data & governance -----------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, CREAM)
header(s, "Data & governance", [("Bad data is stopped at ingest, ", False), ("and patient identity never leaks.", True)])
cols = [("LAKEFLOW PIPELINE", ["2,000 patients · 6,038 raw discharges · 3,000 coordinator notes",
                               "25 invalid rows dropped by the valid_length_of_stay expectation",
                               "6,013 clean discharges in gold, ready for the model",
                               "Serverless, declarative, incremental (Auto Loader)"]),
        ("UNITY CATALOG", ["Name, phone and ZIP tagged phi",
                           "Name and phone masked for anyone outside the care team",
                           "Business comments on the risk table (also improves Genie)",
                           "Lineage captured bronze → silver → gold automatically"])]
cw2 = int((W - Inches(0.2)) / 2)
for i, (lbl, items) in enumerate(cols):
    x = L + i * (cw2 + Inches(0.2))
    box(s, x, Inches(2.25), cw2, Inches(2.6), WHITE, LINE)
    text(s, x + Inches(0.3), Inches(2.45), cw2 - Inches(0.6), Inches(0.3), lbl, 11, RED, True)
    text(s, x + Inches(0.3), Inches(2.85), cw2 - Inches(0.6), Inches(1.9), [[("•  " + it, {"space": 10})] for it in items], 15)
text(s, L, Inches(5.1), W, Inches(0.4), "All data generated synthetically with a fixed seed — no real patients, no customer data.", 14, MUTED)
footer(s, "Pinecrest Care Coordinator", "Evidence: evidence/01_lakeflow · evidence/02_unity_catalog")
notes(s, "I planted 25 invalid discharges in the raw data; the pipeline's expectation dropped exactly those 25. "
         "Name and phone are tagged and masked by a Unity Catalog function, and lineage was captured without extra work.")

# 5 — model -----------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, CREAM)
header(s, "The model", [("The top 10% of patients the model flags are readmitted ", False), ("3.3× as often as average.", True)])
stat_cards(s, Inches(2.35), [("Test AUC", "0.779", "held-out 25% of discharges", False),
                             ("Average precision", "0.434", "vs 0.147 base rate", False),
                             ("Top-decile lift", "3.34×", "where coordinators should call first", True),
                             ("Registered", "v1", "@champion in Unity Catalog", False)])
text(s, L, Inches(4.35), Inches(5.6), Inches(1.6),
     [[("OUTCOME", {"size": 11, "color": MUTED, "bold": True})],
      [("2,000 patients scored → ", {}), ("253 High, 375 Medium, 1,372 Low", {"bold": True}),
       (" risk — each with a next-best action, e.g. \"Schedule follow-up visit within 7 days\".", {})]], 16)
text(s, Inches(6.9), Inches(4.35), Inches(5.5), Inches(1.6),
     [[("WHERE THE RISK SITS", {"size": 11, "color": MUTED, "bold": True})],
      [("Patients who left against medical advice average ", {}), ("0.29", {"bold": True}),
       (" predicted risk vs ", {}), ("0.13", {"bold": True}), (" for those discharged home (from Genie, slide 6).", {})]], 16)
footer(s, "Pinecrest Care Coordinator", "Evidence: evidence/03_ml_training_run_output.md")
notes(s, "AUC 0.779 on a held-out quarter of discharges. The practical number is lift: if coordinators only call "
         "the top 10% the model flags, they reach patients 3.3 times more likely to be readmitted than average.")

# 6 — genie -----------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, CREAM)
header(s, "Genie", [("Ask it in plain English — ", False), ("Genie writes the SQL", True), (" on the same governed tables.", False)])
qa = [("\"How many high-risk patients does each facility have?\"", [("Main ", {}), ("91", {"bold": True, "color": RED}), (" · North ", {}),
                                                                     ("89", {"bold": True, "color": RED}), (" · Valley ", {}), ("73", {"bold": True, "color": RED})]),
      ("\"Which facility had the highest COPD readmission rate?\"", [("Pinecrest North — ", {}), ("20.8%", {"bold": True, "color": RED}), (" (58 of 279)", {})]),
      ("\"Average predicted risk by discharge disposition?\"", [("Left AMA ", {}), ("0.29", {"bold": True, "color": RED}), (" vs Home ", {}),
                                                               ("0.13", {"bold": True, "color": RED}), (" — more than 2× higher", {})])]
for i, (q, a) in enumerate(qa):
    y = Inches(2.3) + i * Inches(1.0)
    box(s, L, y, W, Inches(0.8), WHITE, LINE)
    box(s, L + Inches(0.25), y + Inches(0.22), Inches(0.06), Inches(0.36), RED, radius=False)
    text(s, L + Inches(0.45), y, Inches(5.6), Inches(0.8), q, 16, NAVY, True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, L + Inches(6.4), y, Inches(5.0), Inches(0.8), [a], 16, anchor=MSO_ANCHOR.MIDDLE)
footer(s, "Pinecrest Care Coordinator", "Evidence: evidence/05_genie_conversations.md")
notes(s, "These were asked through the Genie Conversation API; the evidence file shows the SQL Genie generated and "
         "the rows it returned. Business users get answers without writing SQL, on the same governed tables.")

# 7 — one patient -----------------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, CREAM)
header(s, "One patient, end to end", [("Patient PC-01684: CHF, skilled nursing, ", False), ("no follow-up booked", True)])
tl = [("Lakeflow", "Raw file → bronze → silver → gold"), ("Unity Catalog", "Name and phone masked"),
      ("ML", "Risk 0.91 → High: \"Schedule follow-up within 7 days\""), ("Genie", "#1 answer to \"high-risk patients with no follow-up\""),
      ("Lakebase", "Served to the app in ~4 ms"), ("App", "AI explanation → coordinator approves → written to care_actions")]
seg = int(W / 6)
line = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, L + int(seg / 2), Inches(2.7), seg * 5, Inches(0.04))
line.fill.solid(); line.fill.fore_color.rgb = RED; line.line.fill.background()
for i, (t, d) in enumerate(tl):
    cx = L + i * seg + int(seg / 2)
    dot = s.shapes.add_shape(MSO_SHAPE.OVAL, cx - Inches(0.25), Inches(2.47), Inches(0.5), Inches(0.5))
    dot.fill.solid(); dot.fill.fore_color.rgb = RED; dot.line.fill.background()
    dot.text_frame.text = str(i + 1)
    p = dot.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    p.runs[0].font.size = Pt(15); p.runs[0].font.bold = True; p.runs[0].font.color.rgb = WHITE; p.runs[0].font.name = FONT
    text(s, L + i * seg + Inches(0.08), Inches(3.15), seg - Inches(0.16), Inches(0.35), t, 15, NAVY, True, align=PP_ALIGN.CENTER)
    text(s, L + i * seg + Inches(0.08), Inches(3.55), seg - Inches(0.16), Inches(1.0), d, 12, RGBColor(0x3D, 0x4A, 0x50), align=PP_ALIGN.CENTER)
box(s, L, Inches(5.0), W, Inches(0.75), NAVY)
text(s, L + Inches(0.3), Inches(5.0), W - Inches(0.6), Inches(0.75),
     "Human approval before anything is written — every action records the approver and timestamp in Lakebase.",
     15, WHITE, True, anchor=MSO_ANCHOR.MIDDLE)
footer(s, "Pinecrest Care Coordinator", "Evidence: evidence/06_app_execution.md")
notes(s, "This is the integration proof: one patient through all six stages. The approved action c3c92782… is in "
         "the app log and was read back from the Lakebase care_actions table.")

# 8 — value -----------------------------------------------------------------------------
s = prs.slides.add_slide(BLANK); bg(s, NAVY)
header(s, "Value & next step", [("One point of readmission rate is worth ", False), ("~$3M a year", True),
                                (" at a 20,000-discharge system.", False)], dark=True)
math = [("DISCHARGES / YR", "20,000", "mid-size health system", False), ("−1 POINT OF RATE", "−200", "readmissions avoided", False),
        ("× COST EACH", "$15K", "second stay", False), ("= AVOIDED COST", "$3M", "per year, per point", True)]
for i, (lbl, big, sub, hot) in enumerate(math):
    x = L + i * Inches(2.7)
    text(s, x, Inches(2.25), Inches(2.6), Inches(0.3), lbl, 11, RED if hot else RGBColor(0x9F, 0xB0, 0xB8))
    text(s, x, Inches(2.55), Inches(2.6), Inches(0.8), big, 44, RED if hot else WHITE, True)
    text(s, x, Inches(3.35), Inches(2.6), Inches(0.3), sub, 12, SOFT)
text(s, L, Inches(3.8), W, Inches(0.3), "Illustrative industry assumptions, not from the synthetic data.", 12, RGBColor(0x9F, 0xB0, 0xB8))
cw3 = int((W - Inches(0.4)) / 3)
for i, (lbl, body) in enumerate([("01 · PILOT", "90 days on CHF and COPD discharges"),
                                 ("02 · MEASURE", "Follow-ups booked within 7 days, weekly"),
                                 ("03 · IMPROVE", "Retrain monthly from the same pipeline")]):
    x = L + i * (cw3 + Inches(0.2))
    box(s, x, Inches(4.4), cw3, Inches(1.0), CARD_DK, RGBColor(0x33, 0x52, 0x5F))
    text(s, x + Inches(0.25), Inches(4.58), cw3 - Inches(0.5), Inches(0.3), lbl, 11, RGBColor(0xFF, 0x7A, 0x66), True)
    text(s, x + Inches(0.25), Inches(4.88), cw3 - Inches(0.5), Inches(0.4), body, 15, WHITE)
footer(s, "Narasimha Kamathardi · " + EV, "November 2026", dark=True)
notes(s, "The value math uses illustrative industry figures, not the synthetic data: one point of rate at 20,000 "
         "discharges is 200 readmissions, about $3M a year. Ask: a 90-day pilot on CHF and COPD.")

import shutil

prs.save("/tmp/deck.pptx")  # volumes do not support the random-access writes zip needs
shutil.copy("/tmp/deck.pptx", OUT)
print("saved", OUT, "slides:", len(prs.slides))
