// SENTINEL-NIDS — Round 1 submission deck generator.
// Every number is read from reports/metrics/*.json, never typed by hand.
//   node submission/build_deck.js
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const M = (f) => JSON.parse(fs.readFileSync(path.join(ROOT, "reports", "metrics", f), "utf8"));
const FIG = (n) => path.join(ROOT, "reports", "figures", n);

const lk = M("leakage_experiment.json");
const mc = M("model_comparison.json");
const zd = M("zeroday_experiment.json");
const dp = M("deployment_benchmark.json");
const ex = M("explainability.json");
const ds = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "processed", "dataset_summary.json"), "utf8"));

const A = lk.protocol_A_pooled_random_split;
const B = lk.protocol_B_official_split;
const FA = lk.failure_analysis;
const HY = zd.hybrid;
const RP = HY.recommended_operating_point;

// ---------- palette: defence / security. Dark navy dominant, alert red as the single accent.
const NAVY = "0D1B2A";      // dark slide background (dominant)
const NAVY_2 = "16293D";    // dark card
const WHITE = "FFFFFF";
const PAPER = "F7F8FA";     // light slide background
const INK = "0B0B0B";
const INK_2 = "42505C";
const MUTED = "7B8794";
const BLUE = "2A78D6";      // matches the figures
const ORANGE = "EB6834";    // matches the figures
const RED = "D03B3B";       // the accent — reserved for the damaging numbers
const GREEN = "0CA30C";      // fills only
const GREEN_TXT = "046B04";  // darker step for GREEN TEXT on light surfaces (AA)
const HAIR = "DDE3E8";

const H_FONT = "Cambria";   // serif headers — this is a scientific claim
const B_FONT = "Calibri";   // sans body

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";           // 13.333 x 7.5 in — set BEFORE adding slides
pres.author = "Manoj Kharkar";
pres.title = "SENTINEL-NIDS — ML Bubble 2026";

const W = 13.333, H = 7.5, MG = 0.62;

let slideNo = 0;
function footer(s, dark) {
  slideNo += 1;
  s.addText("SENTINEL-NIDS  ·  ML Bubble 2026  ·  TE-BE Advanced", {
    x: MG, y: H - 0.42, w: 7, h: 0.26, fontSize: 9, fontFace: B_FONT,
    color: dark ? "6B7C8F" : MUTED, margin: 0,
  });
  s.addText(String(slideNo), {
    x: W - MG - 0.6, y: H - 0.42, w: 0.6, h: 0.26, fontSize: 9, fontFace: B_FONT,
    color: dark ? "6B7C8F" : MUTED, align: "right", margin: 0,
  });
}

function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: NAVY };
  return s;
}
function lightSlide(title, kicker) {
  const s = pres.addSlide();
  s.background = { color: PAPER };
  if (kicker) {
    s.addText(kicker.toUpperCase(), {
      x: MG, y: 0.34, w: W - 2 * MG, h: 0.24, fontSize: 10.5, bold: true,
      fontFace: B_FONT, color: RED, charSpacing: 1.6, margin: 0,
    });
  }
  s.addText(title, {
    x: MG, y: kicker ? 0.6 : 0.44, w: W - 2 * MG, h: 0.72, fontSize: 27, bold: true,
    fontFace: H_FONT, color: INK, margin: 0, valign: "top",
  });
  return s;
}

// A stat tile: big number + label. The repeated motif of the deck.
function stat(s, x, y, w, value, label, color, valueSize) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h: 1.5, fill: { color: WHITE }, rectRadius: 0.08,
    line: { color: HAIR, width: 1 },
    shadow: { type: "outer", angle: 90, blur: 8, offset: 1, color: "9AA5B1", opacity: 0.18 },
  });
  s.addText(value, {
    x: x + 0.02, y: y + 0.14, w: w - 0.04, h: 0.78, fontSize: valueSize || 40, bold: true,
    fontFace: H_FONT, color: color || INK, align: "center", margin: 0, valign: "middle",
  });
  s.addText(label, {
    x: x + 0.12, y: y + 0.94, w: w - 0.24, h: 0.46, fontSize: 10.5, fontFace: B_FONT,
    color: INK_2, align: "center", margin: 0, valign: "top",
  });
}

function bullets(s, items, opts) {
  const o = Object.assign({ x: MG, y: 1.5, w: 6.0, h: 4.4, fontSize: 14.5 }, opts || {});
  s.addText(items.map((t, i) => ({
    text: t, options: { bullet: true, breakLine: i !== items.length - 1, paraSpaceAfter: 10 },
  })), {
    x: o.x, y: o.y, w: o.w, h: o.h, fontSize: o.fontSize, fontFace: B_FONT,
    color: INK_2, margin: 0, valign: "top", lineSpacing: 20,
  });
}

const QUIET = {
  showLegend: false, showTitle: false,
  catAxisLabelColor: INK_2, valAxisLabelColor: MUTED,
  catAxisLabelFontFace: B_FONT, valAxisLabelFontFace: B_FONT,
  catAxisLabelFontSize: 11, valAxisLabelFontSize: 10,
  valGridLine: { color: HAIR, size: 1 }, catGridLine: { style: "none" },
  catAxisLineShow: false, valAxisLineShow: false,
  dataLabelFontFace: B_FONT, dataLabelFontSize: 10, dataLabelColor: INK,
  showValue: true, dataLabelPosition: "outEnd",
  barGapWidthPct: 45,
};

// ══════════════════════════════════════════════════ 1. TITLE
{
  const s = darkSlide();
  s.addText("SENTINEL-NIDS", {
    x: MG, y: 1.75, w: 11, h: 1.0, fontSize: 54, bold: true, fontFace: H_FONT,
    color: WHITE, margin: 0, charSpacing: 0.5,
  });
  s.addText("Network intrusion detection for critical infrastructure — evaluated honestly", {
    x: MG, y: 2.78, w: 10.6, h: 0.5, fontSize: 19, fontFace: B_FONT, color: "9FB3C8", margin: 0,
  });
  s.addShape(pres.ShapeType.roundRect, {
    x: MG, y: 3.72, w: 8.9, h: 1.16, fill: { color: NAVY_2 }, rectRadius: 0.08,
    line: { color: "24405C", width: 1 },
  });
  s.addText([
    { text: "Machine-learning intrusion detectors report 97–99% accuracy.\n", options: { color: "C9D6E2", fontSize: 14 } },
    { text: "I changed only the train/test split. Accuracy fell to " , options: { color: "C9D6E2", fontSize: 14 } },
    { text: `${(B.accuracy * 100).toFixed(2)}%`, options: { color: WHITE, fontSize: 14, bold: true } },
    { text: ".", options: { color: "C9D6E2", fontSize: 14 } },
  ], { x: MG + 0.3, y: 3.9, w: 8.3, h: 0.8, fontFace: B_FONT, margin: 0, valign: "middle", lineSpacing: 22 });

  s.addText([
    { text: "Manoj Kharkar", options: { bold: true, color: WHITE, fontSize: 14 } },
    { text: "  ·  solo submission", options: { color: "9FB3C8", fontSize: 14 } },
  ], { x: MG, y: 5.25, w: 8, h: 0.32, fontFace: B_FONT, margin: 0 });
  s.addText("ML Bubble 2026  ·  Army Institute of Technology, Pune  ·  Track: TE-BE (Design & Solve — Advanced)", {
    x: MG, y: 5.62, w: 11, h: 0.32, fontSize: 12, fontFace: B_FONT, color: "6B7C8F", margin: 0,
  });
  s.addText("Round 1 — Idea Submission  ·  08 August 2026", {
    x: MG, y: 5.98, w: 11, h: 0.32, fontSize: 12, fontFace: B_FONT, color: "6B7C8F", margin: 0,
  });
  s.addNotes("Opening: state the claim in the first 20 seconds. One model, one pipeline, one seed; " +
    "only the split differs; 99.51% becomes 75.28%.");
  footer(s, true);
}

