# Arnav Sahu
# 24BCE2976

"""Layer C — Mosaic Risk Engine.

In-memory cross-file correlation pass detecting multi-file exposure,
shared organizational/person identities, and geographic co-location.
"""

from dataclasses import dataclass
import math
import re
from typing import Any, Literal
import networkx as nx

from app.mosaic_models import Association, Convergence, MosaicFilePayload, MosaicResult
from app.priority import Priority, max_priority, priority_for_entity
from app.models import ScanResponse
from app.adversarial_router import AdversarialResponse
from app.scan import _analyzer

# Distance threshold in kilometers for geographic proximity correlation.
GEO_DISTANCE_THRESHOLD_KM = 2.0

# Priority weights for the explainable mosaic risk score formula:
# mosaic_score = sum(PRIORITY_WEIGHTS[c.priority] * len(c.source_files) for c in convergences)
# - HIGH (3.0): Financial data, direct identifiers, SSN, PAN, Aadhaar, or close physical co-location.
# - MEDIUM (2.0): Contact details, broader location entities, device/network artifacts.
# - LOW (1.0): Person and organization name mentions without sensitive identifiers.
PRIORITY_WEIGHTS: dict[Priority, float] = {
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
}

# Common corporate and organization legal suffixes stripped during normalization.
ORG_SUFFIX_REGEX = re.compile(
    r"\b(?:inc|incorporated|ltd|limited|llc|corp|corporation|co|company|pvt|private|gmbh|plc)\b\.?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CorrelationEntity:
    """Internal representation of an entity extracted for cross-file correlation."""

    entity_type: str
    raw_text: str
    normalized_key: str
    source_filename: str
    priority: Priority
    source_layer: Literal["baseline", "adversarial"]


def normalize_entity(text: str) -> str:
    """Normalize text by lowercasing, stripping punctuation/whitespace, and removing common org suffixes."""

    cleaned = text.strip().lower()
    cleaned = ORG_SUFFIX_REGEX.sub("", cleaned)
    # Remove all punctuation and collapse consecutive whitespace
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two geographic points in kilometers."""

    r = 6371.0  # Earth radius in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def _canonical_entity_type(entity_type: str) -> str:
    """Normalize equivalent entity type names across Presidio and spaCy."""

    mapping = {
        "ORGANIZATION": "ORG",
        "GPE": "LOCATION",
        "LOC": "LOCATION",
        "FAC": "LOCATION",
    }
    return mapping.get(entity_type, entity_type)


def extract_correlation_entities(scan: ScanResponse, filename: str) -> list[CorrelationEntity]:
    """Extract correlatable entities from Layer A baseline PII and financial findings."""

    supported_types = {
        "PERSON", "ORGANIZATION", "ORG", "LOCATION", "EMAIL_ADDRESS",
        "PHONE_NUMBER", "IP_ADDRESS", "US_SSN", "CREDIT_CARD",
        "FIN_BANK_ACCOUNT_NUMBER", "FIN_AADHAAR", "FIN_PAN_CARD",
        "FIN_IFSC_CODE", "FIN_UPI_ID",
    }
    entities: list[CorrelationEntity] = []
    for finding in scan.pii_findings + scan.financial_findings:
        canonical_type = _canonical_entity_type(finding.entity_type)
        if canonical_type in supported_types or finding.entity_type in supported_types:
            norm_key = normalize_entity(finding.text)
            if norm_key and len(norm_key) >= 2:
                entities.append(
                    CorrelationEntity(
                        entity_type=canonical_type,
                        raw_text=finding.text,
                        normalized_key=norm_key,
                        source_filename=filename,
                        priority=finding.priority,
                        source_layer="baseline",
                    )
                )
    return entities


def extract_vlm_entities(adversarial: AdversarialResponse, filename: str) -> list[CorrelationEntity]:
    """Run the pre-warmed spaCy pipeline over Layer B VLM observations to extract correlatable entities."""

    if not adversarial.vlm_analysis or not adversarial.vlm_analysis.observations:
        return []

    nlp = _analyzer().nlp_engine.nlp["en"]
    entities: list[CorrelationEntity] = []

    for obs in adversarial.vlm_analysis.observations:
        combined_text = f"{obs.description}. {obs.possible_inference}".strip()
        if not combined_text:
            continue
        doc = nlp(combined_text)
        for ent in doc.ents:
            canonical_type = _canonical_entity_type(ent.label_)
            if canonical_type in {"PERSON", "ORG", "LOCATION"}:
                norm_key = normalize_entity(ent.text)
                if norm_key and len(norm_key) >= 2:
                    entities.append(
                        CorrelationEntity(
                            entity_type=canonical_type,
                            raw_text=ent.text,
                            normalized_key=norm_key,
                            source_filename=filename,
                            priority=priority_for_entity(canonical_type),
                            source_layer="adversarial",
                        )
                    )
    return entities


def _format_explanation(
    entity_type: str,
    representative_text: str,
    baseline_files: set[str],
    adversarial_files: set[str],
    all_files: list[str],
) -> str:
    """Generate a clear, template-based plain-language explanation for an entity convergence."""

    if baseline_files and adversarial_files:
        b_str = ", ".join(sorted(baseline_files))
        a_str = ", ".join(sorted(adversarial_files))
        return (
            f"'{representative_text}' ({entity_type}) appears in {b_str} text/metadata "
            f"and is inferred from visual observations in {a_str}."
        )
    files_str = ", ".join(all_files)
    if adversarial_files and not baseline_files:
        return f"'{representative_text}' ({entity_type}) is inferred across visual evidence in {files_str}."
    return f"'{representative_text}' ({entity_type}) appears across {files_str}."


def find_convergences(entities: list[CorrelationEntity]) -> list[Convergence]:
    """Group entities by (entity_type, normalized_key) and retain those spanning 2+ distinct files."""

    grouped: dict[tuple[str, str], list[CorrelationEntity]] = {}
    for entity in entities:
        key = (entity.entity_type, entity.normalized_key)
        grouped.setdefault(key, []).append(entity)

    convergences: list[Convergence] = []
    for (entity_type, _norm_key), cluster in grouped.items():
        distinct_files = sorted(list({e.source_filename for e in cluster}))
        if len(distinct_files) < 2:
            continue

        # Choose the cleanest/longest raw text as the representative label
        representative_text = max((e.raw_text for e in cluster), key=len)
        cluster_priority = max_priority(*(e.priority for e in cluster))

        baseline_files = {e.source_filename for e in cluster if e.source_layer == "baseline"}
        adversarial_files = {e.source_filename for e in cluster if e.source_layer == "adversarial"}

        explanation = _format_explanation(
            entity_type=entity_type,
            representative_text=representative_text,
            baseline_files=baseline_files,
            adversarial_files=adversarial_files,
            all_files=distinct_files,
        )

        convergences.append(
            Convergence(
                entity_type=entity_type,
                representative_text=representative_text,
                source_files=distinct_files,
                priority=cluster_priority,
                explanation=explanation,
            )
        )

    return convergences


def find_geo_convergences(
    file_coords: list[tuple[str, float, float, str]],
    threshold_km: float = GEO_DISTANCE_THRESHOLD_KM,
) -> list[Convergence]:
    """Identify pairs or clusters of files located within the geographic distance threshold."""

    convergences: list[Convergence] = []
    visited_pairs: set[tuple[str, str]] = set()

    for i in range(len(file_coords)):
        for j in range(i + 1, len(file_coords)):
            file_a, lat1, lon1, src_a = file_coords[i]
            file_b, lat2, lon2, src_b = file_coords[j]
            if file_a == file_b:
                continue

            pair_key = (min(file_a, file_b), max(file_a, file_b))
            if pair_key in visited_pairs:
                continue

            dist = haversine_km(lat1, lon1, lat2, lon2)
            if dist <= threshold_km:
                visited_pairs.add(pair_key)
                explanation = (
                    f"Geographic coordinates in {file_a} ({src_a}) and {file_b} ({src_b}) "
                    f"are within {dist:.2f} km of each other."
                )
                convergences.append(
                    Convergence(
                        entity_type="LOCATION_PROXIMITY",
                        representative_text=f"Geo proximity ({dist:.2f} km)",
                        source_files=[pair_key[0], pair_key[1]],
                        priority="high",
                        explanation=explanation,
                    )
                )

    return convergences


def score_mosaic(convergences: list[Convergence]) -> float:
    """Calculate the explainable aggregate mosaic risk score based on priority weights and cluster size."""

    score = 0.0
    for convergence in convergences:
        weight = PRIORITY_WEIGHTS.get(convergence.priority, 1.0)
        score += weight * len(convergence.source_files)
    return round(score, 2)


def build_mosaic_graph(convergences: list[Convergence], filenames: list[str]) -> nx.Graph:
    """Build a NetworkX bipartite graph linking files to shared entity convergences."""

    graph = nx.Graph()
    for filename in filenames:
        graph.add_node(filename, node_type="file")

    for idx, conv in enumerate(convergences):
        conv_node_id = f"conv_{idx}_{conv.entity_type}_{conv.representative_text}"
        graph.add_node(
            conv_node_id,
            node_type="convergence",
            entity_type=conv.entity_type,
            representative_text=conv.representative_text,
            priority=conv.priority,
        )
        for source_file in conv.source_files:
            graph.add_edge(source_file, conv_node_id)

    return graph


def find_possible_associations(entities: list[CorrelationEntity]) -> list[Association]:
    """Identify cross-type PERSON -> ORG associations when exactly one distinct person exists in the batch.

    Ambiguity Guard:
    Only generate a PERSON -> ORG association when the entire batch contains exactly
    one distinct normalized PERSON entity total (across all files and layers).
    If the batch contains zero or more than one distinct person, do not generate any
    associations — avoid combinatorial guessing between multiple candidates or ungrounded inferences.
    """
    person_entities: dict[str, list[CorrelationEntity]] = {}
    for e in entities:
        if e.entity_type == "PERSON":
            person_entities.setdefault(e.normalized_key, []).append(e)

    # Scoping rule: exactly one distinct normalized PERSON entity in the entire batch
    if len(person_entities) != 1:
        # If the batch has zero or more than one distinct person, do not generate
        # any associations — say so in a comment in the code, don't silently guess between multiple candidates.
        return []

    person_cluster = next(iter(person_entities.values()))
    person_text = max((e.raw_text for e in person_cluster), key=len)
    person_files = {e.source_filename for e in person_cluster}

    # Group ORGs by (normalized_key, source_filename) for files other than the person's own files
    org_by_file: dict[tuple[str, str], list[CorrelationEntity]] = {}
    for e in entities:
        if e.entity_type == "ORG" and e.source_filename not in person_files:
            org_by_file.setdefault((e.normalized_key, e.source_filename), []).append(e)

    associations: list[Association] = []
    for (_org_key, org_filename), org_cluster in org_by_file.items():
        org_text = max((e.raw_text for e in org_cluster), key=len)
        explanation = (
            f"{person_text} is the only identified individual in this batch; "
            f"'{org_text}' appears separately in {org_filename}, suggesting a possible association "
            f"(e.g. employment) — not confirmed by direct evidence."
        )
        associations.append(
            Association(
                person_text=person_text,
                org_text=org_text,
                org_filename=org_filename,
                explanation=explanation,
                confidence_label="low",
            )
        )

    return associations


def build_mosaic_report(files: list[MosaicFilePayload]) -> MosaicResult:
    """Correlate entities and locations across all files to produce the MosaicResult."""

    all_entities: list[CorrelationEntity] = []
    file_coords: list[tuple[str, float, float, str]] = []

    for file_payload in files:
        fname = file_payload.filename
        # 1. Extract from Layer A baseline
        all_entities.extend(extract_correlation_entities(file_payload.scan, fname))

        # Check for GPS coordinates in Layer A metadata
        gps = file_payload.scan.metadata.gps
        if gps and gps.get("lat") is not None and gps.get("lon") is not None:
            file_coords.append((fname, float(gps["lat"]), float(gps["lon"]), "EXIF GPS"))

        # 2. Extract from Layer B adversarial if present
        if file_payload.adversarial:
            all_entities.extend(extract_vlm_entities(file_payload.adversarial, fname))
            geo = file_payload.adversarial.geolocation
            if geo and geo.get("lat") is not None and geo.get("lon") is not None:
                file_coords.append((fname, float(geo["lat"]), float(geo["lon"]), "GeoCLIP"))

    # 3. Find entity convergences
    entity_convergences = find_convergences(all_entities)

    # 4. Find geo convergences
    geo_convergences = find_geo_convergences(file_coords)

    all_convergences = entity_convergences + geo_convergences
    # Sort convergences: high priority first, then by number of connected files descending
    priority_order = {"high": 0, "medium": 1, "low": 2}
    all_convergences.sort(
        key=lambda c: (priority_order.get(c.priority, 3), -len(c.source_files))
    )

    score = score_mosaic(all_convergences)

    # 5. Populate NetworkX graph representation for structural validation
    filenames = [f.filename for f in files]
    build_mosaic_graph(all_convergences, filenames)

    # 6. Find cross-type PERSON -> ORG possible associations (hedged, not in mosaic_score)
    possible_associations = find_possible_associations(all_entities)

    return MosaicResult(
        convergences=all_convergences,
        possible_associations=possible_associations,
        mosaic_score=score,
        file_count=len(files),
        error=None,
    )

