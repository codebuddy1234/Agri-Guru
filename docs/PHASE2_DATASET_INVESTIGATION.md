# Phase 2 — Disease Detection: Dataset Investigation

**Status: investigation only. No model trained, no code written, no Phase 1 file touched.**

This document answers one question: *which dataset should AgriGuru's crop disease
detection module be built on, and what can we honestly claim about it?*

---

## 0. How to read this document (verification status)

Phase 1's dataset report was built by inspecting the CSV directly. **This one could
not be**, and that difference matters.

The sandbox this investigation ran in has Hugging Face, Zenodo, TensorFlow Datasets,
arXiv and Kaggle blocked by an egress proxy, so **no image was downloaded and no count
was independently reproduced here.** Every figure below is sourced from published
papers, official repositories, or dataset cards, and each is attributed.

Claims are tagged:

| Tag | Meaning |
|---|---|
| **[verified]** | Read directly from an official source during this investigation |
| **[published]** | From a peer-reviewed paper or official dataset card, not re-derived |
| **[derived]** | Computed in this document from verified inputs; arithmetic shown |
| **[estimate]** | Planning figure, explicitly not measured — treat as order-of-magnitude |

Before any training run, the counts in §3 must be re-checked against the actual
download. A dataset whose image count is quoted five different ways in the literature
(§6.1) is exactly the kind that needs checking rather than trusting.

---

## 1. Dataset sources

### 1.1 PlantVillage

| | |
|---|---|
| **Original paper** | Hughes & Salathé (2015), *An open access repository of images on plant health…*, arXiv:1511.08060 **[published]** |
| **Benchmark paper** | Mohanty, Hughes & Salathé (2016), *Using Deep Learning for Image-Based Plant Disease Detection*, Frontiers in Plant Science **[published]** |
| **Origin** | Penn State / EPFL Digital Epidemiology Lab **[verified]** |
| **Official repository** | `github.com/spMohanty/PlantVillage-Dataset` **[verified]** |
| **Variants** | `color/`, `grayscale/`, `segmented/` **[verified]** |
| **License** | CC BY 3.0 on the original release **[published]**; mirrors vary — see §5 |

**Important:** the widely-used "PlantVillage" on Kaggle is usually a *derived* copy —
often augmented, resized, pre-split, or with the 1,143-image `background_without_leaves`
class added (making 39 classes). These copies are **not** the original and their
licensing is frequently unstated. Use the official repository or the Hugging Face
`mohanty/PlantVillage` release, and record which one in the model card.

### 1.2 PlantDoc

| | |
|---|---|
| **Paper** | Singh, Jain, Jain, Kayal, Kumawat & Batra (2020), *PlantDoc: A Dataset for Visual Plant Disease Detection*, ACM CoDS-COMAD 2020, pp. 249–253 **[verified]** |
| **Origin** | IIT Gandhinagar, India **[published]** |
| **Repository** | `github.com/pratikkayal/PlantDoc-Dataset` **[verified]** |
| **License** | **CC BY 4.0** — confirmed from the repository's LICENSE.txt **[verified]** |
| **Build method** | Internet-scraped field images, ~300 human hours of annotation **[verified]** |

### 1.3 PlantWild

| | |
|---|---|
| **Paper** | *Benchmarking In-the-Wild Multimodal Plant Disease Recognition and A Versatile Baseline*, ACM Multimedia 2024 **[published]** |
| **Size** | 18,542 images, 89 classes (33 healthy, 56 diseased) **[published]** |
| **Nature** | In-the-wild, multimodal (images + descriptive text prompts) **[published]** |
| **Note** | A later "PlantWild v2" (115 disease-only classes, 11,488 images) also exists — a different release, not interchangeable **[published]** |

### 1.4 FieldPlant (found during investigation, not in the original brief)

Worth recording because it directly criticises PlantDoc:

| | |
|---|---|
| **Paper** | *FieldPlant: A Dataset of Field Plant Images…*, IEEE Access (2023) **[published]** |
| **Size** | 5,170 field images, 8,629 annotated individual leaves, 27 classes **[published]** |
| **Crops** | Corn, cassava, tomato (Cameroon plantations) **[published]** |
| **Key claim** | Annotation was **supervised by plant pathologists**, and the authors state PlantDoc "includes some laboratory images and the absence of plant pathologists during annotation may have resulted in misclassification" **[published]** |

This is a caution about PlantDoc's label quality, from a peer-reviewed source. It does
not disqualify PlantDoc, but it means PlantDoc results should be read as *indicative*,
not as ground truth.