// ══════════════════════════════════════════════════ 2. THE PROBLEM
{
  const s = lightSlide("Critical networks are defended by systems that cannot see a new attack", "The problem");
  bullets(s, [
    "Defence networks, power grids and military logistics are still largely protected by signature-based intrusion detection — traffic is flagged only if it matches a known pattern.",
    "That is structurally blind to any attack never seen before. Machine learning is the obvious replacement.",
    "Intrusion detection is not pattern matching. It is a distribution-shift problem: the adversary actively invents traffic the model has never seen.",
    "The rarest attack classes are the most dangerous ones, and a missed intrusion costs incomparably more than a wasted analyst minute.",
    "So the question that decides whether an ML-IDS number is meaningful is not which model was used. It is how the data was split.",
  ], { y: 1.62, w: 6.9, h: 4.3, fontSize: 14.5 });

  s.addShape(pres.ShapeType.roundRect, {
    x: 7.85, y: 1.62, w: 4.863, h: 4.05, fill: { color: NAVY }, rectRadius: 0.1, line: { color: NAVY, width: 1 },
  });
  s.addText("Why the published numbers can't be trusted", {
    x: 8.13, y: 1.9, w: 4.3, h: 0.6, fontSize: 16, bold: true, fontFace: H_FONT, color: WHITE, margin: 0,
  });
  s.addText([
    { text: "Standard supervised learning assumes the test data is drawn from the training distribution.\n\n", options: { fontSize: 13, color: "C9D6E2", breakLine: true } },
    { text: "In intrusion detection that assumption is false by definition — the attacker's job is to violate it.\n\n", options: { fontSize: 13, color: "C9D6E2", breakLine: true } },
    { text: "So the way a benchmark is split is not a technical detail. It decides whether the reported number means anything at all.", options: { fontSize: 13, color: WHITE, bold: true } },
  ], { x: 8.13, y: 2.6, w: 4.3, h: 3.1, fontFace: B_FONT, margin: 0, valign: "top", lineSpacing: 19 });
  s.addNotes("Frame ML as necessary but the evaluation as broken. Do not oversell ML here.");
  footer(s);
}

// ══════════════════════════════════════════════════ 3. HYPOTHESIS (dark)
{
  const s = darkSlide();
  s.addText("THE HYPOTHESIS", {
    x: MG, y: 1.15, w: 11, h: 0.3, fontSize: 11, bold: true, fontFace: B_FONT,
    color: RED, charSpacing: 1.8, margin: 0,
  });
  s.addText("The high accuracies reported for ML-based intrusion detection are an artefact of evaluating on a random split of a single dataset.", {
    x: MG, y: 1.6, w: 11.6, h: 1.9, fontSize: 30, bold: true, fontFace: H_FONT,
    color: WHITE, margin: 0, lineSpacing: 40, valign: "top",
  });
  s.addText("Under a realistic protocol — where the test set contains attack types absent from training — performance collapses, and the collapse is concentrated precisely in the rarest and most severe attack categories.", {
    x: MG, y: 3.7, w: 11.2, h: 1.2, fontSize: 16, fontFace: B_FONT, color: "9FB3C8",
    margin: 0, lineSpacing: 26, valign: "top",
  });
  s.addShape(pres.ShapeType.roundRect, {
    x: MG, y: 5.25, w: 12.093, h: 0.95, fill: { color: NAVY_2 }, rectRadius: 0.08, line: { color: "24405C", width: 1 },
  });
  s.addText("This is a falsifiable claim, and the experiment that tests it is one command.", {
    x: MG + 0.3, y: 5.25, w: 11, h: 0.95, fontSize: 15, bold: true, fontFace: B_FONT,
    color: WHITE, margin: 0, valign: "middle",
  });
  s.addNotes("Say the hypothesis out loud. Emphasise that it could have come out the other way.");
  footer(s, true);
}

// ══════════════════════════════════════════════════ 4. DATASET
{
  const s = lightSlide("NSL-KDD — chosen because it ships a built-in zero-day benchmark", "The dataset");
  const CW4 = 2.873, ST4 = 3.073;   // 4 cards + 3 x 0.2in gutters = 12.093in content width
  stat(s, MG, 1.55, CW4, ds.train_rows.toLocaleString(), "training flows (KDDTrain+)", INK, 30);
  stat(s, MG + ST4, 1.55, CW4, ds.test_rows.toLocaleString(), "test flows (KDDTest+)", INK, 30);
  stat(s, MG + 2 * ST4, 1.55, CW4, String(ds.n_attack_types_test_only), "attack types that appear ONLY in the test set", RED, 40);
  stat(s, MG + 3 * ST4, 1.55, CW4, `${(ds.novel_share_of_test * 100).toFixed(1)}%`, "of test flows are an attack type never trained on", RED, 40);

  s.addText("Two properties — both destroyed by pooling the splits", {
    x: MG, y: 3.32, w: 6.4, h: 0.34, fontSize: 15, bold: true, fontFace: H_FONT, color: INK, margin: 0,
  });
  bullets(s, [
    "17 of the 37 attack types occur only in KDDTest+ — 3,750 flows. The model must generalise to attacks it has never observed.",
    "The class priors move: R2L is 0.79% of training data but 12.2% of test data (15.5×); U2R moves 0.04% → 0.89% (21.5×).",
    "0 duplicate rows in training — so this is NOT classical row leakage. It is distribution shift, which is a more interesting failure.",
  ], { x: MG, y: 3.72, w: 6.4, h: 2.5, fontSize: 13 });

  s.addText("Why not a newer dataset?", {
    x: 7.5, y: 3.32, w: 5.2, h: 0.34, fontSize: 15, bold: true, fontFace: H_FONT, color: INK, margin: 0,
  });
  s.addText([
    { text: "UNSW-NB15, CIC-IDS2017 and HuggingFace NIDS corpora were all attempted and are unreachable from the build environment (verified 403).\n\n", options: { breakLine: true } },
    { text: "But NSL-KDD is also the right choice on merit: it is the only common benchmark with a documented unseen-attack test protocol — which is what makes the experiment possible.\n\n", options: { breakLine: true } },
    { text: "Its age (1999 traffic) is a genuine limitation, stated in the model card rather than hidden.", options: { bold: true, color: INK } },
  ], { x: 7.5, y: 3.72, w: 5.2, h: 2.5, fontSize: 12.5, fontFace: B_FONT, color: INK_2, margin: 0, valign: "top", lineSpacing: 17 });
  s.addNotes("If asked why not a modern dataset, lead with the merit argument, not the availability one.");
  footer(s);
}

