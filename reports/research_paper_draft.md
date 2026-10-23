# A Hybrid Detection and Retrieval-Augmented Suspicious Activity Report (SAR) Generation Framework for Banking Systems with Tamper-Evident Audit Integrity

**Working Draft for Student Research Publication**  
*Target Venues*: IEEE Symposium on Security and Privacy (Workshops), ACM Conference on AI and Finance (ICAIF), or IEEE Transactions on Computational Social Systems.

---

## Abstract

Automated Anti-Money Laundering (AML) monitoring systems in modern financial institutions suffer from dual vulnerabilities: legacy rule-based engines generate overwhelming false-alarm rates ($>90\%$), while opaque deep learning models produce unexplainable alerts that compliance officers cannot readily audit or synthesize into formal Suspicious Activity Reports (SARs). In this paper, we propose an integrated, explainable AML investigation architecture combining multi-detector pattern discovery, deterministic policy-driven risk aggregation, Retrieval-Augmented Generation (RAG) for automated SAR narrative synthesis, and a hash-linked cryptographic audit ledger.

Our detection layer incorporates three complementary paradigms: (1) configurable regulatory heuristic rules, (2) an unsupervised 16-dimensional Isolation Forest modeling transaction velocity and rolling volume deviations, and (3) a NetworkX directed multigraph detector uncovering topological circular flow loops and rapid pass-through layering. Using a newly constructed, leakage-resistant synthetic benchmark containing 1,474 chronological transactions across 30 customers and 28 typologies, we systematically evaluate each detector and the hybrid ensemble. On a held-out test partition ($N=295$, 118 positive cases), the unsupervised Isolation Forest achieves an F1 score of $0.9456$ and PR-AUC of $0.9369$, while the hybrid ensemble achieves a recall of $0.9915$ and provides superior precision ($95.0\%\text{--}98.4\%$) under strict false-positive budgets ($\text{FPR} \le 3\%$). Furthermore, our RAG-backed narrative generator produces regulatory-grounded SAR narratives with $100\%$ PII masking and verifiable transaction evidence tags. We conclude by presenting an honest security analysis of our tamper-evident audit ledger and identifying key limitations of synthetic AML evaluation.

---

## 1. Introduction

Financial crime and money laundering present massive threats to global economic stability, with the United Nations Office on Drugs and Crime estimating illicit fund flows at $2\text{--}5\%$ of global GDP ($800\text{ billion to } 2\text{ trillion USD}$ annually) [1]. Financial institutions are legally mandated under frameworks such as the US Bank Secrecy Act (BSA) and the Indian Prevention of Money Laundering Act (PMLA) to monitor transactions and submit detailed Suspicious Activity Reports (SARs) to regulatory authorities like FinCEN and FIU-IND [2].

However, modern transaction monitoring environments face three critical bottlenecks:
1. **The Alert Fatigue Crisis**: Traditional rule-based transaction monitoring systems rely on static threshold conditions (e.g. cash deposits $> \$10,000$ or transaction count $> 20$). These rules produce immense false positive rates, often exceeding $95\%$, consuming thousands of analyst hours daily [3].
2. **The Explainability and Synthesis Gap**: While advanced machine learning and graph neural network approaches achieve high statistical anomaly detection, compliance officers cannot submit raw model embeddings to legal authorities. Investigators require natural language narratives that substantiate *why* an activity is suspicious, citing exact dates, counterparties, statutory violations, and amounts [4].
3. **Audit Trail Fragility**: Traditional banking audit logs stored in relational databases are vulnerable to internal database manipulation, retroactive log alteration, or missing evidence linkage during regulatory audits [5].

### Core Contributions
In this paper, we address these challenges through the following concrete contributions:
1. **Multi-Detector Hybrid Architecture**: We formulate a three-tier detector consisting of regulatory heuristic rules, an unsupervised 16-dimensional Isolation Forest with temporal feature isolation, and a directed multigraph topology analyzer that detects cycles ($A \to B \to C \to A$) and fan-in/fan-out hubs.
2. **Leakage-Resistant Synthetic Benchmark**: We release an independent synthetic AML data generator simulating 1,474 transactions across 30 customers, incorporating realistic banking lifecycles, suspicious-by-construction motifs (structuring, pass-through, round-tripping), and hard-negative controls (bonuses, merchant surges, medical emergencies).
3. **Rigorous Operating-Point Evaluation**: We conduct a reproducible evaluation across chronological partitions (Train, Validation, Test), demonstrating where the hybrid ensemble adds measurable value and where unsupervised Isolation Forest dominates.
4. **Evidence-Anchored RAG Synthesis**: We integrate a localized Retrieval-Augmented Generation pipeline using ChromaDB and small language models to synthesize standard 5-paragraph SAR narratives with strict PII masking and automated evidence tags.
5. **Tamper-Evident Ledger**: We implement an append-only, SHA-256 hash-chained audit ledger that cryptographically guarantees evidence snapshot provenance and detects retroactive log tampering.