---

## 2. Dataset comparison

| Criterion | PlantVillage | PlantDoc | PlantWild |
|---|---|---|---|
| **Image count** | 54,306 (see §6.1 — sources disagree) | 2,598 total / 2,569 / 2,482 depending on release | 18,542 |
| **Number of crops** | 14 | 13 | not stated per-crop; 89 disease classes |
| **Disease classes** | 26 | 17 | 56 |
| **Healthy classes** | 12 | 10 | 33 |
| **Total classes** | 38 (39 with background class in some copies) | 27 classification / ~29–30 detection | 89 |
| **Controlled vs field** | **Controlled** — single detached leaf, uniform grey/black background | **Field** — in-the-wild, internet-scraped, cluttered | **Field** — in-the-wild, multimodal |
| **Class balance** | **Poor** — `Potato___healthy` 152 images vs largest classes >5,000 (≈36:1) | Poor, and small absolute counts (~90 images/class average) | Moderate; 89 classes over 18.5k images ≈ 208/class average |
| **Image diversity** | **Very low** — one lab setup, 4–7 orientations of the *same* leaf | High — varied cameras, lighting, backgrounds, distances | High |
| **License** | CC BY 3.0 (original); mirrors vary | **CC BY 4.0** | Check release; academic use |
| **Train/test quality** | Good **if** the leaf-grouped 80/20 split is used; dangerous otherwise | Small test set (~230–240 images); some label noise reported | Defined benchmark splits |
| **Leakage risk** | **HIGH** — same leaf photographed 4–7 times | Low (distinct sources), but near-duplicates possible from scraping | Low |
| **Maharashtra relevance** | **Partial** — 66% of classes on relevant crops, but top 5 MH crops absent (§4) | Partial — same crop set, so same gaps | Broader, needs per-class audit |
| **Transfer-learning suitability** | **Good** — enough volume to fine-tune an ImageNet backbone | **Poor for training** (too small), good for evaluation | Good, but heavier |
| **Deployment suitability** | **Low on its own** — 31.4% on out-of-distribution images (§7.2) | N/A (evaluation set) | Best proxy for real conditions |

---

## 3. Exact class analysis

### 3.1 PlantVillage — all 38 classes **[verified]**

Read directly from `github.com/spMohanty/PlantVillage-Dataset/tree/master/raw/color`:

| Crop | Classes | Names |
|---|---|---|
| **Tomato** | 10 | Bacterial_spot, Early_blight, Late_blight, Leaf_Mold, Septoria_leaf_spot, Spider_mites Two-spotted_spider_mite, Target_Spot, Tomato_Yellow_Leaf_Curl_Virus, Tomato_mosaic_virus, healthy |
| **Apple** | 4 | Apple_scab, Black_rot, Cedar_apple_rust, healthy |
| **Corn (maize)** | 4 | Cercospora_leaf_spot Gray_leaf_spot, Common_rust_, Northern_Leaf_Blight, healthy |
| **Grape** | 4 | Black_rot, Esca_(Black_Measles), Leaf_blight_(Isariopsis_Leaf_Spot), healthy |
| **Potato** | 3 | Early_blight, Late_blight, healthy |
| **Cherry** | 2 | Powdery_mildew, healthy |
| **Peach** | 2 | Bacterial_spot, healthy |
| **Pepper, bell** | 2 | Bacterial_spot, healthy |
| **Strawberry** | 2 | Leaf_scorch, healthy |
| **Blueberry** | 1 | healthy |
| **Orange** | 1 | Haunglongbing_(Citrus_greening) |
| **Raspberry** | 1 | healthy |
| **Soybean** | 1 | healthy |
| **Squash** | 1 | Powdery_mildew |

Cross-check **[derived]**: 38 classes, 14 crops, 12 healthy, 26 disease — consistent
with the published "14 crops, 26 diseases" figure.

### 3.2 The asymmetry nobody mentions **[derived]**

Five of the 14 crops have **only one side of the healthy/diseased pair**:

| Crop | Has | Missing | Consequence |
|---|---|---|---|
| Soybean | healthy only | *all diseases* | Cannot detect any soybean disease |
| Blueberry | healthy only | all diseases | — (not a Maharashtra crop) |
| Raspberry | healthy only | all diseases | — (not a Maharashtra crop) |
| **Orange** | Huanglongbing only | **healthy** | Cannot say "your orange tree is healthy" |
| Squash | Powdery mildew only | healthy | — (minor crop) |