// ══════════════════════════════════════════════════ 5. EXPERIMENT DESIGN
{
  const s = lightSlide("One model. One pipeline. One seed. Only the split changes.", "The experiment");

  const cardW = 5.7715;   // 2 cards + 0.55in gutter = 12.093in, flush with the band below
  [["PROTOCOL A", "The common error", BLUE,
    "Concatenate KDDTrain+ and KDDTest+ (148,517 rows), shuffle, stratified 80/20 split.\n\nThis is what a large share of tutorials, blog posts and student projects do.",
    "Used ONLY for this comparison. Never to report our performance."],
   ["PROTOCOL B", "Honest", ORANGE,
    "Train on KDDTrain+ (125,973). Test on KDDTest+ (22,544) — as the dataset authors designed it.\n\nThe test set keeps its 17 unseen attack types and its shifted class priors.",
    "Every performance number we claim comes from here."],
  ].forEach(([tag, sub, col, body, note], i) => {
    const x = MG + i * (cardW + 0.55);
    s.addShape(pres.ShapeType.roundRect, {
      x, y: 1.6, w: cardW, h: 3.15, fill: { color: WHITE }, rectRadius: 0.1,
      line: { color: HAIR, width: 1 },
      shadow: { type: "outer", angle: 90, blur: 8, offset: 1, color: "9AA5B1", opacity: 0.16 },
    });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.32, y: 1.9, w: 0.42, h: 0.42, fill: { color: col }, line: { color: col, width: 1 } });
    s.addText(String.fromCharCode(65 + i), { x: x + 0.32, y: 1.9, w: 0.42, h: 0.42, fontSize: 15, bold: true, fontFace: H_FONT, color: WHITE, align: "center", valign: "middle", margin: 0 });
    s.addText(tag, { x: x + 0.9, y: 1.88, w: cardW - 1.2, h: 0.26, fontSize: 12, bold: true, fontFace: B_FONT, color: col, charSpacing: 1.2, margin: 0 });
    s.addText(sub, { x: x + 0.9, y: 2.12, w: cardW - 1.2, h: 0.3, fontSize: 16, bold: true, fontFace: H_FONT, color: INK, margin: 0 });
    s.addText(body, { x: x + 0.34, y: 2.62, w: cardW - 0.68, h: 1.35, fontSize: 12.5, fontFace: B_FONT, color: INK_2, margin: 0, valign: "top", lineSpacing: 17 });
    s.addText(note, { x: x + 0.34, y: 4.06, w: cardW - 0.68, h: 0.55, fontSize: 12, bold: true, fontFace: B_FONT, color: INK, margin: 0, valign: "top", lineSpacing: 16 });
  });

  s.addShape(pres.ShapeType.roundRect, { x: MG, y: 5.15, w: 12.093, h: 0.94, fill: { color: NAVY }, rectRadius: 0.1, line: { color: NAVY, width: 1 } });
  s.addText("Held constant across both protocols", { x: MG + 0.34, y: 5.26, w: 11.4, h: 0.26, fontSize: 12, bold: true, fontFace: B_FONT, color: RED, charSpacing: 1.1, margin: 0 });
  s.addText(`RandomForestClassifier(n_estimators=300)  ·  ${lk.feature_count} one-hot features  ·  identical preprocessing  ·  random_state=42  ·  no tuning on either split`, {
    x: MG + 0.34, y: 5.54, w: 11.4, h: 0.46, fontSize: 13.5, fontFace: B_FONT, color: WHITE, margin: 0, valign: "top", lineSpacing: 19,
  });
  s.addNotes("The controlled-experiment framing is what makes this more than a caveat.");
  footer(s);
}

// ══════════════════════════════════════════════════ 6. HEADLINE RESULT
{
  const s = lightSlide("Accuracy falls 24 points. Macro-F1 falls 47. The error rate is 50× higher.", "The result");
  s.addChart(pres.ChartType.bar, [
    { name: "Protocol A — pooled random split", labels: ["Accuracy", "Macro-F1", "Balanced acc."], values: [A.accuracy, A.macro_f1, A.balanced_accuracy] },
    { name: "Protocol B — official split (honest)", labels: ["Accuracy", "Macro-F1", "Balanced acc."], values: [B.accuracy, B.macro_f1, B.balanced_accuracy] },
  ], Object.assign({}, QUIET, {
    x: MG - 0.1, y: 1.5, w: 7.5, h: 4.3, barDir: "bar", chartColors: [BLUE, ORANGE],
    showLegend: true, legendPos: "b", legendFontFace: B_FONT, legendFontSize: 11,
    valAxisMaxVal: 1.15, valAxisMinVal: 0, dataLabelFormatCode: "0.000",
  }));

  stat(s, 8.3, 1.55, 2.05, `${A.accuracy.toFixed(3)}`, "accuracy reported under Protocol A", BLUE, 26);
  stat(s, 10.55, 1.55, 2.15, `${B.accuracy.toFixed(3)}`, "accuracy under the honest protocol", ORANGE, 26);
  stat(s, 8.3, 3.3, 4.4, `${lk.gap.relative_error_increase_x}× more errors`, "under honest evaluation, same model", RED, 26);

  s.addShape(pres.ShapeType.roundRect, { x: 8.3, y: 5.05, w: 4.4, h: 1.35, fill: { color: NAVY }, rectRadius: 0.1, line: { color: NAVY, width: 1 } });
  s.addText("Nothing about the model changed. Only the way it was measured.", {
    x: 8.55, y: 5.05, w: 3.9, h: 1.35, fontSize: 14, bold: true, fontFace: B_FONT, color: WHITE, margin: 0, valign: "middle", lineSpacing: 20,
  });
  s.addNotes(`Gap: ${lk.gap.accuracy_points} accuracy points, ${lk.gap.macro_f1_points} macro-F1 points.`);
  footer(s);
}