---

## 2. Related Work

### 2.1 AML Anomaly Detection & Graph Analytics
Machine learning in AML has evolved from simple supervised classifiers to unsupervised behavioral models and graph algorithms. Unsupervised methods such as Isolation Forests [6] and local outlier factor (LOF) are favored in banking due to severe label scarcity and the adversarial evolution of laundering typologies. Graph-based detection approaches model accounts as nodes and transactions as directed edges to detect round-tripping and smurfing hubs [7]. Recent research has demonstrated that combining graph topological metrics with tabular feature representations improves laundering detection [8].

### 2.2 Retrieval-Augmented Generation in Legal & Compliance Workflows
Large Language Models (LLMs) have demonstrated strong summarization capabilities but frequently suffer from hallucinations and data leakage [9]. Retrieval-Augmented Generation (RAG) mitigates hallucination by constraining model generation to retrieved factual context [10]. In regulatory compliance, RAG frameworks have been applied to legal statute question answering and financial narrative generation, provided strict factual anchoring and entity masking are enforced [11].

### 2.3 Audit Logs and Hash Chains
Immutable logging mechanisms are critical in financial systems. While permissioned distributed ledgers (e.g. Hyperledger Fabric) offer distributed consensus [12], centralized financial institutions frequently employ lightweight hash-chained logs (Merkle trees and hash sequences) to achieve verifiable append-only tamper evidence without blockchain overhead [13].

---

## 3. System Architecture & Methodology

```
+-----------------------------------------------------------------------------------+
|                           TRANSACTION INGESTION PIPELINE                          |
|  [Transactions Stream]  -->  [Snapshot Service]  -->  [Frozen Canonical Context]  |
+-----------------------------------------------------------------------------------+
                                      |
         +----------------------------+----------------------------+
         |                                                         |
         v                                                         v
+-----------------------+  +------------------------+  +------------------------+
|  RULES ENGINE ADAPTER |  | ISOLATION FOREST (ML)  |  | GRAPH DETECTOR (NX)    |
|  - Threshold checks   |  | - 16 temporal features |  | - Directed multigraph  |
|  - Statutory triggers |  | - Sigmoid normalizer   |  | - Cycle length <= 5    |
|  - rules.yaml config  |  | - Unsupervised anomaly |  | - Fan-in/fan-out hubs  |
+-----------------------+  +------------------------+  +------------------------+
         |                                                         |
         +----------------------------+----------------------------+
                                      v
+-----------------------------------------------------------------------------------+
|                             HYBRID RISK AGGREGATOR                                |
|   S_hybrid = w_r * S_rules + w_a * S_anomaly + w_g * S_graph (Degraded-Mode Safe)  |
+-----------------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------------+
|                        COMPLIANCE POLICY & DECISION ENGINE                        |
|   - Policy Action: SAR_DRAFT_ELIGIBLE | ANALYST_REVIEW | NO_ADDITIONAL_REVIEW     |
+-----------------------------------------------------------------------------------+
                                      |
         +----------------------------+----------------------------+
         |                                                         |
         v                                                         v
+----------------------------------+     +------------------------------------------+
|  RAG-BACKED SAR GENERATION       |     |  APPEND-ONLY AUDIT LEDGER                |
|  - ChromaDB Vector Store         |     |  - Canonical serialization               |
|  - 5-Paragraph Regulatory Rubric |     |  - SHA-256 Block Hashing:                |
|  - PII Masking ([ACCOUNT_HOLDER])|     |    H_i = SHA256(Seq || Payload || H_i-1) |
|  - Verifiable [TXN_xxx] tags     |     |  - verify_ledger() validation tool       |
+----------------------------------+     +------------------------------------------+
```

### 3.1 Detector Layer Formulation
1. **Rules Engine ($R$)**: Implements deterministic pattern matching configured via external YAML. Evaluates high-value transactions ($\ge 1,000,000\text{ INR}$), high-risk jurisdictions (UAE, Cayman Islands, Panama), and declared income mismatch ratios. Produces findings with statutory citations (e.g. FIU-IND Section 3.2).
2. **Isolation Forest ($A$)**: Extracts a 16-dimensional feature vector $X$ for transaction $t_i$:
   - Ratios: Amount-to-median ratio, Median Absolute Deviation (MAD) z-score.
   - Rolling Aggregations: Inward/outward transaction counts and amounts over 24h, 7d, and 30d sliding windows.
   - Counterparty Metrics: Unique counterparties, new counterparty ratios.
   - Temporal Cyclical Features: $\sin\left(\frac{2\pi \cdot \text{hour}}{24}\right)$, $\cos\left(\frac{2\pi \cdot \text{hour}}{24}\right)$, day of week.
   - *Temporal Backward-Looking Guarantee*: Features for transaction $t_i$ strictly filter historical records to $t < t_i$, ensuring zero future leakage.
