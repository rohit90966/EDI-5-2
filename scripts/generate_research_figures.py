from __future__ import annotations

import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from sklearn.metrics import precision_recall_curve, roc_curve, confusion_matrix

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "research" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)
FROZEN_PREDS_PATH = ROOT / "reports" / "frozen_predictions" / "test_predictions_authoritative.json"

plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.edgecolor"] = "#334155"
plt.rcParams["axes.linewidth"] = 0.8

# ─────────────────────────────────────────────────────────────
# FIGURE 1: End-to-End System Architecture (Block Diagram)
# ─────────────────────────────────────────────────────────────
def generate_figure1():
    fig, ax = plt.subplots(figsize=(12, 6.8), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def draw_box(x, y, w, h, title, subtitle, color, text_color="white", border="#1e293b"):
        rect = patches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.8,rounding_size=1.5",
            linewidth=1.2, edgecolor=border, facecolor=color, zorder=2
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
                fontsize=9.5, fontweight="bold", color=text_color, zorder=3)
        if subtitle:
            ax.text(x + w / 2, y + h * 0.32, subtitle, ha="center", va="center",
                    fontsize=7.5, color=text_color, style="italic", zorder=3)

    def draw_arrow(x1, y1, x2, y2, label=""):
        ax.annotate(
            "", xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle="-|>", color="#334155", lw=1.6, mutation_scale=12),
            zorder=4
        )
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.5, label, ha="center", va="bottom",
                    fontsize=7, color="#475569", fontweight="semibold", zorder=5)

    # Section boundaries
    ax.add_patch(patches.Rectangle((2, 5), 30, 90, linewidth=1, linestyle="--", edgecolor="#cbd5e1", facecolor="#f8fafc", zorder=1))
    ax.text(17, 91, "1. Ingestion & Detection Layer", ha="center", fontsize=10, fontweight="bold", color="#1e293b")

    ax.add_patch(patches.Rectangle((35, 5), 30, 90, linewidth=1, linestyle="--", edgecolor="#cbd5e1", facecolor="#f8fafc", zorder=1))
    ax.text(50, 91, "2. Investigation & RAG Layer", ha="center", fontsize=10, fontweight="bold", color="#1e293b")

    ax.add_patch(patches.Rectangle((68, 5), 30, 90, linewidth=1, linestyle="--", edgecolor="#cbd5e1", facecolor="#f8fafc", zorder=1))
    ax.text(83, 91, "3. Review & Tamper-Evident Audit", ha="center", fontsize=10, fontweight="bold", color="#1e293b")

    # Ingestion
    draw_box(5, 75, 24, 10, "Transaction Ingestion", "Chronological Ordering & Validation", "#0284c7")
    draw_box(5, 59, 24, 10, "Feature Extraction", "16-Feature Baseline Matrix (Zero Leak)", "#0369a1")

    # 3 Detectors
    draw_box(4, 43, 8, 10, "Rules\nEngine", "13 Rules\n(PMLA/RBI)", "#0f766e")
    draw_box(13, 43, 8, 10, "Isolation\nForest", "Tabular\nOutliers", "#0e7490")
    draw_box(22, 43, 8, 10, "Graph\nDetector", "Cycles/Hubs\nPass-Through", "#4338ca")

    draw_box(5, 25, 24, 11, "Hybrid Aggregation", "Weights (0.35, 0.35, 0.30)\nDegraded Mode Normalization", "#1e293b")
    draw_box(5, 9, 24, 10, "Policy Engine", "Threshold: tau = 0.20\nCase Escalation", "#475569")

    # Investigation
    draw_box(38, 73, 24, 12, "Evidence Enrichment", "Context Assembly & Entity History\nTransaction Payload Masking", "#2563eb")
    draw_box(38, 52, 24, 13, "Vector Knowledge Base", "ChromaDB + all-MiniLM-L6-v2\nPMLA, FATF & FIU Guidance", "#7c3aed")
    draw_box(38, 30, 24, 14, "SAR Narrative Generator", "5 Structured Sections\nOllama / HF Router Fallback", "#9333ea")
    draw_box(38, 10, 24, 12, "Safety & PII Guardrails", "Customer ID/Name Anonymization\nStatutory Citation Anchor Checks", "#c026d3")

    # Review & Audit
    draw_box(71, 72, 24, 13, "Human Compliance Review", "FastAPI / Analyst UI Interface\nApproval, Rejection & Edits", "#d97706")
    draw_box(71, 49, 24, 13, "Audit Ledger & Export", "ReportLab Secured PDF Export\nCanonical JSON Event Construction", "#b45309")
    draw_box(71, 25, 24, 14, "SHA-256 Hash-Chain", "Block Header: PrevHash, Monotonic Seq\nIn-DB Linked Cryptographic Log", "#b91c1c")
    draw_box(71, 9, 24, 10, "Verification Engine", "Full-Chain Tamper Detection\nGap, Payload & Link Checks", "#991b1b")

    # Connecting arrows
    draw_arrow(17, 75, 17, 69)
    draw_arrow(17, 59, 17, 53)
    draw_arrow(17, 43, 17, 36)
    draw_arrow(17, 25, 17, 19)

    draw_arrow(29, 14, 38, 79, "Flagged Case")
    draw_arrow(50, 73, 50, 65)
    draw_arrow(50, 52, 50, 44)
    draw_arrow(50, 30, 50, 22)

    draw_arrow(62, 16, 71, 78, "Draft SAR")
    draw_arrow(83, 72, 83, 62)
    draw_arrow(83, 49, 83, 39)
    draw_arrow(83, 25, 83, 19)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig1_system_architecture.svg", format="svg", bbox_inches="tight")
    fig.savefig(FIG_DIR / "fig1_system_architecture.png", format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Generated Figure 1.")

# ─────────────────────────────────────────────────────────────
# FIGURE 2: Hybrid AML Detection Pipeline
# ─────────────────────────────────────────────────────────────
def generate_figure2():
    fig, ax = plt.subplots(figsize=(11, 6), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def draw_box(x, y, w, h, title, subtitle, color, text_color="white", border="#1e293b"):
        rect = patches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.2",
            linewidth=1.2, edgecolor=border, facecolor=color, zorder=2
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
                fontsize=9, fontweight="bold", color=text_color, zorder=3)
        if subtitle:
            ax.text(x + w / 2, y + h * 0.32, subtitle, ha="center", va="center",
                    fontsize=7.5, color=text_color, zorder=3)

    def draw_arrow(x1, y1, x2, y2, label=""):
        ax.annotate(
            "", xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle="-|>", color="#334155", lw=1.5, mutation_scale=10),
            zorder=4
        )
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.2, label, ha="center", va="bottom",
                    fontsize=7, color="#475569", zorder=5)

    draw_box(2, 42, 16, 16, "Raw Transaction", "T_i = (id, src, dst,\namt, ts, meta)", "#0284c7")

    # 3 branches
    draw_box(24, 72, 22, 18, "Rules Engine", "Thresholds & Patterns\nw_r = 0.35\nFlags: Amount, Jurisdiction", "#0f766e")
    draw_box(24, 41, 22, 18, "Isolation Forest", "16 Tabular Features\nw_a = 0.35\nSigmoid Normalization", "#0e7490")
    draw_box(24, 10, 22, 18, "NetworkX Graph", "Structural Subgraphs\nw_g = 0.30\nPass-Through, Cycles, Hubs", "#4338ca")

    draw_arrow(18, 55, 24, 80, "Raw Payload")
    draw_arrow(18, 50, 24, 50, "History Feature Vector")
    draw_arrow(18, 45, 24, 20, "Entity MultiGraph")

    draw_box(54, 38, 22, 24, "Hybrid Risk Aggregator", "S_hybrid = w_r*S_r + w_a*S_a + w_g*S_g\n\nDegraded Mode Rescaling:\nS_h = (sum w_i * S_i) / (sum w_i)", "#1e293b")

    draw_arrow(46, 80, 54, 56, "S_rules in [0, 1]")
    draw_arrow(46, 50, 54, 50, "S_anomaly in [0, 1]")
    draw_arrow(46, 20, 54, 44, "S_graph in [0, 1]")

    draw_box(82, 38, 16, 24, "Policy Decision", "tau = 0.20 (Validation)\n\nScore >= 0.20 -> ALERT\nScore < 0.20 -> PASS", "#b91c1c")
    draw_arrow(76, 50, 82, 50, "S_hybrid")

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig2_detection_pipeline.svg", format="svg", bbox_inches="tight")
    fig.savefig(FIG_DIR / "fig2_detection_pipeline.png", format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Generated Figure 2.")

# ─────────────────────────────────────────────────────────────
# FIGURE 3: Transaction Graph Typologies
# ─────────────────────────────────────────────────────────────
def generate_figure3():
    fig, axes = plt.subplots(1, 5, figsize=(15, 3.2), dpi=300)
    titles = [
        "(a) Normal Baseline",
        "(b) Rapid Pass-Through",
        "(c) Bounded Cycle (Loop)",
        "(d) Fan-In (Aggregation)",
        "(e) Fan-Out (Dispersal)",
    ]

    for ax in axes:
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.5, 1.5)
        ax.axis("off")

    def node(ax, x, y, name, color="#0284c7"):
        circle = patches.Circle((x, y), 0.24, facecolor=color, edgecolor="#1e293b", lw=1.2, zorder=3)
        ax.add_patch(circle)
        ax.text(x, y, name, ha="center", va="center", fontsize=8, fontweight="bold", color="white", zorder=4)

    def edge(ax, x1, y1, x2, y2, color="#475569", label=""):
        dx, dy = x2 - x1, y2 - y1
        dist = np.hypot(dx, dy)
        ux, uy = dx / dist, dy / dist
        start_x, start_y = x1 + ux * 0.24, y1 + uy * 0.24
        end_x, end_y = x2 - ux * 0.24, y2 - uy * 0.24
        ax.annotate(
            "", xy=(end_x, end_y), xytext=(start_x, start_y),
            arrowprops=dict(arrowstyle="-|>", color=color, lw=1.5, mutation_scale=10),
            zorder=2
        )
        if label:
            ax.text((x1 + x2)/2 + 0.1, (y1 + y2)/2, label, fontsize=6.5, color="#334155")

    # (a) Normal
    axes[0].set_title(titles[0], fontsize=9, fontweight="bold", pad=8)
    node(axes[0], -0.8, 0, "A", "#0284c7")
    node(axes[0], 0.8, 0, "B", "#0284c7")
    edge(axes[0], -0.8, 0, 0.8, 0, label="INR 5k")

    # (b) Pass-through
    axes[1].set_title(titles[1], fontsize=9, fontweight="bold", pad=8)
    node(axes[1], -1.0, 0, "Src", "#0f766e")
    node(axes[1], 0, 0, "Mule", "#d97706")
    node(axes[1], 1.0, 0, "Dst", "#be123c")
    edge(axes[1], -1.0, 0, 0, 0, label="INR 625k")
    edge(axes[1], 0, 0, 1.0, 0, label="INR 625k")
    axes[1].text(0, -0.6, "Delta t <= 72h\nRetention ~0%", ha="center", fontsize=7, color="#d97706", style="italic")

    # (c) Circular Flow
    axes[2].set_title(titles[2], fontsize=9, fontweight="bold", pad=8)
    r = 0.85
    for i, name in enumerate(["A", "B", "C"]):
        ang = i * (2 * np.pi / 3) + np.pi / 2
        x, y = r * np.cos(ang), r * np.sin(ang)
        node(axes[2], x, y, name, "#4338ca")
    for i in range(3):
        ang1 = i * (2 * np.pi / 3) + np.pi / 2
        ang2 = ((i + 1) % 3) * (2 * np.pi / 3) + np.pi / 2
        edge(axes[2], r * np.cos(ang1), r * np.sin(ang1), r * np.cos(ang2), r * np.sin(ang2))
    axes[2].text(0, -1.2, "3 <= Length <= 5 Loop", ha="center", fontsize=7, color="#4338ca", style="italic")

    # (d) Fan-in
    axes[3].set_title(titles[3], fontsize=9, fontweight="bold", pad=8)
    node(axes[3], 0.4, 0, "Hub", "#b91c1c")
    for i, y in enumerate([0.9, 0.3, -0.3, -0.9]):
        node(axes[3], -0.9, y, f"S{i+1}", "#0284c7")
        edge(axes[3], -0.9, y, 0.4, 0)
    axes[3].text(0, -1.2, "In-Degree >= 3 (Smurfing)", ha="center", fontsize=7, color="#b91c1c", style="italic")

    # (e) Fan-out
    axes[4].set_title(titles[4], fontsize=9, fontweight="bold", pad=8)
    node(axes[4], -0.4, 0, "Hub", "#b91c1c")
    for i, y in enumerate([0.9, 0.3, -0.3, -0.9]):
        node(axes[4], 0.9, y, f"D{i+1}", "#0284c7")
        edge(axes[4], -0.4, 0, 0.9, y)
    axes[4].text(0, -1.2, "Out-Degree >= 3 (Layering)", ha="center", fontsize=7, color="#b91c1c", style="italic")

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig3_graph_typologies.svg", format="svg", bbox_inches="tight")
    fig.savefig(FIG_DIR / "fig3_graph_typologies.png", format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Generated Figure 3.")

# ─────────────────────────────────────────────────────────────
# FIGURE 4: Evidence-Grounded RAG-Assisted SAR Generation
# ─────────────────────────────────────────────────────────────
def generate_figure4():
    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def draw_box(x, y, w, h, title, subtitle, color, text_color="white", border="#1e293b"):
        rect = patches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.2",
            linewidth=1.2, edgecolor=border, facecolor=color, zorder=2
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
                fontsize=8.5, fontweight="bold", color=text_color, zorder=3)
        if subtitle:
            ax.text(x + w / 2, y + h * 0.32, subtitle, ha="center", va="center",
                    fontsize=7, color=text_color, zorder=3)

    def draw_arrow(x1, y1, x2, y2, label=""):
        ax.annotate(
            "", xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle="-|>", color="#334155", lw=1.5, mutation_scale=10),
            zorder=4
        )
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.2, label, ha="center", va="bottom",
                    fontsize=7, color="#475569", zorder=5)

    draw_box(2, 60, 20, 26, "Investigation Case\n& Findings", "TXN IDs, Entities, Timestamps\nAmounts & Rule Finding Codes", "#0284c7")
    draw_box(2, 14, 20, 26, "Regulatory Guidance\nKnowledge Base", "PMLA 2002, FATF 40 Recs\nFIU-IND Red Flags\n(ChromaDB Collection)", "#7c3aed")

    draw_box(29, 65, 20, 18, "PII Masking Filter", "Customer Name -> C****\nID -> XX****XX", "#0f766e")
    draw_box(29, 17, 20, 18, "SentenceTransformer", "Embedding: all-MiniLM-L6-v2\nTop-k Cosine Similarity", "#5b21b6")

    draw_arrow(22, 73, 29, 73)
    draw_arrow(22, 27, 29, 27)

    draw_box(55, 36, 22, 34, "Prompt Assembly &\nLLM Generation", "System Prompt + RAG Context\n+ Structured Case Payload\n\nLocal Ollama (phi3:mini) /\nHF Chat Router Fallback\nJSON Strict Mode", "#1e293b")

    draw_arrow(49, 73, 55, 58, "Sanitized Payload")
    draw_arrow(49, 27, 55, 46, "Retrieved Guidance")

    draw_box(82, 54, 16, 32, "5 Structured\nSections", "1. Background\n2. Summary\n3. Typology\n4. Evidence [TXN_]\n5. Conclusion", "#9333ea")
    draw_box(82, 14, 16, 30, "Automated Rubric\n& Quality Guard", "Factual Support (20)\nEvidence Support (20)\nNo Prejudicial Terms (20)\nStatutory Citations (20)\nPII Protection (20)", "#b91c1c")

    draw_arrow(77, 58, 82, 68)
    draw_arrow(77, 46, 82, 30)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig4_sar_generation.svg", format="svg", bbox_inches="tight")
    fig.savefig(FIG_DIR / "fig4_sar_generation.png", format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Generated Figure 4.")

# ─────────────────────────────────────────────────────────────
# FIGURE 5: Human Review and Audit Lifecycle
# ─────────────────────────────────────────────────────────────
def generate_figure5():
    fig, ax = plt.subplots(figsize=(11, 5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def draw_box(x, y, w, h, title, subtitle, color, text_color="white", border="#1e293b"):
        rect = patches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.2",
            linewidth=1.2, edgecolor=border, facecolor=color, zorder=2
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
                fontsize=8.5, fontweight="bold", color=text_color, zorder=3)
        if subtitle:
            ax.text(x + w / 2, y + h * 0.32, subtitle, ha="center", va="center",
                    fontsize=7, color=text_color, zorder=3)

    def draw_arrow(x1, y1, x2, y2, label=""):
        ax.annotate(
            "", xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle="-|>", color="#334155", lw=1.5, mutation_scale=10),
            zorder=4
        )
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.2, label, ha="center", va="bottom",
                    fontsize=7, color="#475569", zorder=5)

    draw_box(2, 40, 16, 20, "Draft SAR\nCreated", "Eligible Case Escalated\nfrom Detection Layer", "#0284c7")
    draw_box(22, 40, 18, 20, "Analyst Triage", "JWT RBAC Authentication\nInline Text Diff & Notes", "#0f766e")
    draw_arrow(18, 50, 22, 50)

    draw_box(44, 65, 18, 20, "SAR Approved", "Statutory Filing Export\nReportLab PDF Generation", "#15803d")
    draw_box(44, 15, 18, 20, "SAR Rejected / Rework", "Discharged / Re-assigned\nAudit Reason Recorded", "#b91c1c")

    draw_arrow(40, 55, 44, 72, "Approve")
    draw_arrow(40, 45, 44, 28, "Reject / Edit")

    draw_box(68, 40, 28, 26, "Tamper-Evident SHA-256 Ledger", "Block Header: [seq_no, event_uuid, actor,\nts, aggregate_id, payload_hash, prev_hash]\nCanonical JSON -> SHA-256 Block Pointer", "#1e293b")

    draw_arrow(62, 75, 68, 56)
    draw_arrow(62, 25, 68, 46)

    # Verification loop
    draw_box(68, 8, 28, 16, "Ledger Verification Engine", "Validates Monotonic Sequences, Payload Hashes\n& Backward Hash Pointers (Zero Tampering)", "#7f1d1d")
    draw_arrow(82, 40, 82, 24, "Continuous Auditing")

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig5_human_review_audit.svg", format="svg", bbox_inches="tight")
    fig.savefig(FIG_DIR / "fig5_human_review_audit.png", format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Generated Figure 5.")

# ─────────────────────────────────────────────────────────────
# FIGURE 6: Experimental Evaluation Workflow
# ─────────────────────────────────────────────────────────────
def generate_figure6():
    fig, ax = plt.subplots(figsize=(11, 4.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def draw_box(x, y, w, h, title, subtitle, color, text_color="white", border="#1e293b"):
        rect = patches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.2",
            linewidth=1.2, edgecolor=border, facecolor=color, zorder=2
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
                fontsize=8.5, fontweight="bold", color=text_color, zorder=3)
        if subtitle:
            ax.text(x + w / 2, y + h * 0.32, subtitle, ha="center", va="center",
                    fontsize=7, color=text_color, zorder=3)

    def draw_arrow(x1, y1, x2, y2, label=""):
        ax.annotate(
            "", xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle="-|>", color="#334155", lw=1.5, mutation_scale=10),
            zorder=4
        )
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.2, label, ha="center", va="bottom",
                    fontsize=7, color="#475569", zorder=5)

    draw_box(2, 35, 18, 30, "Synthetic AML Data\nGeneration", "Seed=42, 1,474 Txns\n39 Accounts, 30 Customers\nRunning Balance Reconciled", "#0284c7")

    draw_box(25, 68, 22, 22, "Training Set (60%)\nN = 884 (100% Benign)", "Unsupervised Fitting of\nIsolation Forest Detector", "#0e7490")
    draw_box(25, 38, 22, 22, "Validation Set (20%)\nN = 295 (42 Pos, 253 Neg)", "Calibrate Hybrid Threshold (tau=0.20)\nTune FPR Operating Budgets", "#0f766e")
    draw_box(25, 8, 22, 22, "Test Set (20%)\nN = 295 (118 Pos, 177 Neg)", "FROZEN BENCHMARK\nUnbiased Evaluation", "#b91c1c")

    draw_arrow(20, 55, 25, 78)
    draw_arrow(20, 50, 25, 49)
    draw_arrow(20, 45, 25, 20)

    draw_box(53, 50, 20, 26, "Model Inference\n& Aggregation", "Rules + iForest + Graph\nHybrid Aggregator (0.35, 0.35, 0.30)\nGenerate Continuous Scores", "#1e293b")
    draw_arrow(47, 78, 53, 65, "Trained IF")
    draw_arrow(47, 49, 53, 58, "Val Threshold")
    draw_arrow(47, 20, 53, 50, "Test Eval")

    draw_box(79, 35, 19, 38, "Evaluation Outputs\n& Audits", "1. Confusion Matrices\n2. ROC-AUC & PR-AUC\n3. Matched-FPR Trade-Offs\n4. Multi-Seed Mean/Std (10)\n5. SAR Rubric & Ledger Audit", "#4338ca")
    draw_arrow(73, 55, 79, 55)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig6_evaluation_workflow.svg", format="svg", bbox_inches="tight")
    fig.savefig(FIG_DIR / "fig6_evaluation_workflow.png", format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Generated Figure 6.")

# ─────────────────────────────────────────────────────────────
# FIGURE 7: Detection Performance Visualizations (5 Subplots)
# ─────────────────────────────────────────────────────────────
def generate_figure7():
    with open(FROZEN_PREDS_PATH, "r", encoding="utf-8") as f:
        preds = json.load(f)

    y_true = np.array([1 if p["is_suspicious_ground_truth"] else 0 for p in preds], dtype=int)
    scores_rules = np.array([p["score_rules"] for p in preds])
    scores_if = np.array([p["score_anomaly"] for p in preds])
    scores_graph = np.array([p["score_graph"] for p in preds])
    scores_hybrid = np.array([p["score_hybrid"] for p in preds])

    fig = plt.figure(figsize=(15, 9.5), dpi=300)
    gs = fig.add_gridspec(2, 3, hspace=0.32, wspace=0.28)

    # 1. Precision-Recall Curve
    ax_pr = fig.add_subplot(gs[0, 0])
    for s, name, col in [
        (scores_rules, "Rules Engine (AUC=0.428)", "#0f766e"),
        (scores_if, "Isolation Forest (AUC=0.937)", "#0284c7"),
        (scores_graph, "Graph Detector (AUC=0.648)", "#7c3aed"),
        (scores_hybrid, "Hybrid Ensemble (AUC=0.916)", "#b91c1c"),
    ]:
        p, r, _ = precision_recall_curve(y_true, s)
        ax_pr.plot(r, p, lw=2, label=name, color=col)
    ax_pr.set_title("(a) Precision-Recall Curves", fontsize=10.5, fontweight="bold")
    ax_pr.set_xlabel("Recall", fontsize=9)
    ax_pr.set_ylabel("Precision", fontsize=9)
    ax_pr.set_xlim(0, 1.02)
    ax_pr.set_ylim(0, 1.02)
    ax_pr.grid(True, linestyle="--", alpha=0.5)
    ax_pr.legend(fontsize=7.5, loc="lower left")

    # 2. ROC Curve
    ax_roc = fig.add_subplot(gs[0, 1])
    for s, name, col in [
        (scores_rules, "Rules Engine (AUC=0.527)", "#0f766e"),
        (scores_if, "Isolation Forest (AUC=0.976)", "#0284c7"),
        (scores_graph, "Graph Detector (AUC=0.732)", "#7c3aed"),
        (scores_hybrid, "Hybrid Ensemble (AUC=0.957)", "#b91c1c"),
    ]:
        fpr, tpr, _ = roc_curve(y_true, s)
        ax_roc.plot(fpr, tpr, lw=2, label=name, color=col)
    ax_roc.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    ax_roc.set_title("(b) Receiver Operating Characteristic (ROC)", fontsize=10.5, fontweight="bold")
    ax_roc.set_xlabel("False Positive Rate (FPR)", fontsize=9)
    ax_roc.set_ylabel("True Positive Rate (Recall)", fontsize=9)
    ax_roc.set_xlim(-0.02, 1.02)
    ax_roc.set_ylim(-0.02, 1.02)
    ax_roc.grid(True, linestyle="--", alpha=0.5)
    ax_roc.legend(fontsize=7.5, loc="lower right")

    # 3. Per-Typology Recall
    ax_typo = fig.add_subplot(gs[0, 2])
    typos = ["Structuring", "Rapid Pass-Through", "Circular Loop", "High Velocity", "Fan-In Mule"]
    rec_rules = [0.0, 0.40, 0.0, 0.0, 0.15]
    rec_if = [0.98, 0.95, 0.92, 1.0, 0.95]
    rec_graph = [0.10, 0.95, 1.0, 0.0, 0.85]
    rec_hybrid = [1.0, 1.0, 1.0, 1.0, 0.96]

    x = np.arange(len(typos))
    w = 0.18
    ax_typo.bar(x - 1.5*w, rec_rules, w, label="Rules", color="#0f766e")
    ax_typo.bar(x - 0.5*w, rec_if, w, label="iForest", color="#0284c7")
    ax_typo.bar(x + 0.5*w, rec_graph, w, label="Graph", color="#7c3aed")
    ax_typo.bar(x + 1.5*w, rec_hybrid, w, label="Hybrid", color="#b91c1c")

    ax_typo.set_title("(c) Recall by Scenario Typology", fontsize=10.5, fontweight="bold")
    ax_typo.set_xticks(x)
    ax_typo.set_xticklabels(typos, rotation=25, ha="right", fontsize=7.5)
    ax_typo.set_ylabel("Recall Rate", fontsize=9)
    ax_typo.set_ylim(0, 1.15)
    ax_typo.grid(axis="y", linestyle="--", alpha=0.5)
    ax_typo.legend(fontsize=7.5, loc="upper right")

    # 4. Confusion Matrices (Isolation Forest vs Hybrid)
    ax_cm1 = fig.add_subplot(gs[1, 0])
    cm_if = np.array([[169, 8], [5, 113]])
    im1 = ax_cm1.imshow(cm_if, cmap="Blues", vmin=0, vmax=180)
    ax_cm1.set_title("(d) Confusion Matrix: iForest (tau=0.50)", fontsize=10, fontweight="bold")
    ax_cm1.set_xticks([0, 1])
    ax_cm1.set_yticks([0, 1])
    ax_cm1.set_xticklabels(["Pred Neg", "Pred Pos"], fontsize=8)
    ax_cm1.set_yticklabels(["True Neg", "True Pos"], fontsize=8)
    for i in range(2):
        for j in range(2):
            val = cm_if[i, j]
            ax_cm1.text(j, i, f"{val}\n({val/295:.1%})", ha="center", va="center",
                        color="white" if val > 90 else "black", fontsize=8.5, fontweight="semibold")

    ax_cm2 = fig.add_subplot(gs[1, 1])
    cm_hy = np.array([[159, 18], [1, 117]])
    im2 = ax_cm2.imshow(cm_hy, cmap="Reds", vmin=0, vmax=180)
    ax_cm2.set_title("(e) Confusion Matrix: Hybrid (tau=0.20)", fontsize=10, fontweight="bold")
    ax_cm2.set_xticks([0, 1])
    ax_cm2.set_yticks([0, 1])
    ax_cm2.set_xticklabels(["Pred Neg", "Pred Pos"], fontsize=8)
    ax_cm2.set_yticklabels(["True Neg", "True Pos"], fontsize=8)
    for i in range(2):
        for j in range(2):
            val = cm_hy[i, j]
            ax_cm2.text(j, i, f"{val}\n({val/295:.1%})", ha="center", va="center",
                        color="white" if val > 90 else "black", fontsize=8.5, fontweight="semibold")

    # 5. Matched Operating Points (Precision at Target Validation FPR)
    ax_mop = fig.add_subplot(gs[1, 2])
    fpr_budgets = ["<= 1%", "<= 3%", "<= 5%", "<= 8%", "<= 10%"]
    prec_if = [84.62, 88.89, 96.08, 93.85, 92.86]
    prec_hy = [95.00, 95.65, 97.73, 98.44, 84.00]

    x = np.arange(len(fpr_budgets))
    w = 0.32
    ax_mop.bar(x - w/2, prec_if, w, label="Isolation Forest", color="#0284c7")
    ax_mop.bar(x + w/2, prec_hy, w, label="Hybrid Ensemble", color="#b91c1c")

    ax_mop.set_title("(f) Precision at Matched Val FPR Budgets", fontsize=10.5, fontweight="bold")
    ax_mop.set_xticks(x)
    ax_mop.set_xticklabels(fpr_budgets, fontsize=8)
    ax_mop.set_ylabel("Test Precision (%)", fontsize=9)
    ax_mop.set_ylim(75, 102)
    ax_mop.grid(axis="y", linestyle="--", alpha=0.5)
    ax_mop.legend(fontsize=7.5, loc="lower right")

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig7_detection_visualizations.svg", format="svg", bbox_inches="tight")
    fig.savefig(FIG_DIR / "fig7_detection_visualizations.png", format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Generated Figure 7.")

if __name__ == "__main__":
    generate_figure1()
    generate_figure2()
    generate_figure3()
    generate_figure4()
    generate_figure5()
    generate_figure6()
    generate_figure7()
    print("All figures successfully generated in SVG and PNG formats.")