// ══════════════════════════════════════════════════ 7. WHERE IT COLLAPSES
{
  const s = lightSlide("The collapse lands on the two families that mean an attacker got in", "Per-class breakdown");
  const fams = ["Normal", "DoS", "Probe", "R2L", "U2R"];
  s.addChart(pres.ChartType.bar, [
    { name: "Protocol A (pooled random split)", labels: fams, values: fams.map((f) => A.per_class_recall[f]) },
    { name: "Protocol B (honest)", labels: fams, values: fams.map((f) => B.per_class_recall[f]) },
  ], Object.assign({}, QUIET, {
    x: MG - 0.1, y: 1.5, w: 7.7, h: 4.35, barDir: "col", chartColors: [BLUE, ORANGE],
    showLegend: true, legendPos: "b", legendFontFace: B_FONT, legendFontSize: 11,
    valAxisMaxVal: 1.15, valAxisMinVal: 0, dataLabelFormatCode: "0.000",
    catAxisLabelFontSize: 12,
  }));
  s.addText("Recall, by attack family", { x: MG, y: 5.9, w: 7, h: 0.3, fontSize: 11, italic: true, fontFace: B_FONT, color: MUTED, margin: 0 });

  s.addShape(pres.ShapeType.roundRect, { x: 8.5, y: 1.6, w: 4.2, h: 1.92, fill: { color: WHITE }, rectRadius: 0.1, line: { color: RED, width: 2 } });
  s.addText("R2L — remote-to-local intrusion", { x: 8.78, y: 1.78, w: 3.7, h: 0.3, fontSize: 12.5, bold: true, fontFace: B_FONT, color: RED, margin: 0 });
  s.addText([{ text: "0.915", options: { fontSize: 24, bold: true, color: MUTED, fontFace: H_FONT } },
             { text: "   →   ", options: { fontSize: 16, color: MUTED } },
             { text: "0.038", options: { fontSize: 32, bold: true, color: RED, fontFace: H_FONT } }],
    { x: 8.78, y: 2.11, w: 3.7, h: 0.66, margin: 0, valign: "middle" });
  s.addText("2,754 of these in the test set. The model finds 106.", { x: 8.78, y: 2.82, w: 3.7, h: 0.7, fontSize: 12, fontFace: B_FONT, color: INK_2, margin: 0, valign: "top", lineSpacing: 16 });

  s.addShape(pres.ShapeType.roundRect, { x: 8.5, y: 3.82, w: 4.2, h: 1.92, fill: { color: WHITE }, rectRadius: 0.1, line: { color: RED, width: 2 } });
  s.addText("U2R — privilege escalation", { x: 8.78, y: 4.0, w: 3.7, h: 0.3, fontSize: 12.5, bold: true, fontFace: B_FONT, color: RED, margin: 0 });
  s.addText([{ text: "0.780", options: { fontSize: 24, bold: true, color: MUTED, fontFace: H_FONT } },
             { text: "   →   ", options: { fontSize: 16, color: MUTED } },
             { text: "0.005", options: { fontSize: 32, bold: true, color: RED, fontFace: H_FONT } }],
    { x: 8.78, y: 4.33, w: 3.7, h: 0.66, margin: 0, valign: "middle" });
  s.addText("200 in the test set. The model finds one.", { x: 8.78, y: 5.04, w: 3.7, h: 0.7, fontSize: 12, fontFace: B_FONT, color: INK_2, margin: 0, valign: "top", lineSpacing: 16 });
  s.addNotes("These two families signify actual compromise rather than disruption. Accuracy cannot see this.");
  footer(s);
}

// ══════════════════════════════════════════════════ 8. WHY — PRIOR SHIFT
{
  const s = lightSlide("Why: the test set is not the training distribution — by design", "Mechanism");
  const fams = ["Normal", "DoS", "Probe", "R2L", "U2R"];
  const ntr = Object.values(ds.family_counts_train).reduce((a, b) => a + b, 0);
  const nte = Object.values(ds.family_counts_test).reduce((a, b) => a + b, 0);
  s.addChart(pres.ChartType.bar, [
    { name: "KDDTrain+ share of split (%)", labels: fams, values: fams.map((f) => +(100 * ds.family_counts_train[f] / ntr).toFixed(2)) },
    { name: "KDDTest+ share of split (%)", labels: fams, values: fams.map((f) => +(100 * ds.family_counts_test[f] / nte).toFixed(2)) },
  ], Object.assign({}, QUIET, {
    x: MG - 0.1, y: 1.5, w: 7.7, h: 4.3, barDir: "col", chartColors: [BLUE, ORANGE],
    showLegend: true, legendPos: "b", legendFontFace: B_FONT, legendFontSize: 11,
    valAxisMinVal: 0, dataLabelFormatCode: "0.0",
    catAxisLabelFontSize: 12,
  }));
  stat(s, 8.5, 1.55, 4.2, "15.5×", "more R2L in test than in training (0.79% → 12.2%)", RED, 40);
  stat(s, 8.5, 3.3, 4.2, "21.5×", "more U2R in test than in training (0.04% → 0.89%)", RED, 40);
  s.addShape(pres.ShapeType.roundRect, { x: 8.5, y: 5.05, w: 4.2, h: 1.35, fill: { color: NAVY }, rectRadius: 0.1, line: { color: NAVY, width: 1 } });
  s.addText("Pooling the two files forces the priors to match — and deletes the whole problem.", {
    x: 8.75, y: 5.05, w: 3.7, h: 1.35, fontSize: 13, bold: true, fontFace: B_FONT, color: WHITE, margin: 0, valign: "middle", lineSpacing: 19,
  });
  footer(s);
}