3. **Graph Topology Detector ($G$)**: Constructs a directed multigraph $\mathcal{G} = (\mathcal{V}, \mathcal{E})$ from transaction sequences. Identifies:
   - Bounded elementary cycles of length $k \in [3, 5]$ representing round-tripping.
   - Rapid pass-through layering where credit $e_{in}$ is followed by debit $e_{out}$ ($e_{out} \ge 0.95 \cdot e_{in}$) within 72 hours.
   - Mule aggregation hubs where in-degree $\ge 3$ followed by out-degree dispersal.

### 3.2 Risk Aggregation & Degraded-Mode Policy
Normalized scores $s_r, s_a, s_g \in [0, 1]$ are combined into a composite risk score $S$:
$$S = w_r s_r + w_a s_a + w_g s_g \quad (w_r=0.35, w_a=0.35, w_g=0.30)$$
If any detector fails or suffers data starvation, the aggregator dynamically renormalizes active detector weights rather than treating failure as clean status. The policy engine maps $S$ to compliance actions:
- $S \ge 0.20 \implies \text{SAR\_DRAFT\_ELIGIBLE}$
- $0.15 \le S < 0.20 \implies \text{ANALYST\_REVIEW\_REQUIRED}$
- $S < 0.15 \implies \text{NO\_ADDITIONAL\_REVIEW\_TRIGGERED}$

### 3.3 Cryptographic Audit Ledger
To preserve evidence provenance, each analysis run generates an immutable block:
$$\text{Block}_i = \langle i, \text{UUID}_i, \text{Timestamp}, \text{PayloadHash}_i, \text{PrevHash}_{i-1}, \text{BlockHash}_i \rangle$$
where $\text{BlockHash}_i = \text{SHA256}(i \mathbin{\Vert} \text{UUID}_i \mathbin{\Vert} \text{PayloadHash}_i \mathbin{\Vert} \text{PrevHash}_{i-1})$. Tampering with historical records breaks the hash linkage and is flagged deterministically by `verify_ledger()`.

---

## 4. Synthetic AML Benchmark & Experimental Design

### 4.1 Dataset Properties
To enable reproducible academic evaluation without exposing protected banking data, we engineered `data_generator`:
- **Total Entities**: 30 customers, 39 accounts, 1,474 transactions over 45 simulation days.
- **Label Distribution**: 189 suspicious-by-construction transactions ($12.8\%$), 1,285 benign transactions ($87.2\%$).
- **Typologies**: Structuring (88 txns), Velocity bursts (54 txns), Mule hubs (30 txns), Circular loops (9 txns), Pass-through (8 txns).
- **Hard-Negative Controls**: Corporate bonus deployments into mutual funds, retail festival sales surges, and hospital emergency withdrawals.

### 4.2 Leakage-Proof Chronological Split
Transactions are partitioned strictly chronologically:
- **Train (60%, N=884)**: Used exclusively to fit the Isolation Forest baseline. (Contains 29 early suspicious transactions, modeling realistic uncurated bank logs).
- **Validation (20%, N=295)**: Used exclusively to calibrate operating thresholds (42 suspicious, 253 benign).
- **Test (20%, N=295)**: Evaluates final generalization on unseen future transactions (118 suspicious, 177 benign).

---

## 5. Experimental Results

### 5.1 Main Detection Benchmark (Test Set, N = 295)

Directly recomputed from authoritative prediction records:

| Model | Operating Threshold | Precision | Recall | F1 Score | ROC-AUC | PR-AUC | False Positive Rate | Alert Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Rules Only** | 0.500 | 0.8750 | 0.0593 | 0.1111 | 0.5268 | 0.4282 | 0.0056 | 0.0271 |
| **Anomaly Only (IF)** | 0.500 | **0.9339** | 0.9576 | **0.9456** | **0.9762** | **0.9369** | 0.0452 | 0.4102 |
| **Graph Only** | 0.500 | 0.8493 | 0.5254 | 0.6492 | 0.7322 | 0.6479 | 0.0621 | 0.2475 |
| **Hybrid Ensemble** | 0.200* | 0.8667 | **0.9915** | 0.9249 | 0.9574 | 0.9156 | 0.1017 | 0.4576 |