**This is the finding with the most product impact.** Soybean is Maharashtra's
second-biggest crop by national share, and PlantVillage contains *zero* soybean disease
images. Orange (Nagpur mandarin) has a disease class but no healthy baseline — a
classifier trained on it will label every orange leaf as diseased, because it has never
seen a healthy one.

Any model shipped on these two classes would be actively misleading. They must be
excluded from v1 or handled as a single-class detector with an explicit abstain path.

### 3.3 Class imbalance **[published]**

- Smallest class: `Potato___healthy` at **152 images**, while most classes exceed 1,000.
- Tomato alone: 18,160 images, from 5,357 (Yellow Leaf Curl Virus) down to 373 (Mosaic Virus) — **≈14:1 within one crop**.
- Overall imbalance ≈ **36:1** **[derived]** from the 152 minimum against >5,000 maxima.

Unlike Phase 1's crop dataset (exactly 100 rows per class, perfectly balanced), **plain
accuracy is not a safe headline metric here.** Macro-averaged metrics and a per-class
breakdown are mandatory — see §11.

### 3.4 PlantDoc classes **[verified/published]**

29 classes in the detection release, mapping onto 13 species: Apple (scab, rust, leaf),
Bell pepper (leaf spot, leaf), Blueberry leaf, Cherry leaf, Corn (gray leaf spot, rust,
blight), Grape (black rot, leaf), Peach leaf, Potato (early blight, late blight, leaf),
Raspberry leaf, Soyabean leaf, Squash powdery mildew, Strawberry leaf, Tomato (bacterial
spot, early blight, late blight, mold, septoria, spider mites, yellow virus, mosaic
virus, leaf).

**Every one of the 29 PlantDoc classes has a PlantVillage counterpart [derived]** — the
dataset was deliberately built to mirror PlantVillage. That is what makes it usable as
an external validation set.

Nine PlantVillage classes have **no** PlantDoc counterpart **[derived]**:
`Apple___Black_rot`, `Cherry___Powdery_mildew`, `Corn___healthy`, `Grape___Esca`,
`Grape___Leaf_blight`, `Orange___Haunglongbing`, `Peach___Bacterial_spot`,
`Strawberry___Leaf_scorch`, `Tomato___Target_Spot`.

---

## 4. Maharashtra relevance

This is where a generic "train on PlantVillage" plan falls apart, and it is the
strongest argument in this document.

### 4.1 Coverage of Maharashtra's actual crops **[derived]**

| Maharashtra crop | Why it matters | In PlantVillage? |
|---|---|---|
| **Cotton** | 2nd largest producer in India (~22%) | ❌ **absent** |
| **Sugarcane** | Leading producer | ❌ **absent** |
| **Onion** | Largest producer (~63%) | ❌ **absent** |
| **Pomegranate** | Largest producer | ❌ **absent** |
| **Banana** | Major producer (Jalgaon) | ❌ **absent** |
| **Tur / jowar / bajra** | Staple pulses and millets | ❌ **absent** |
| **Rice** | Konkan, Vidarbha | ❌ **absent** |
| **Soybean** | 2nd largest producer (~28%) | ⚠️ healthy class only — **no diseases** |
| **Orange** | Nagpur mandarin, flagship crop | ⚠️ one disease — **no healthy class** |
| **Grape** | Largest producer of seedless grapes (~78%), Nashik | ✅ 4 classes |
| **Tomato** | Widely grown | ✅ 10 classes |
| **Corn (maize)** | Widely grown | ✅ 4 classes |
| **Potato** | Grown, minor | ✅ 3 classes |
| **Bell pepper** | Grown, minor | ✅ 2 classes |

**Arithmetic [derived]:** 25 of 38 classes (66%) sit on crops grown in Maharashtra;
13 of 38 (34%) are on **apple, blueberry, cherry, peach, raspberry, squash and
strawberry** — crops with essentially no Maharashtra cultivation.

### 4.2 What this means

Training on all 38 classes spends a third of the model's capacity, and a third of the
confusion matrix, on crops no Maharashtra farmer will photograph. Worse, it creates
**failure modes that read as absurd to the user**: a farmer photographs a diseased
cotton leaf — a crop the model has never seen — and receives "Strawberry Leaf Scorch,
92% confident."

This is the disease-detection analogue of the Phase 1 problem where the model could
recommend apple to a farmer in Nashik. There, the fix was showing ranked alternatives.
Here the stakes are higher, because a closed-set classifier **cannot** say "this is not
a crop I know" unless we build that in deliberately.