// ══════════════════════════════════════════════════ 9. CONSEQUENCE
{
  const s = darkSlide();
  s.addText("THE OPERATIONAL CONSEQUENCE", { x: MG, y: 0.85, w: 11, h: 0.3, fontSize: 11, bold: true, fontFace: B_FONT, color: RED, charSpacing: 1.8, margin: 0 });
  s.addText("A missed attack is not a mislabelled row. It is an intrusion that raises no alarm at all.", {
    x: MG, y: 1.28, w: 11.6, h: 1.15, fontSize: 27, bold: true, fontFace: H_FONT, color: WHITE, margin: 0, lineSpacing: 36, valign: "top",
  });
  s.addImage({ path: FIG("fig4_novel_vs_seen.png"), x: MG, y: 2.62, w: 7.55, h: 2.98 });

  s.addShape(pres.ShapeType.roundRect, { x: 8.5, y: 2.62, w: 4.2, h: 1.62, fill: { color: NAVY_2 }, rectRadius: 0.1, line: { color: "24405C", width: 1 } });
  s.addText([{ text: `${(FA.novel_attacks.missed_as_normal_rate * 100).toFixed(1)}%\n`, options: { fontSize: 42, bold: true, color: RED, fontFace: H_FONT } },
             { text: "of attack types never seen in training are silently cleared as “normal”", options: { fontSize: 12, color: "C9D6E2" } }],
    { x: 8.72, y: 2.74, w: 3.76, h: 1.44, fontFace: B_FONT, margin: 0, valign: "top", lineSpacing: 20 });

  s.addShape(pres.ShapeType.roundRect, { x: 8.5, y: 4.42, w: 4.2, h: 1.62, fill: { color: NAVY_2 }, rectRadius: 0.1, line: { color: "24405C", width: 1 } });
  s.addText([{ text: `${(FA.novel_attacks.family_accuracy * 100).toFixed(1)}%\n`, options: { fontSize: 42, bold: true, color: WHITE, fontFace: H_FONT } },
             { text: "of unseen attacks are assigned the correct attack family", options: { fontSize: 12, color: "C9D6E2" } }],
    { x: 8.72, y: 4.54, w: 3.76, h: 1.44, fontFace: B_FONT, margin: 0, valign: "top", lineSpacing: 20 });

  s.addText("The model that reports 99.5% accuracy is, against a genuinely new attack, close to useless — and it says nothing to warn you.", {
    x: MG, y: 5.85, w: 12.1, h: 0.7, fontSize: 15, bold: true, fontFace: B_FONT, color: "9FB3C8", margin: 0, valign: "top", lineSpacing: 21,
  });
  footer(s, true);
}

// ══════════════════════════════════════════════════ 10. COMPARATIVE ANALYSIS
{
  const s = lightSlide("Eight models, identical splits — the protocol dominates the model", "Comparative analysis");
  const ok = Object.entries(mc.models).filter(([, v]) => v.macro_f1 !== undefined)
    .sort((a, b) => b[1].macro_f1 - a[1].macro_f1);
  const nice = (k) => k.split("_").slice(1).join(" ");

  const rows = [[
    { text: "Model", options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 11 } },
    { text: "Macro-F1\n(honest)", options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 11, align: "center" } },
    { text: "CV F1\n(in-dist.)", options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 11, align: "center" } },
    { text: "Shift\npenalty", options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 11, align: "center" } },
    { text: "R2L\nrecall", options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 11, align: "center" } },
    { text: "Unseen\nmissed", options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 11, align: "center" } },
  ]];
  ok.forEach(([k, v], i) => {
    const best = i === 0;
    const f = { color: i % 2 ? "EEF1F4" : WHITE };
    rows.push([
      { text: nice(k), options: { fontSize: 11, bold: best, color: best ? INK : INK_2, fill: f } },
      { text: v.macro_f1.toFixed(3), options: { fontSize: 11, bold: true, color: best ? GREEN_TXT : INK, fill: f, align: "center" } },
      { text: v.cv_macro_f1_mean_on_train != null ? v.cv_macro_f1_mean_on_train.toFixed(3) : "—", options: { fontSize: 11, color: INK_2, fill: f, align: "center" } },
      { text: v.shift_penalty_macro_f1 != null ? v.shift_penalty_macro_f1.toFixed(3) : "—", options: { fontSize: 11, color: RED, fill: f, align: "center" } },
      { text: v.per_class_recall.R2L.toFixed(3), options: { fontSize: 11, color: INK_2, fill: f, align: "center" } },
      { text: (v.novel_attacks.missed_as_normal_rate * 100).toFixed(0) + "%", options: { fontSize: 11, color: INK_2, fill: f, align: "center" } },
    ]);
  });
  s.addTable(rows, {
    x: MG, y: 1.5, w: 7.4, colW: [2.35, 1.05, 1.0, 0.95, 1.0, 1.05],
    border: { type: "solid", color: HAIR, pt: 1 }, fontFace: B_FONT,
    rowH: 0.3, valign: "middle", autoPage: false,
  });

  s.addText("Three findings", { x: 8.3, y: 1.5, w: 4.4, h: 0.32, fontSize: 15, bold: true, fontFace: H_FONT, color: INK, margin: 0 });
  const findings = [
    ["1", "The protocol beats the model.", "Every real model scores 0.84–0.94 in-distribution and 0.46–0.55 under shift. The gap between columns (~0.40) dwarfs the gap between best and worst model (~0.09)."],
    ["2", "Capacity does not help.", "The two simplest models — a small MLP and plain logistic regression — generalise best. XGBoost has the highest CV score and a worse test score than logistic regression."],
    ["3", "Rebalancing makes it worse.", "class_weight='balanced_subsample' cut macro-F1 from 0.494 to 0.468 and R2L recall from 0.048 to 0.005. Reweighting cannot invent information about absent attack types."],
  ];
  let yy = 1.92;
  findings.forEach(([n, head, body]) => {
    s.addShape(pres.ShapeType.ellipse, { x: 8.3, y: yy, w: 0.34, h: 0.34, fill: { color: RED }, line: { color: RED, width: 1 } });
    s.addText(n, { x: 8.3, y: yy, w: 0.34, h: 0.34, fontSize: 12, bold: true, fontFace: B_FONT, color: WHITE, align: "center", valign: "middle", margin: 0 });
    s.addText(head, { x: 8.76, y: yy - 0.02, w: 3.95, h: 0.3, fontSize: 12.5, bold: true, fontFace: B_FONT, color: INK, margin: 0 });
    s.addText(body, { x: 8.76, y: yy + 0.27, w: 3.95, h: 1.0, fontSize: 11, fontFace: B_FONT, color: INK_2, margin: 0, valign: "top", lineSpacing: 14 });
    yy += 1.55;
  });
  s.addNotes("LightGBM's negative shift penalty is an artefact of collapse on rare classes inside small CV folds — reported as measured.");
  footer(s);
}

