#!/usr/bin/env python3
"""Generate RDF/XML linked data for the RTLDI Atlas."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from urllib.parse import quote
import xml.etree.ElementTree as ET

from src.generate_atlas_ebook import prepare_atlas_data
from src.lever_display import LEVER_DISPLAY, lever_long_description


OUT_PATH = Path("outputs/html-atlas/rtldi_atlas_2026.rdf")
BASE_URI = "https://rtldi.org/atlas/2026/"

NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "dcterms": "http://purl.org/dc/terms/",
    "dcat": "http://www.w3.org/ns/dcat#",
    "qb": "http://purl.org/linked-data/cube#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "schema": "https://schema.org/",
    "prov": "http://www.w3.org/ns/prov#",
    "void": "http://rdfs.org/ns/void#",
    "rtldi": "https://rtldi.org/ontology#",
}

for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


def qname(prefix: str, name: str) -> str:
    return f"{{{NS[prefix]}}}{name}"


def uri_path(value: Any) -> str:
    return quote(str(value).strip().replace(" ", "-"), safe="-_.~")


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def as_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def description(root: ET.Element, uri: str, rdf_type: str | None = None) -> ET.Element:
    node = ET.SubElement(root, qname("rdf", "Description"), {qname("rdf", "about"): uri})
    if rdf_type:
        ET.SubElement(node, qname("rdf", "type"), {qname("rdf", "resource"): rdf_type})
    return node


def literal(
    parent: ET.Element,
    prefix: str,
    name: str,
    value: Any,
    datatype: str | None = None,
    lang: str | None = None,
) -> None:
    attrs = {}
    if datatype:
        attrs[qname("rdf", "datatype")] = datatype
    if lang:
        attrs["{http://www.w3.org/XML/1998/namespace}lang"] = lang
    child = ET.SubElement(parent, qname(prefix, name), attrs)
    child.text = clean(value)


def resource(parent: ET.Element, prefix: str, name: str, uri: str) -> None:
    ET.SubElement(parent, qname(prefix, name), {qname("rdf", "resource"): uri})


def lever_property_uri(num: int) -> str:
    return NS["rtldi"] + f"lever{num}"


def write_rdf_atlas(data: Dict[str, Any], out_path: Path = OUT_PATH) -> Path:
    """Write RDF/XML for atlas-level metadata, countries, levers, and observations."""
    root = ET.Element(qname("rdf", "RDF"), {"{http://www.w3.org/XML/1998/namespace}base": BASE_URI})

    dataset_uri = f"{BASE_URI}dataset/rtldi-atlas-2026"
    dsd_uri = f"{BASE_URI}structure/rtldi-observation"
    lever_scheme_uri = f"{BASE_URI}scheme/rtldi-levers"
    distribution_uri = f"{BASE_URI}distribution/rdfxml"
    source_uri = "https://doi.org/10.5281/zenodo.19468550"

    dataset = description(root, dataset_uri, NS["qb"] + "DataSet")
    resource(dataset, "rdf", "type", NS["dcat"] + "Dataset")
    resource(dataset, "rdf", "type", NS["void"] + "Dataset")
    literal(dataset, "dcterms", "title", "RTLDI Atlas 2026: UN Member States computed RTLP scores", lang="en")
    literal(
        dataset,
        "dcterms",
        "description",
        "Linked open data export of the RTLDI Atlas for 193 UN member states, including computed RTLP score, nine binary RTLP lever values, GDP baseline, potential GDP, and annual capital exclusions in USD.",
        lang="en",
    )
    literal(dataset, "dcterms", "issued", "2026", NS["xsd"] + "gYear")
    literal(dataset, "dcterms", "language", "en")
    resource(dataset, "dcterms", "source", source_uri)
    resource(dataset, "qb", "structure", dsd_uri)
    resource(dataset, "dcat", "distribution", distribution_uri)
    resource(dataset, "dcterms", "subject", lever_scheme_uri)
    literal(dataset, "void", "uriSpace", BASE_URI)

    distribution = description(root, distribution_uri, NS["dcat"] + "Distribution")
    literal(distribution, "dcterms", "title", "RTLDI Atlas 2026 RDF/XML distribution", lang="en")
    literal(distribution, "dcat", "mediaType", "application/rdf+xml")
    resource(distribution, "dcat", "downloadURL", f"{BASE_URI}rtldi_atlas_2026.rdf")

    scheme = description(root, lever_scheme_uri, NS["skos"] + "ConceptScheme")
    literal(scheme, "skos", "prefLabel", "RTLDI nine-lever concept scheme", lang="en")
    literal(scheme, "dcterms", "description", "The nine binary right-to-life protection levers used to compute national RTLP scores.", lang="en")

    dsd = description(root, dsd_uri, NS["qb"] + "DataStructureDefinition")
    literal(dsd, "rdfs", "label", "RTLDI national observation structure", lang="en")

    # Define reusable RDF properties for the metrics and lever columns.
    property_labels = {
        "rtlpScore": ("RTLP score", "Computed right-to-life protection score on a 0-1 scale."),
        "gdpPerCapita": ("GDP per capita", "GDP per capita baseline in current USD."),
        "perCapitaPotential": ("Per capita potential", "GDP per capita plus capital exclusions per capita in current USD."),
        "annualGdp": ("Annual GDP", "GDP per capita multiplied by population in current USD."),
        "annualPotentialGdp": ("Annual potential GDP", "Annual GDP plus capped capital exclusions in current USD."),
        "capitalExclusionUsd": ("Capital exclusion USD", "Annual capped capital exclusions in current USD."),
        "capitalExclusionPerCapita": ("Capital exclusion per capita", "Annual capped capital exclusions per capita in current USD."),
        "population": ("Population", "Population used in the atlas computation."),
        "gdpBaselineYear": ("GDP baseline year", "Year of the GDP per capita baseline."),
        "vdemYear": ("V-Dem year", "Year of the V-Dem indicators used in the RTLP component crosswalk."),
    }
    for term, (label, comment) in property_labels.items():
        prop = description(root, NS["rtldi"] + term, NS["rdf"] + "Property")
        literal(prop, "rdfs", "label", label, lang="en")
        literal(prop, "rdfs", "comment", comment, lang="en")

    for num, meta in LEVER_DISPLAY.items():
        concept_uri = f"{BASE_URI}lever/{num}"
        prop_uri = lever_property_uri(num)

        concept = description(root, concept_uri, NS["skos"] + "Concept")
        resource(concept, "skos", "inScheme", lever_scheme_uri)
        literal(concept, "skos", "notation", str(num), NS["xsd"] + "integer")
        literal(concept, "skos", "prefLabel", meta["name"], lang="en")
        literal(concept, "skos", "definition", lever_long_description(num, meta.get("description", "")), lang="en")

        prop = description(root, prop_uri, NS["rdf"] + "Property")
        literal(prop, "rdfs", "label", f"Lever {num}: {meta['name']}", lang="en")
        literal(prop, "rdfs", "comment", "Binary RTLP lever value: 1 means present under the atlas threshold; 0 means absent.", lang="en")
        resource(prop, "dcterms", "subject", concept_uri)

    for region_name in sorted(data["regional_data"].keys()):
        region_uri = f"{BASE_URI}region/{uri_path(region_name)}"
        region = description(root, region_uri, NS["skos"] + "Concept")
        literal(region, "skos", "prefLabel", region_name, lang="en")

    for d in sorted(data["detailed_all"], key=lambda row: clean(row.get("country", row.get("iso3", "")))):
        iso3 = clean(d.get("iso3")).upper()
        country_uri = f"{BASE_URI}country/{iso3}"
        observation_uri = f"{BASE_URI}observation/{iso3}"
        region_name = clean(d.get("un_region"))
        region_uri = f"{BASE_URI}region/{uri_path(region_name)}"

        country = description(root, country_uri, NS["schema"] + "Country")
        literal(country, "schema", "name", d.get("country", iso3), lang="en")
        literal(country, "schema", "identifier", iso3)
        if region_name:
            resource(country, "schema", "containedInPlace", region_uri)
        resource(country, "schema", "subjectOf", observation_uri)

        gdp_per_capita = as_float(d.get("g0"))
        exclusion_per_capita = as_float(d.get("delta_g_per_capita"))
        population = as_float(d.get("population"))
        capital_exclusion = as_float(d.get("total_deficit_usd"))
        annual_gdp = gdp_per_capita * population
        annual_potential_gdp = annual_gdp + capital_exclusion
        per_capita_potential = gdp_per_capita + exclusion_per_capita

        obs = description(root, observation_uri, NS["qb"] + "Observation")
        resource(obs, "qb", "dataSet", dataset_uri)
        resource(obs, "dcterms", "spatial", country_uri)
        literal(obs, "dcterms", "identifier", iso3)
        literal(obs, "rtldi", "rtlpScore", f"{as_float(d.get('r')):.9f}", NS["xsd"] + "decimal")
        literal(obs, "rtldi", "gdpPerCapita", f"{gdp_per_capita:.6f}", NS["xsd"] + "decimal")
        literal(obs, "rtldi", "capitalExclusionPerCapita", f"{exclusion_per_capita:.6f}", NS["xsd"] + "decimal")
        literal(obs, "rtldi", "perCapitaPotential", f"{per_capita_potential:.6f}", NS["xsd"] + "decimal")
        literal(obs, "rtldi", "annualGdp", f"{annual_gdp:.6f}", NS["xsd"] + "decimal")
        literal(obs, "rtldi", "annualPotentialGdp", f"{annual_potential_gdp:.6f}", NS["xsd"] + "decimal")
        literal(obs, "rtldi", "capitalExclusionUsd", f"{capital_exclusion:.6f}", NS["xsd"] + "decimal")
        literal(obs, "rtldi", "population", f"{population:.0f}", NS["xsd"] + "decimal")
        literal(obs, "rtldi", "gdpBaselineYear", clean(d.get("g0_year")), NS["xsd"] + "gYear")
        literal(obs, "rtldi", "vdemYear", clean(d.get("vdem_year")), NS["xsd"] + "gYear")

        components = d.get("components", [])
        for i in range(9):
            value = 0
            if len(components) > i:
                value = int(components[i].get("bin", 0) or 0)
            literal(obs, "rtldi", f"lever{i + 1}", str(value), NS["xsd"] + "integer")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(out_path, encoding="utf-8", xml_declaration=True)
    return out_path


def main() -> None:
    print("Preparing data for RDF/XML linked data export...")
    data = prepare_atlas_data()
    out_path = write_rdf_atlas(data)
    print(f"RDF/XML linked data written to: {out_path}")


if __name__ == "__main__":
    main()