---

## 5. Licensing

| Dataset | License | Commercial use | Attribution required |
|---|---|---|---|
| PlantVillage (original) | CC BY 3.0 **[published]** | Yes | Yes — cite Hughes & Salathé 2015 |
| PlantVillage (Kaggle mirrors) | **Varies / often unstated** | ⚠️ verify per copy | ⚠️ |
| PlantDoc | **CC BY 4.0** **[verified]** | Yes | Yes — cite Singh et al. 2020 |
| PlantWild | Check release terms **[unverified]** | ⚠️ verify before use | Yes |
| FieldPlant | Check release terms **[unverified]** | ⚠️ verify | Yes |

**Actions required before training:**
1. Download from the **official** source, not a Kaggle re-upload of unknown provenance.
2. Record the source URL and a SHA-256 of the archive in the model metadata — the same
   discipline Phase 1 already applies to `Crop_recommendation.csv`.
3. Put the attributions in the app's about page, not only in a README. CC BY requires
   attribution in the distributed product.

AgriGuru is a student project today but is intended to become a real platform. CC BY on
both primary datasets permits that, provided attribution travels with the product.

---

## 6. Data quality

### 6.1 The image count does not agree with itself **[verified]**

Across sources encountered in this investigation, PlantVillage's size is quoted as
**54,303 / 54,304 / 54,305 / 54,306 / 54,309**, and some copies add 1,143
`background_without_leaves` images for a 39th class.

This is not pedantry. If the paper you cite in your viva says 54,306 and your training
log says 54,309, an examiner is entitled to ask why. **Count it yourself, record the
number and the SHA-256, and cite your own count** alongside the published one.

### 6.2 Image characteristics

| Property | PlantVillage | PlantDoc |
|---|---|---|
| Typical resolution | 256×256 in the standard distribution **[published]** | Variable — internet-scraped **[published]** |
| Background | Uniform grey/black lab paper **[published]** | Cluttered, natural **[published]** |
| Leaves per image | Exactly one, detached, facing up **[published]** | Multiple, attached, any angle **[published]** |
| Lighting | Controlled **[published]** | Uncontrolled **[published]** |
| Label quality | High (lab-collected) | **Questioned** — no plant pathologist supervision (FieldPlant, IEEE Access 2023) **[published]** |

256×256 source images constrain input resolution: upscaling to 380×380 for
EfficientNet-B4 invents no new detail. See §9.6.

---

## 7. Leakage risks

### 7.1 The same leaf appears 4–7 times **[published]**

PlantVillage captured **4–7 orientations of each physical leaf** to document
morphological variability. A naive random 80/20 split therefore puts *the same leaf*
in both train and test, and the reported accuracy measures memorisation, not
generalisation.

**Mitigation:** use the leaf-grouped split published with the dataset, or group by
`leaf_id` in any custom split or cross-validation. This is the Phase 2 equivalent of the
Phase 1 finding that the crop CSV was sorted by class — a split-construction bug that
produces a model which "works" while being meaningless.

### 7.2 Capture bias — the most damaging finding **[published]**

Noyan (2022), *Uncovering bias in the PlantVillage dataset* (arXiv:2206.04374), trained a
model on **8 background pixels only** — four corners and four edge midpoints, containing
no leaf at all. It reached **49.0% accuracy on 38 classes**, against a 2.6% random
baseline.

Read that again. **Nearly half the benchmark is solvable without looking at the plant.**
The dataset contains capture artefacts — lighting, paper texture, session conditions —
that correlate with the label, and the paper reports that removing the background does
not remove the bias.

Consequences:
- A 99%+ PlantVillage accuracy is **not** evidence of disease-recognition skill. Up to
  ~49 points of it may be shortcut exploitation.
- The headline number belongs in the report only with this caveat attached.
- **Grad-CAM is not optional.** We must show the model attends to lesions, not corners.

### 7.3 Near-duplicates in PlantDoc

Internet-scraped images risk the same photograph appearing at different resolutions.
Run a perceptual-hash duplicate check before using PlantDoc as a held-out set.

---

## 8. Recommended dataset

**Train on a Maharashtra-relevant subset of PlantVillage. Validate externally on
PlantDoc. Do not train on PlantDoc.**

Reasoning:

1. **PlantVillage is the only candidate with enough volume to fine-tune a backbone.**
   PlantDoc's ~2,600 images across 27 classes (~90/class) is far too small to train
   from, and would overfit immediately.