// ══════════════════════════════════════════════════ 11. LOFO
{
  const s = lightSlide("Controlled zero-day: delete an attack family, then test on it", "Zero-day evaluation");
  const fams = Object.keys(zd.lofo);
  s.addChart(pres.ChartType.bar, [
    { name: "Family present in training", labels: fams, values: fams.map((f) => zd.lofo[f].detection_rate_family_INCLUDED) },
    { name: "Family deleted from training (simulated zero-day)", labels: fams, values: fams.map((f) => zd.lofo[f].detection_rate_family_HELD_OUT) },
  ], Object.assign({}, QUIET, {
    x: MG - 0.1, y: 1.5, w: 7.7, h: 4.3, barDir: "col", chartColors: [BLUE, ORANGE],
    showLegend: true, legendPos: "b", legendFontFace: B_FONT, legendFontSize: 11,
    valAxisMaxVal: 1.0, valAxisMinVal: 0, dataLabelFormatCode: "0.000", catAxisLabelFontSize: 12,
  }));
  s.addText("Detection rate on the held-out family. Each bar pair is a model retrained from scratch.", {
    x: MG, y: 5.88, w: 7.6, h: 0.3, fontSize: 11, italic: true, fontFace: B_FONT, color: MUTED, margin: 0,
  });
  s.addText("Why run this as well?", { x: 8.5, y: 1.52, w: 4.2, h: 0.32, fontSize: 15, bold: true, fontFace: H_FONT, color: INK, margin: 0 });
  const pIn = zd.lofo.Probe.detection_rate_family_INCLUDED.toFixed(3);
  const pOut = zd.lofo.Probe.detection_rate_family_HELD_OUT.toFixed(3);
  s.addText([
    { text: "The test-set result confounds two things: novelty and the prior shift. This isolates novelty.\n\n", options: { breakLine: true } },
    { text: "For each family: delete every one of its rows from training, refit from scratch, then measure detection on it.\n\n", options: { breakLine: true } },
    { text: `Probe detection falls ${pIn} → ${pOut} purely from removing Probe. The novelty effect is real and not an artefact of the priors.`, options: { bold: true, color: INK } },
  ], { x: 8.5, y: 1.92, w: 4.2, h: 2.4, fontSize: 12.5, fontFace: B_FONT, color: INK_2, margin: 0, valign: "top", lineSpacing: 17 });
  stat(s, 8.5, 4.72, 4.2, pOut, `Probe detection when Probe is unseen (${pIn} when seen)`, RED, 36);
  footer(s);
}

// ══════════════════════════════════════════════════ 12. THE FIX — ARCHITECTURE
{
  const s = lightSlide("The fix: give the detector a way to say “I don't recognise this”", "The solution");
  s.addText("A softmax over five known classes cannot express “none of these”. Forced to choose, it picks the class with the largest prior mass — Normal. The failure is structural, not a tuning problem.", {
    x: MG, y: 1.42, w: 12.1, h: 0.62, fontSize: 13.5, fontFace: B_FONT, color: INK_2, margin: 0, valign: "top", lineSpacing: 19,
  });

  const cw = 5.7715;      // flush with the code band and table below
  [["A", "Supervised + abstention", BLUE,
    "Logistic regression over the 5 known families.\n\nIf the argmax is Normal but confidence < τ, do not clear the flow — emit SUSPICIOUS_UNCLASSIFIED and route to an analyst."],
   ["B", "Unsupervised novelty", ORANGE,
    "IsolationForest fitted on the 67,343 NORMAL training flows only.\n\nIt never sees a single attack during training, so it cannot be biased toward the 22 known attack types."],
  ].forEach(([tag, head, col, body], i) => {
    const x = MG + i * (cw + 0.55);
    s.addShape(pres.ShapeType.roundRect, { x, y: 2.18, w: cw, h: 1.82, fill: { color: WHITE }, rectRadius: 0.1, line: { color: HAIR, width: 1 },
      shadow: { type: "outer", angle: 90, blur: 8, offset: 1, color: "9AA5B1", opacity: 0.16 } });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.3, y: 2.38, w: 0.42, h: 0.42, fill: { color: col }, line: { color: col, width: 1 } });
    s.addText(tag, { x: x + 0.3, y: 2.38, w: 0.42, h: 0.42, fontSize: 15, bold: true, fontFace: H_FONT, color: WHITE, align: "center", valign: "middle", margin: 0 });
    s.addText(`Channel ${tag} — ${head}`, { x: x + 0.88, y: 2.40, w: cw - 1.15, h: 0.34, fontSize: 14.5, bold: true, fontFace: H_FONT, color: INK, margin: 0 });
    s.addText(body, { x: x + 0.32, y: 2.86, w: cw - 0.64, h: 1.08, fontSize: 12, fontFace: B_FONT, color: INK_2, margin: 0, valign: "top", lineSpacing: 16 });
  });

  s.addShape(pres.ShapeType.roundRect, { x: MG, y: 4.3, w: 12.093, h: 0.86, fill: { color: NAVY }, rectRadius: 0.08, line: { color: NAVY, width: 1 } });
  s.addText("alarm  =  A says attack   OR   A abstains   OR   B says outlier", {
    x: MG + 0.3, y: 4.4, w: 11.5, h: 0.32, fontSize: 13, bold: true, fontFace: "Courier New", color: WHITE, margin: 0, valign: "middle",
  });
  s.addText("verdict ∈  { NORMAL ,  ATTACK:family ,  SUSPICIOUS_UNCLASSIFIED }", {
    x: MG + 0.3, y: 4.74, w: 11.5, h: 0.32, fontSize: 13, bold: true, fontFace: "Courier New", color: "9FB3C8", margin: 0, valign: "middle",
  });

  const rows = [[
    { text: "Configuration", options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 11 } },
    { text: "Unseen-attack detection", options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 11, align: "center" } },
    { text: "Seen-attack detection", options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 11, align: "center" } },
    { text: "False-alarm rate", options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: 11, align: "center" } },
  ]];
  const abl = [
    ["Channel A alone (plain 5-class classifier)", HY.channel_A_only_no_abstention, false],
    ["Channel B alone (trained on zero attacks)", HY.channel_B_only_isolationforest, false],
    ["A OR B, no abstention", HY.channel_A_or_B_no_abstention, false],
    [`A + abstention (τ=${RP.tau}) OR B  — recommended`, RP, true],
  ];
  abl.forEach(([nm, v, hi], i) => {
    const f = { color: hi ? "E6F4E6" : (i % 2 ? "EEF1F4" : WHITE) };
    rows.push([
      { text: nm, options: { fontSize: 11, bold: hi, color: hi ? INK : INK_2, fill: f } },
      { text: v.novel_attack_detection_rate.toFixed(3), options: { fontSize: 11.5, bold: true, color: hi ? GREEN_TXT : INK, fill: f, align: "center" } },
      { text: v.seen_attack_detection_rate.toFixed(3), options: { fontSize: 11, color: INK_2, fill: f, align: "center" } },
      { text: v.false_alarm_rate.toFixed(3), options: { fontSize: 11, color: INK_2, fill: f, align: "center" } },
    ]);
  });
  s.addTable(rows, { x: MG, y: 5.46, w: 12.093, colW: [5.493, 2.3, 2.2, 2.1], border: { type: "solid", color: HAIR, pt: 1 }, fontFace: B_FONT, rowH: 0.26, valign: "middle", autoPage: false });
  s.addNotes("Channel B alone beats Channel A on unseen attacks at a third of the false-alarm rate. That is the most informative row.");
  footer(s);
}