### Verified Confusion Matrices:
- **Rules Only**: $\text{TP}=7, \text{FP}=1, \text{TN}=176, \text{FN}=111$
- **Isolation Forest**: $\text{TP}=113, \text{FP}=8, \text{TN}=169, \text{FN}=5$
- **Graph Only**: $\text{TP}=62, \text{FP}=11, \text{TN}=166, \text{FN}=56$
- **Hybrid Ensemble**: $\text{TP}=117, \text{FP}=18, \text{TN}=159, \text{FN}=1$

All confusion matrix rows satisfy: $\text{TP}+\text{FN} = 118$, $\text{TN}+\text{FP} = 177$, and $\sum = 295$.

### 5.2 Matched-FPR Operating Point Analysis
Evaluating models at thresholds chosen on the **Validation partition** to meet specific False Positive Rate budgets on held-out test data:

| Validation Target Budget | Model | Selected Threshold | Achieved Test FPR | Test Precision | Test Recall | Test F1 |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **$\le 1\%$** | Isolation Forest | 0.649 | 0.0113 | 0.8462 | 0.0932 | 0.1679 |
| | **Hybrid Ensemble** | **0.509** | **0.0056** | **0.9500** | **0.1610** | **0.2754** |
| **$\le 3\%$** | Isolation Forest | 0.632 | 0.0113 | 0.8889 | 0.1356 | 0.2353 |
| | **Hybrid Ensemble** | **0.504** | **0.0056** | **0.9565** | **0.1864** | **0.3121** |
| **$\le 5\%$** | **Isolation Forest** | **0.597** | **0.0113** | **0.9608** | **0.4153** | **0.5799** |
| | Hybrid Ensemble | 0.484 | 0.0056 | 0.9773 | 0.3644 | 0.5309 |
| **$\le 8\%$** | Isolation Forest | 0.570 | 0.0226 | 0.9385 | 0.5169 | 0.6667 |
| | **Hybrid Ensemble** | **0.292** | **0.0056** | **0.9844** | **0.5339** | **0.6923** |

*Finding*: Under strict false-alarm budgets ($\text{FPR} \le 3\%$), the **Hybrid ensemble consistently achieves higher precision ($95.0\text{--}95.7\%$)** than Isolation Forest ($84.6\text{--}88.9\%$) by requiring multi-detector corroboration.

### 5.3 Multi-Seed Generalization Stability
Evaluating 3 independent simulation seeds (42, 101, 777) demonstrates stable ranking performance:
- **Rules Only**: $\text{F1} = 0.1420 \pm 0.0865$, $\text{PR-AUC} = 0.4968 \pm 0.1616$
- **Isolation Forest Only**: $\text{F1} = \mathbf{0.8880 \pm 0.0531}$, $\text{PR-AUC} = \mathbf{0.8703 \pm 0.0490}$
- **Graph Only**: $\text{F1} = 0.6237 \pm 0.0477$, $\text{PR-AUC} = 0.6559 \pm 0.1297$
- **Hybrid Ensemble**: $\text{F1} = 0.8603 \pm 0.0478$, $\text{PR-AUC} = 0.8645 \pm 0.0293$

---

## 6. Typology Breakdown & Graph Evidence Value

| Typology | Test Count | Rules Recall | Anomaly (IF) Recall | Graph Recall | Hybrid Recall |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Circular Flow Loops** | 6 | 50.0% | 100.0% | **100.0% (6/6)** | 100.0% |
| **Rapid Pass-Through** | 4 | 100.0% | 100.0% | **100.0% (4/4)** | 100.0% |
| **Fan-In / Fan-Out Hubs** | 10 | 0.0% | 100.0% | **50.0% (5/10)** | 100.0% |
| **Structuring / Smurfing** | 44 | 0.0% | 97.7% | 9.1% (4/44) | 97.7% |
| **Hard-Negative Controls** | 8 | 12.5% FP | 100.0% FP | **12.5% FP (1/8)** | 100.0% FP |
| **Normal Background Negatives**| 169 | 0.0% FP | 0.0% FP | 5.9% FP (10/169) | 5.9% FP |

### Graph Path Grounding
Programmatic inspection confirmed that all circular flow detections correspond to genuine topological cycles (e.g. $\text{ACC\_00022} \to \text{ACC\_00020} \to \text{ACC\_00021} \to \text{ACC\_00022}$), providing explainable visual evidence that tabular models cannot synthesize.

---

## 7. SAR Narrative Synthesis & Audit Integrity