2. **PlantDoc is the right external validation set** because it was built to mirror
   PlantVillage's label space — all 29 of its classes map onto PlantVillage classes
   **[derived]** — while differing in every capture condition. That is precisely the
   controlled→field shift we need to measure.
3. **The full 38 classes are the wrong training target** (§4): a third of capacity on
   irrelevant crops, plus two classes (soybean, orange) that are structurally incapable
   of supporting a healthy-vs-diseased decision.
4. **PlantWild is deferred to Phase 2.5**, not v1 — see §8.1.

### 8.1 On PlantWild

PlantWild (18,542 images, 89 classes, in-the-wild, ACM MM 2024) is **well suited to
robustness testing and future work**, and poorly suited to v1:

- ✅ Best available proxy for real farmer photographs.
- ✅ Multimodal text prompts open a route to zero-shot handling of unseen diseases —
  directly relevant to the cotton/sugarcane/onion gap.
- ❌ Its 89-class label space does not align with a 21-class PlantVillage subset, so it
  needs a manual class-mapping exercise before it can score anything.
- ❌ Licensing not yet verified.

**Recommendation:** use PlantWild as a *second* external test set once v1 exists, and as
the model for how AgriGuru's own farmer-image collection should be structured.

---

## 9. Recommended subset and classes

### 9.1 Proposed v1: 21 classes across 4 crops **[derived]**

| Crop | Classes | Maharashtra justification |
|---|---|---|
| **Tomato** | 10 (9 disease + healthy) | Widely grown; richest disease coverage in the dataset |
| **Grape** | 4 (3 disease + healthy) | Maharashtra produces ~78% of India's seedless grapes (Nashik) |
| **Corn (maize)** | 4 (3 disease + healthy) | Widely grown across the state |
| **Potato** | 3 (2 disease + healthy) | Grown; completes a healthy/diseased pair |

**Total: 21 classes, ~21,000 images [estimate]** — roughly 39% of PlantVillage.

Every crop in this subset has **both** healthy and diseased classes, so the model can
always make the decision a farmer actually cares about: *is this plant sick or not?*

### 9.2 Explicitly excluded, and why

| Excluded | Reason |
|---|---|
| Apple, Blueberry, Cherry, Peach, Raspberry, Strawberry, Squash | Not Maharashtra crops — 13 classes of wasted capacity |
| **Soybean** | Healthy class only; **no disease images exist** — cannot detect anything |
| **Orange** | Disease class only; **no healthy baseline** — would call every orange leaf diseased |
| Bell pepper | Minor crop; can be added in v1.1 at low cost (2 classes, both sides present) |

Soybean and orange are the painful exclusions, because both are strategically important
to Maharashtra. They are excluded *because* they matter: shipping a soybean detector
that has never seen a soybean disease, or an orange detector that cannot recognise a
healthy tree, would damage trust more than not shipping one.

### 9.3 The out-of-scope problem

A 21-class softmax **always returns one of 21 answers**. A farmer photographing cotton,
sugarcane, onion, pomegranate or banana — five of Maharashtra's largest crops — will get
a confident, wrong tomato or grape label.

This must be designed for before v1 ships. Options, in increasing order of effort:

1. **Confidence threshold + abstain** — below a calibrated threshold, return "I am not
   sure; this may not be a crop I recognise." Cheap, imperfect.
2. **Crop-first, disease-second** — a small crop classifier gates the disease model and
   says "cotton is not supported yet" explicitly. Honest and legible to the user.
3. **Open-set / OOD detection** (energy score, Mahalanobis) — most robust, most work.

**Recommendation: option 2 for v1.** It maps cleanly onto the existing "Coming Soon"
pattern already used on the dashboard: *the system knows what it does not do.*

### 9.4 Supported-crop list must be visible

The UI has to state the four supported crops **before** the farmer takes a photograph,
in Marathi/Hindi/English, exactly as the N/P/K unit warning is shown before input in
Phase 1.

---

## 10. Recommended model strategy

### 10.1 Architecture comparison **[published]**

ImageNet top-1 varies by source (original papers vs Keras retraining); ranges given.

| Model | Params | ImageNet top-1 | Size (fp32) | Size (int8) **[derived]** | Verdict |
|---|---|---|---|---|---|
| **MobileNetV3-Small** | ~2.5M | ~67% | ~10 MB | ~2.5 MB | Fastest; accuracy floor too low for 21 fine-grained classes |
| **MobileNetV3-Large** | ~5.4M | ~75.2% | ~22 MB | ~5.5 MB | Strong on-device option |
| **EfficientNet-B0** | ~5.3M | ~76.3–77.1% | ~29 MB | ~7.2 MB | **Best accuracy-per-parameter** |
| **ResNet50** | ~25.6M | ~74.9–76.0% | ~98 MB | ~24.5 MB | 5× the parameters for *no* accuracy gain |