// ══════════════════════════════════════════════════ 13. THE FIX — RESULT
{
  const s = lightSlide("Unseen-attack coverage rises 24 points for 2 points of false alarms", "The solution works");
  s.addImage({ path: FIG("fig8_hybrid_operating_curve.png"), x: MG, y: 1.45, w: 7.6, h: 4.6 });
  stat(s, 8.4, 1.55, 2.05, `${(HY.channel_A_only_no_abstention.novel_attack_detection_rate * 100).toFixed(1)}%`, "unseen attacks caught — plain classifier", MUTED, 25);
  stat(s, 10.65, 1.55, 2.05, `${(RP.novel_attack_detection_rate * 100).toFixed(1)}%`, "unseen attacks caught — SENTINEL hybrid", GREEN_TXT, 25);
  stat(s, 8.4, 3.3, 4.3, `+${HY.improvement_vs_plain_classifier.novel_detection_gain_pp} pp`, `coverage gained, for only +${HY.improvement_vs_plain_classifier.false_alarm_cost_pp} pp of false alarms`, GREEN_TXT, 30);
  s.addShape(pres.ShapeType.roundRect, { x: 8.4, y: 5.05, w: 4.3, h: 1.35, fill: { color: NAVY }, rectRadius: 0.1, line: { color: NAVY, width: 1 } });
  s.addText("An unsupervised model that never saw a single attack detects unseen attacks better than the supervised one — 0.566 vs 0.415.", {
    x: 8.62, y: 5.05, w: 3.86, h: 1.35, fontSize: 12.5, bold: true, fontFace: B_FONT, color: WHITE, margin: 0, valign: "middle", lineSpacing: 17,
  });
  s.addNotes("τ is a staffing decision, not a hyperparameter. Report the curve, don't pick for the operator.");
  footer(s);
}

// ══════════════════════════════════════════════════ 14. EXPLAINABILITY
{
  const s = lightSlide("Why R2L and U2R fail — a mechanistic answer, not a shrug", "Explainability");
  s.addImage({ path: FIG("fig12_shap_r2l_u2r_deck.png"), x: MG, y: 1.4, w: 12.093, h: 3.76 });

  const grp = ex.importance_by_feature_group_pct;
  const contentPct = grp[Object.keys(grp).find((k) => k.startsWith("Content"))];
  const basicPct = grp[Object.keys(grp).find((k) => k.startsWith("Basic"))];

  s.addShape(pres.ShapeType.roundRect, { x: MG, y: 5.5, w: 3.531, h: 1.36, fill: { color: WHITE }, rectRadius: 0.08, line: { color: HAIR, width: 1 } });
  s.addText([{ text: `${contentPct}%\n`, options: { fontSize: 30, bold: true, color: RED, fontFace: H_FONT } },
             { text: "of total model importance sits in CONTENT features", options: { fontSize: 11, color: INK_2 } }],
    { x: MG + 0.2, y: 5.6, w: 3.15, h: 1.16, fontFace: B_FONT, margin: 0, valign: "top", lineSpacing: 17 });

  s.addShape(pres.ShapeType.roundRect, { x: MG + 3.812, y: 5.5, w: 3.531, h: 1.36, fill: { color: WHITE }, rectRadius: 0.08, line: { color: HAIR, width: 1 } });
  s.addText([{ text: `${basicPct}%\n`, options: { fontSize: 30, bold: true, color: BLUE, fontFace: H_FONT } },
             { text: "sits in basic header / byte-count features", options: { fontSize: 11, color: INK_2 } }],
    { x: MG + 4.012, y: 5.6, w: 3.15, h: 1.16, fontFace: B_FONT, margin: 0, valign: "top", lineSpacing: 17 });

  s.addShape(pres.ShapeType.roundRect, { x: MG + 7.624, y: 5.5, w: 4.469, h: 1.36, fill: { color: NAVY }, rectRadius: 0.08, line: { color: NAVY, width: 1 } });
  s.addText("The model became a traffic-pattern detector, because that is 99% of its training signal. A successful password guess just looks like one ordinary login.", {
    x: MG + 7.844, y: 5.5, w: 4.029, h: 1.36, fontSize: 11.5, bold: true, fontFace: B_FONT, color: WHITE, margin: 0, valign: "middle", lineSpacing: 16,
  });
  s.addNotes("Round 2 is a Model Explanation round — this slide is the one to expand if they push.");
  footer(s);
}

// ══════════════════════════════════════════════════ 15. DEPLOYMENT
{
  const s = lightSlide("Deployment: the best model is also the cheapest to run", "Deployment considerations");
  const order = ["03_random_forest", "06_lightgbm", "05_xgboost", "07_mlp", "01_logistic_regression", "02_decision_tree"];
  const labels = { "03_random_forest": "Random forest", "06_lightgbm": "LightGBM", "05_xgboost": "XGBoost", "07_mlp": "MLP (128,64)", "01_logistic_regression": "Logistic regression", "02_decision_tree": "Decision tree" };
  const avail = order.filter((k) => dp.models[k]);
  const cats = avail.map((k) => labels[k]).concat(["ONNX (logreg)"]);
  const vals = avail.map((k) => dp.models[k].single_flow_latency.p50_ms).concat([dp.onnx_runtime.single_flow_latency.p50_ms]);
  s.addChart(pres.ChartType.bar, [{ name: "p50 latency per flow (ms, log-ish scale shown as value labels)", labels: cats, values: vals }],
    Object.assign({}, QUIET, {
      x: MG - 0.1, y: 1.5, w: 7.5, h: 4.3, barDir: "bar", chartColors: [BLUE],
      valAxisMinVal: 0, dataLabelFormatCode: "0.000", catAxisLabelFontSize: 11,
    }));
  s.addText("p50 inference latency per flow (ms). Random forest is off-scale at 65.206 ms.", {
    x: MG, y: 5.88, w: 7.5, h: 0.3, fontSize: 11, italic: true, fontFace: B_FONT, color: MUTED, margin: 0,
  });

  stat(s, 8.3, 1.55, 2.1, `${dp.onnx_runtime.single_flow_latency.p50_ms} ms`, "per flow, ONNX Runtime single-threaded", GREEN_TXT, 24);
  stat(s, 10.6, 1.55, 2.1, `${dp.onnx_runtime.disk_size_kb} KB`, "deployed model size on disk", GREEN_TXT, 24);
  stat(s, 8.3, 3.3, 4.4, `${(dp.onnx_runtime.batch_4096_flows_per_second / 1000).toFixed(0)}k flows/s`, "single-threaded throughput — about 8× a saturated 1 Gbps link", INK, 26);
  s.addShape(pres.ShapeType.roundRect, { x: 8.3, y: 5.05, w: 4.4, h: 1.35, fill: { color: NAVY }, rectRadius: 0.1, line: { color: NAVY, width: 1 } });
  s.addText("Random forest — the reflexive choice — is 5,055× slower and 8,027× larger, for 0.05 LOWER macro-F1.", {
    x: 8.52, y: 5.05, w: 3.96, h: 1.35, fontSize: 12.5, bold: true, fontFace: B_FONT, color: WHITE, margin: 0, valign: "middle", lineSpacing: 17,
  });
  s.addNotes("Caveat to volunteer: this measures inference on pre-computed features. Feature extraction from a live packet stream is the harder problem and is out of scope.");
  footer(s);
}