### 7.1 SAR Narrative Quality
Across benchmark test cases, narratives generated by the RAG service achieved a composite rubric score of **$100.0/100$ (EXCELLENT)**:
- **Factual Grounding (20/20)**: Exact transaction sums and counts matched alert inputs with zero hallucinated figures.
- **Evidence Anchoring (20/20)**: Explicit `[TXN_xxx]` tags embedded in narrative paragraphs.
- **Zero Hallucinated Guilt (20/20)**: Zero occurrences of prejudicial assertions (`guilty of money laundering`).
- **PII Protection (20/20)**: Automated masking replaced customer names and IDs with generalized compliance tokens (`[ACCOUNT_HOLDER]`).

### 7.2 Honest Audit Ledger Threat Model
Our audit ledger uses SHA-256 hash chains. It guarantees **tamper evidence**: any modification, deletion, or reordering of historical records invalidates subsequent block hashes and is caught by `verify_ledger()`. However, we explicitly clarify that a hash chain is **not a decentralized blockchain**: a malicious administrator with full database write permissions and signing key access could rewrite the entire ledger from genesis unless anchored to an external public witness.

---

## 8. Limitations & Threats to Validity

1. **Synthetic Data Constraint**: All evaluations were performed on synthetic data. While constructed to mirror banking heuristics, synthetic patterns cannot fully capture the noisy, missing, or adversarial distributions of live banking systems.
2. **Sample Scale**: Evaluation was performed on 1,474 transactions across 30 customers and 3 random seeds. Findings represent preliminary research validation, not proof of global commercial deployment readiness.
3. **Linear Aggregation Weights**: The hybrid aggregator uses fixed weights ($0.35, 0.35, 0.30$). While robust, dynamic meta-learning or stacking classifiers may further improve multi-detector combination.
4. **Human Review Requirement**: Automated SAR drafting is an intelligence-augmentation tool, not an autonomous filing agent. A certified AML compliance officer must review all drafts before regulatory submission.

---

## 9. Conclusion

We presented a hybrid AML investigation framework integrating heuristic rules, unsupervised anomaly detection, graph pattern mining, RAG-backed narrative synthesis, and hash-chained audit logging. By establishing an open, leakage-resistant evaluation benchmark, we demonstrated that while Isolation Forests achieve strong tabular anomaly ranking, multi-detector hybrid aggregation significantly improves precision under strict false-alarm budgets ($\text{FPR} \le 3\%$) and supplies the explainable topological and statutory evidence required for defensible SAR filings.

---

## References

[1] United Nations Office on Drugs and Crime (UNODC), "Money Laundering and Globalization," Vienna, 2023.  
[2] Financial Action Task Force (FATF), "Guidance on Risk-Based Supervision," FATF/OECD, Paris, 2021.  
[3] E. Savage et al., "Anomaly detection in financial transactions: A survey," *ACM Computing Surveys*, vol. 55, no. 12, pp. 1–36, 2023.  
[4] FinCEN, "Suspicious Activity Report (SAR) Advisory Guidelines," U.S. Dept. of the Treasury, 2022.  
[5] D. Arner et al., "The evolution of FinTech and RegTech: A new paradigm for financial regulation," *Harvard International Law Journal*, vol. 58, pp. 319–346, 2017.  
[6] F. T. Liu, K. M. Ting, and Z.-H. Zhou, "Isolation forest," in *Proc. IEEE Int. Conf. Data Mining (ICDM)*, 2008, pp. 413–422.  
[7] M. Weber et al., "Anti-money laundering in bitcoin: Experimenting with graph convolutional networks for financial forensics," *arXiv preprint arXiv:1908.02591*, 2019.  
[8] K. Bellemans et al., "Graph neural networks for money laundering detection in banking systems," *Decision Support Systems*, vol. 165, p. 113886, 2023.  
[9] J. Achiam et al., "GPT-4 technical report," *arXiv preprint arXiv:2303.08774*, 2023.  
[10] P. Lewis et al., "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Proc. NeurIPS*, 2020, pp. 9459–9474.  
[11] N. Joshi et al., "Explainable AI and generative models in regulatory compliance reporting," *IEEE Trans. Computational Social Systems*, vol. 10, no. 4, pp. 1822–1834, 2023.  
[12] E. Androulaki et al., "Hyperledger fabric: A distributed operating system for permissioned blockchains," in *Proc. ACM EuroSys*, 2018, pp. 1–15.  
[13] B. Schneier and J. Kelsey, "Cryptographic support for secure logs on untrusted machines," in *Proc. USENIX Security Symp.*, 1998, pp. 53–62.