**ResNet50 is the wrong default here.** It is the most-cited architecture in plant
disease papers, but EfficientNet-B0 matches or beats it with ~5× fewer parameters. Given
the Phase 1 precedent — GaussianNB was rejected despite the best macro-F1 because its
probabilities were unusable — "most popular" is not a reason. Choosing ResNet50 out of
habit is exactly what §8 of the original spec warns against.

### 10.2 Recommendation: EfficientNet-B0

- Best accuracy-per-parameter of the four **[published]**.
- 29 MB fp32 / ~7 MB int8 — deployable server-side now, on-device later.
- Well-supported pretrained weights in both PyTorch and TensorFlow.
- **Keep MobileNetV3-Large as the fallback**, and report both. A two-architecture
  comparison is stronger in a viva than one unexplained choice, and costs one extra
  training run (§12).

### 10.3 Transfer-learning strategy — two stages

**Stage 1 — feature extraction (~10 epochs)**
Freeze the backbone, train only a new head (global average pooling → dropout → dense →
21-way softmax). Establishes a baseline and prevents large early gradients from
destroying pretrained features.

**Stage 2 — fine-tuning (~20 epochs)**
Unfreeze the top ~30% of blocks, drop the learning rate by 10×, continue. Keep the
lower layers frozen: generic edge and texture filters transfer fine, and unfreezing
everything on 21k images invites overfitting.

Rationale to give in the viva: ImageNet features are generic in early layers and
domain-specific in later ones, so we re-learn only the domain-specific end.

### 10.4 Augmentation — and its limits

Justified (mimics real capture variation): random rotation ±30°, horizontal/vertical
flip, random resized crop (0.8–1.0), brightness/contrast jitter, slight blur.

Avoid: heavy colour-channel shifts — **colour is diagnostic** for chlorosis and necrosis,
and distorting hue destroys the signal we want.

**Be honest about what augmentation cannot fix.** Rotating a lab image does not produce
a field image. It does not add soil, other leaves, hands, shadows, or motion blur.
Augmentation narrows the controlled→field gap slightly; it does not close it. §7.2 says
why: the bias is in capture conditions, which no geometric transform removes.

---

## 11. Recommended evaluation strategy

### 11.1 Splits

- **Train / val / test = 70 / 15 / 15**, stratified by class, **grouped by leaf_id** (§7.1).
- Fixed seed, recorded in metadata — same discipline as Phase 1.
- Test set touched **once**, at the end.

### 11.2 Metrics — accuracy is not the headline

Given ≈36:1 imbalance (§3.3), report:

| Metric | Why |
|---|---|
| **Macro-F1** | Primary selection metric — weights a 152-image class equally |
| Macro precision / recall | Precision and recall trade off differently for a farmer (§11.3) |
| Per-class precision/recall/F1 | Where a mean hides a failure |
| **Confusion matrix** | Which diseases get confused — the agronomically interesting result |
| Balanced accuracy | Cross-check against macro-recall |
| Top-3 accuracy | Matches a UI that shows ranked candidates |
| **Calibration (ECE / reliability diagram)** | Required if we threshold on confidence (§9.3) |

Plain accuracy is reported **only** alongside macro-F1, never alone.

### 11.3 Which error is worse?

Worth stating explicitly in the viva. **False negative** (diseased called healthy) →
farmer does not treat, crop is lost. **False positive** (healthy called diseased) →
unnecessary pesticide, cost and environmental harm. For a smallholder both are serious,
so **macro-F1 rather than recall-only** is the defensible primary metric — with the
per-class breakdown showing where each type of error concentrates.

### 11.4 The two-number rule

Every result must be reported as a **pair**:

> PlantVillage held-out macro-F1: `0.XX` · PlantDoc external macro-F1: `0.YY`

Publishing the first without the second is the single most common failure in this
literature. §7.2 and §13 are why.

### 11.5 Explainability

Grad-CAM on a sample of correct and incorrect predictions, included in the report.
Given the 8-pixel result, we **must** show the model looks at lesions. If Grad-CAM
highlights corners and background, the model is exploiting capture bias and the result
is void regardless of its score.

---

## 12. Hardware and training considerations

### 12.1 Time estimates **[estimate — planning figures, not measured]**