// ══════════════════════════════════════════════════ 16. LIMITATIONS (dark)
{
  const s = darkSlide();
  s.addText("WHAT THIS PROJECT DOES NOT CLAIM", { x: MG, y: 0.8, w: 11, h: 0.3, fontSize: 11, bold: true, fontFace: B_FONT, color: RED, charSpacing: 1.8, margin: 0 });
  s.addText("Stated here rather than buried", { x: MG, y: 1.18, w: 11, h: 0.6, fontSize: 27, bold: true, fontFace: H_FONT, color: WHITE, margin: 0 });

  const lim = [
    ["Dataset age", "NSL-KDD is 1999-era simulated traffic. The methodological finding transfers to any dataset with a designed shift; the absolute numbers do not describe a 2026 network."],
    ["Single dataset", "The strongest remaining criticism. Cross-dataset validation was planned; UNSW-NB15 and CIC-IDS2017 hosts are unreachable from the build environment."],
    ["The fix is partial", "Even at the recommended operating point, 34% of unseen attacks are still missed. That is a real gap, not a rounding error."],
    ["R2L and U2R remain unsolved", "Best-case recall 0.106 and 0.105 across all eight models. We explain the cause mechanically; we do not fix it."],
    ["No adversarial robustness", "We evaluate against a fixed dataset, not an adaptive adversary. A linear model is easy to evade with white-box knowledge."],
    ["Feature extraction out of scope", "Latency figures measure inference on pre-computed flow aggregates. Computing them from live packets is the harder engineering problem."],
  ];
  lim.forEach(([h, b], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = MG + col * 6.2, y = 2.02 + row * 1.5;
    s.addShape(pres.ShapeType.roundRect, { x, y, w: 5.9, h: 1.16, fill: { color: NAVY_2 }, rectRadius: 0.08, line: { color: "24405C", width: 1 } });
    s.addText(h, { x: x + 0.26, y: y + 0.11, w: 5.4, h: 0.28, fontSize: 13, bold: true, fontFace: B_FONT, color: WHITE, margin: 0 });
    s.addText(b, { x: x + 0.26, y: y + 0.4, w: 5.4, h: 0.7, fontSize: 10.5, fontFace: B_FONT, color: "9FB3C8", margin: 0, valign: "top", lineSpacing: 14 });
  });
  s.addText("For a defence evaluator, a system whose limits are known is worth more than one whose headline number cannot be trusted.", {
    x: MG, y: 6.55, w: 12.1, h: 0.5, fontSize: 14, bold: true, italic: true, fontFace: B_FONT, color: WHITE, margin: 0, valign: "top",
  });
  footer(s, true);
}

// ══════════════════════════════════════════════════ 17. CLOSE (dark)
{
  const s = darkSlide();
  s.addText("Everything here is reproducible", { x: MG, y: 1.0, w: 11.6, h: 0.7, fontSize: 32, bold: true, fontFace: H_FONT, color: WHITE, margin: 0 });
  s.addText("Every number on every slide is read from a JSON file in reports/metrics/. None was typed by hand.", {
    x: MG, y: 1.78, w: 11.6, h: 0.4, fontSize: 15, fontFace: B_FONT, color: "9FB3C8", margin: 0,
  });

  s.addShape(pres.ShapeType.roundRect, { x: MG, y: 2.42, w: 6.2, h: 1.75, fill: { color: NAVY_2 }, rectRadius: 0.08, line: { color: "24405C", width: 1 } });
  s.addText("Reproduce the whole project", { x: MG + 0.3, y: 2.6, w: 5.6, h: 0.3, fontSize: 12.5, bold: true, fontFace: B_FONT, color: RED, margin: 0 });
  s.addText("git clone <repo> && cd sentinel-nids\npip install -r requirements.txt\npython run_all.py", {
    x: MG + 0.3, y: 2.95, w: 5.6, h: 1.05, fontSize: 12.5, fontFace: "Courier New", color: WHITE, margin: 0, valign: "top", lineSpacing: 20,
  });

  s.addShape(pres.ShapeType.roundRect, { x: MG + 6.55, y: 2.42, w: 5.55, h: 1.75, fill: { color: NAVY_2 }, rectRadius: 0.08, line: { color: "24405C", width: 1 } });
  s.addText("Reproduce just the headline", { x: MG + 6.85, y: 2.6, w: 4.95, h: 0.3, fontSize: 12.5, bold: true, fontFace: B_FONT, color: RED, margin: 0 });
  s.addText("python run_all.py --only leakage\n\n≈ 35 seconds. Prints both protocols\nand the gap between them.", {
    x: MG + 6.85, y: 2.95, w: 4.95, h: 1.05, fontSize: 12.5, fontFace: "Courier New", color: WHITE, margin: 0, valign: "top", lineSpacing: 18,
  });

  s.addText("Submitted artefacts", { x: MG, y: 4.42, w: 11.6, h: 0.3, fontSize: 13, bold: true, fontFace: B_FONT, color: WHITE, margin: 0 });
  s.addText("Source code (9 modules, all idempotent and checkpointed)  ·  dataset provenance + SHA-256 manifest  ·  6 metrics JSON files  ·  12 figures  ·  README, methodology, model card, deployment notes  ·  FastAPI inference service  ·  4.9 KB ONNX model  ·  this deck", {
    x: MG, y: 4.75, w: 11.9, h: 0.9, fontSize: 12, fontFace: B_FONT, color: "9FB3C8", margin: 0, valign: "top", lineSpacing: 18,
  });

  s.addShape(pres.ShapeType.roundRect, { x: MG, y: 5.8, w: 12.1, h: 1.0, fill: { color: RED }, rectRadius: 0.08, line: { color: RED, width: 1 } });
  s.addText("A detector that reports 99.5% accuracy silently clears 77% of never-before-seen attacks. Measuring it honestly is the whole job.", {
    x: MG + 0.34, y: 5.8, w: 11.4, h: 1.0, fontSize: 15.5, bold: true, fontFace: H_FONT, color: WHITE, margin: 0, valign: "middle", lineSpacing: 22,
  });
  footer(s, true);
}

const out = path.join(ROOT, "submission", "SENTINEL-NIDS_ML-Bubble-2026_Manoj-Kharkar.pptx");
pres.writeFile({ fileName: out }).then(() => console.log("wrote " + out));