30 epochs, 224×224, batch 32, on the ~21k-image subset (14,699 training images):

| Hardware | MobileNetV3-S | EfficientNet-B0 | ResNet50 |
|---|---|---|---|
| CPU only (4–8 cores) | ~4h 53m | ~10h 12m | ~30h 37m |
| Entry GPU (GTX 1650 4 GB) | ~22m | ~40m | ~1h 21m |
| Colab T4 (free tier) | ~12m | ~18m | ~33m |

For the full 54.3k-image dataset, multiply by ~2.6 (CPU-only ResNet50 ≈ 79 hours —
a good illustration of why the subset is the right call).

### 12.2 Verdict

**Yes, this is trainable on a normal development machine — with caveats.**

- **With any CUDA GPU:** comfortable. EfficientNet-B0 on the subset is under an hour.
- **CPU only:** EfficientNet-B0 at ~10 hours is an overnight run — viable but painful to
  iterate on. Prototype on a 3-class subset first.
- **Recommended:** develop locally, run final training on **Google Colab (free T4)**.
  ~18 minutes per run makes the two-architecture comparison (§10.2) trivially affordable.

### 12.3 Storage **[estimate]**

PlantVillage `color/` ~2 GB; all three variants ~5.5 GB; PlantDoc ~0.6 GB. Use `color/`
only — grayscale and segmented are derived and would triple the download for no benefit.

### 12.4 Do not commit images to git

Phase 1 committed `Crop_recommendation.csv` (150 KB). **2 GB of images must not go into
the repository.** Download via script, verify by checksum, keep out of version control —
the pattern `.gitignore` already establishes for `.joblib` artifacts.

---

## 13. Real-world limitations

### 13.1 The number that matters

Mohanty et al. (2016) reported **99.35%** on the held-out PlantVillage split. On images
taken under **different conditions**, the same approach scored **31.4%** **[published]**.

> **99.35% → 31.4%. A 68-point collapse, from the paper that created this benchmark.**

Combined with the 8-background-pixel result (§7.2), the conclusion is unavoidable:
**PlantVillage accuracy is close to meaningless as a predictor of field performance.**

This is the Phase 2 analogue of the Phase 1 caveat, but far more severe. In Phase 1 the
0.9955 accuracy was real for the data and merely unrepresentative of the field. Here,
up to half the benchmark score can be earned without looking at the plant.

### 13.2 Controlled vs farmer images

| | PlantVillage | A farmer's phone |
|---|---|---|
| Background | Uniform lab paper | Soil, other plants, hands, shoes |
| Leaves | One, detached, flat | Many, attached, overlapping |
| Lighting | Controlled | Harsh sun, shade, dusk |
| Focus | Sharp | Motion blur, dirty lens |
| Framing | Centred, filling frame | Too far, too close, tilted |
| Disease stage | Clear, developed | Early, ambiguous, or several at once |
| Crop | One of 14 | **Anything grown in Maharashtra** |

### 13.3 What we must not claim

- ❌ "99% accurate disease detection"
- ❌ "Detects 26 plant diseases" (we support far fewer, in 4 crops)
- ❌ Any benchmark number presented without its PlantDoc counterpart
- ✅ "Trained on a public research dataset of laboratory leaf images. Accuracy on real
  field photographs is substantially lower. Always confirm with an agricultural officer."

### 13.4 Product implications

1. **Show top-3 with probabilities**, as Phase 1's crop result page already does.
2. **Abstain below a calibrated threshold** rather than guessing.
3. **Say which crops are supported**, before the camera opens.
4. **Photo guidance** — one leaf, plain background, good light, in focus — which both
   helps the farmer and moves their image closer to the training distribution.
5. **Route to expert verification**, the mechanism the architecture already reserves.

---

## 14. Future data collection strategy

The intended path — *public dataset → initial model → deployment → farmer images →
expert verification → local dataset → retraining* — is exactly right, and it is the only
route that closes the gap in §13.1. Sketch of what Phase 2 must put in place:

**Stage 1 — capture (v1 launch).** Store every farmer-submitted image with its
prediction, confidence, crop, timestamp, district and model version. **Consent must be
explicit**, in the farmer's language, and separable: using the app must not require
donating images.

**Stage 2 — expert verification.** The `expert` role already exists in the Phase 1
schema. Experts confirm or correct the label; disagreements go to a third reviewer.
Target: a few hundred verified images per class.

**Stage 3 — local dataset.** A Maharashtra-specific, field-condition, expert-labelled
dataset. This is the genuinely novel contribution of the project, and a far stronger
viva result than another 99% PlantVillage number.

**Stage 4 — retraining.** Fine-tune on public + local. Evaluate on a **held-out local
test set**, which is the only honest measure of the deployed system. Version every
model; `crop_predictions.model_version` already establishes the pattern.

**Stage 5 — expand crops.** Cotton, sugarcane, onion, pomegranate and banana have no
public dataset worth using. Locally collected, expert-verified images are the *only*
route to covering Maharashtra's biggest crops — which is also the project's clearest
path to real-world value.

**Privacy:** GPS is sensitive. Store district-level location by default; require opt-in
for precise coordinates; never expose one farmer's images to another.

---

# Recommendation

### Recommended dataset
**PlantVillage** (official `spMohanty/PlantVillage-Dataset`, `color/` variant, CC BY 3.0)
for training — the only candidate with sufficient volume to fine-tune a backbone.

### Recommended initial classes
**21 classes across 4 crops** — Tomato (10), Grape (4), Corn/maize (4), Potato (3).
~21,000 images, ~39% of the dataset.

Excluded: apple, blueberry, cherry, peach, raspberry, strawberry, squash (not
Maharashtra crops); **soybean** (healthy images only — no disease exists in the dataset);
**orange** (disease only — no healthy baseline). Bell pepper is a cheap v1.1 addition.

### Recommended model
**EfficientNet-B0**, ImageNet-pretrained. ~5.3M parameters, ~76–77% ImageNet top-1,
29 MB — matches or beats ResNet50 with ~5× fewer parameters.
**MobileNetV3-Large reported alongside** as the deployment-oriented comparison.

### Recommended training strategy
Two-stage transfer learning at 224×224: freeze the backbone and train the head (~10
epochs), then unfreeze the top ~30% at a 10× lower learning rate (~20 epochs).
70/15/15 stratified split **grouped by leaf_id**. Moderate geometric and brightness
augmentation; no aggressive hue shifts. Class weighting or balanced sampling for the
36:1 imbalance. Select on **macro-F1**, never accuracy alone.

### Recommended external validation dataset
**PlantDoc** (CC BY 4.0) — all 29 of its classes map onto PlantVillage, and **17 of our
21 proposed classes (81%) are externally checkable** on it. Never train on it.
**PlantWild** is deferred to Phase 2.5 as a second, harder external test.

### Reason

Three findings drive every choice above.

**1. PlantVillage's benchmark score is not what it appears.** A model trained on **8
background pixels** — no leaf at all — reaches **49% on 38 classes** where random is
2.6% (Noyan 2022). And the dataset's own authors measured **99.35% → 31.4%** when
conditions changed (Mohanty 2016). We therefore treat PlantVillage as a *feature
initialiser*, not as evidence of field skill, and refuse to report any number without
its PlantDoc counterpart beside it.

**2. The full 38 classes are a poor fit for Maharashtra.** A third of them are apple,
cherry, blueberry, peach, raspberry, strawberry and squash — crops the target farmer
does not grow. Meanwhile **soybean has no disease class** and **orange has no healthy
class**, so the state's second-largest crop and its flagship fruit cannot be served
honestly by this data at all. Subsetting is not a shortcut; it is the only configuration
that does not mislead.

**3. The crops that matter most are simply absent.** Cotton, sugarcane, onion,
pomegranate and banana appear in no suitable public dataset. That makes the farmer-image
and expert-verification pipeline (§14) the central deliverable of Phase 2 rather than a
nice-to-have — and it is what will make this project's result genuinely its own, instead
of one more 99% PlantVillage number.

---

## Sources

- Hughes & Salathé (2015), *An open access repository of images on plant health…*, arXiv:1511.08060
- Mohanty, Hughes & Salathé (2016), *Using Deep Learning for Image-Based Plant Disease Detection*, Frontiers in Plant Science
- Noyan (2022), *Uncovering bias in the PlantVillage dataset*, arXiv:2206.04374
- Singh et al. (2020), *PlantDoc: A Dataset for Visual Plant Disease Detection*, ACM CoDS-COMAD 2020
- *Benchmarking In-the-Wild Multimodal Plant Disease Recognition and A Versatile Baseline*, ACM MM 2024 (PlantWild)
- *FieldPlant: A Dataset of Field Plant Images…*, IEEE Access (2023)
- `github.com/spMohanty/PlantVillage-Dataset` — official class listing
- `github.com/pratikkayal/PlantDoc-Dataset` — license and citation
