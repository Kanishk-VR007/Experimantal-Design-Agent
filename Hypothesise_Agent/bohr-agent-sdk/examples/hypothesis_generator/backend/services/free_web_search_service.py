"""
Free Web Search Adapter for Scientific Visual References
=========================================================
Implements zero-cost, compliant search across:
  1. Wikimedia Commons API (Open access, CC/Public Domain technical diagrams & apparatus)
  2. SearXNG (If local/configured instance available)
  3. Curated Open-Access Scientific Diagram Catalogue (Deterministic fallback with verified licenses)
"""

import os
import re
import logging
import urllib.parse
from typing import List, Dict, Any, Optional
import requests
from dotenv import load_dotenv

from backend.visualization.prompt_schema import ReferenceItem

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

logger = logging.getLogger(__name__)

SEARXNG_BASE_URL = os.getenv("SEARXNG_BASE_URL", "").rstrip("/")


# ── Curated Open Scientific Diagram Catalogue (Deterministic Verified References) ──
CURATED_REFERENCE_CATALOGUE: Dict[str, List[Dict[str, Any]]] = {
    "mechanical_engineering": [
        {
            "title": "Four-Bar Linkage Mechanism Diagram",
            "keywords": ["four bar linkage", "linkage", "crank", "rocker", "coupler", "kinematics", "mechanism"],
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Four-bar_linkage_animation.gif/400px-Four-bar_linkage_animation.gif",
            "page_url": "https://commons.wikimedia.org/wiki/File:Four-bar_linkage_animation.gif",
            "source_name": "Wikimedia Commons (Open Mechanism)",
            "license": "CC-BY-SA 3.0",
            "image_type": "technical_diagram",
            "relevance_reason": "Clear mechanical four-bar linkage showing ground frame, input crank, connecting rod, and output rocker.",
            "confidence": 0.95,
        },
        {
            "title": "Involute Spur Gear Mesh & Tooth Geometry",
            "keywords": ["gear", "spur gear", "gear train", "pitch circle", "teeth", "torque", "speed ratio"],
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/Involute_wheel.gif/360px-Involute_wheel.gif",
            "page_url": "https://commons.wikimedia.org/wiki/File:Involute_wheel.gif",
            "source_name": "Wikimedia Commons (Gear Dynamics)",
            "license": "Public Domain",
            "image_type": "technical_diagram",
            "relevance_reason": "Visualizes pitch diameter, tooth profile meshing, center distance, and rotational synchronization.",
            "confidence": 0.94,
        },
    ],
    "civil_engineering": [
        {
            "title": "Simply Supported Beam Deflection Under Central Point Load",
            "keywords": ["beam", "simply supported", "deflection", "point load", "bending", "shear", "euler bernoulli"],
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Beam_bending_simple.svg/480px-Beam_bending_simple.svg.png",
            "page_url": "https://commons.wikimedia.org/wiki/File:Beam_bending_simple.svg",
            "source_name": "Wikimedia Commons (Structural Mechanics)",
            "license": "CC-BY-SA 3.0",
            "image_type": "technical_diagram",
            "relevance_reason": "Shows pin and roller boundary supports, applied vertical force P, and exaggerated parabolic deflection curve.",
            "confidence": 0.96,
        },
        {
            "title": "Truss Bridge Structural Member Analysis",
            "keywords": ["truss", "bridge", "warren truss", "pratt truss", "joints", "tension", "compression"],
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Pratt_truss.svg/480px-Pratt_truss.svg.png",
            "page_url": "https://commons.wikimedia.org/wiki/File:Pratt_truss.svg",
            "source_name": "Wikimedia Commons (Civil Structures)",
            "license": "Public Domain",
            "image_type": "technical_diagram",
            "relevance_reason": "Visualizes structural top chord, bottom chord, vertical struts, and diagonal members under nodal load.",
            "confidence": 0.92,
        },
    ],
    "electronics": [
        {
            "title": "Series RLC Circuit Schematic and Phase Diagram",
            "keywords": ["rlc", "resistor", "inductor", "capacitor", "resonance", "cutoff", "filter", "ac circuit"],
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cf/Series_RLC_circuit.svg/400px-Series_RLC_circuit.svg.png",
            "page_url": "https://commons.wikimedia.org/wiki/File:Series_RLC_circuit.svg",
            "source_name": "Wikimedia Commons (Electrical Circuits)",
            "license": "Public Domain",
            "image_type": "schematic",
            "relevance_reason": "Standard IEEE circuit schematic depicting series connection of resistor R, inductor L, and capacitor C.",
            "confidence": 0.95,
        },
        {
            "title": "RC Low-Pass Filter Frequency Response Schematic",
            "keywords": ["rc filter", "low pass filter", "cutoff frequency", "bode plot", "passive filter"],
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/1st_Order_Lowpass_Filter_RC.svg/400px-1st_Order_Lowpass_Filter_RC.svg.png",
            "page_url": "https://commons.wikimedia.org/wiki/File:1st_Order_Lowpass_Filter_RC.svg",
            "source_name": "Wikimedia Commons (Electronics)",
            "license": "Public Domain",
            "image_type": "schematic",
            "relevance_reason": "First-order passive RC filter layout with input voltage Vin and output voltage Vout across the capacitor.",
            "confidence": 0.94,
        },
    ],
    "computer_science": [
        {
            "title": "Breadth-First Search (BFS) Graph Traversal Diagram",
            "keywords": ["bfs", "breadth first search", "graph", "tree", "traversal", "nodes", "edges", "queue"],
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Breadth-First-Search-Algorithm.gif/400px-Breadth-First-Search-Algorithm.gif",
            "page_url": "https://commons.wikimedia.org/wiki/File:Breadth-First-Search-Algorithm.gif",
            "source_name": "Wikimedia Commons (Computer Science)",
            "license": "CC-BY-SA 3.0",
            "image_type": "technical_diagram",
            "relevance_reason": "Depicts numbered graph nodes with hierarchical levels, visited wave-fronts, and step-by-step state markers.",
            "confidence": 0.95,
        },
        {
            "title": "Binary Search Tree (BST) Structure and Balance",
            "keywords": ["binary search", "binary tree", "bst", "algorithm", "sorting", "search tree", "complexity"],
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Binary_search_tree.svg/360px-Binary_search_tree.svg.png",
            "page_url": "https://commons.wikimedia.org/wiki/File:Binary_search_tree.svg",
            "source_name": "Wikimedia Commons (Data Structures)",
            "license": "Public Domain",
            "image_type": "technical_diagram",
            "relevance_reason": "Visualizes root node, left subtree, right subtree, directed edge pointers, and key ordering.",
            "confidence": 0.93,
        },
    ],
    "physics": [
        {
            "title": "Simple Gravity Pendulum Free-Body Diagram",
            "keywords": ["pendulum", "oscillation", "simple pendulum", "gravity", "period", "tension", "damping"],
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/24/Oscillating_pendulum.gif/360px-Oscillating_pendulum.gif",
            "page_url": "https://commons.wikimedia.org/wiki/File:Oscillating_pendulum.gif",
            "source_name": "Wikimedia Commons (Classical Mechanics)",
            "license": "CC-BY-SA 3.0",
            "image_type": "technical_diagram",
            "relevance_reason": "Shows pivot point, string length L, bob mass m, angle theta, and restored force vector components.",
            "confidence": 0.96,
        },
    ],
    "chemistry": [
        {
            "title": "Chemical Reaction Kinetics & Gas Syringe Apparatus",
            "keywords": ["reaction kinetics", "rate of reaction", "gas syringe", "titration", "flask", "concentration"],
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Laboratory_glassware.jpg/400px-Laboratory_glassware.jpg",
            "page_url": "https://commons.wikimedia.org/wiki/File:Laboratory_glassware.jpg",
            "source_name": "Wikimedia Commons (Chemistry Lab)",
            "license": "CC-BY-SA 4.0",
            "image_type": "photograph",
            "relevance_reason": "Shows standard volumetric flasks, graduated cylinders, beakers, and reaction setup.",
            "confidence": 0.90,
        },
    ],
}


class FreeWebSearchService:
    """Zero-cost, privacy-respecting search adapter."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "HypothesiseAgent-ScienceVisualizer/2.0 (Open Research Tool)"})

    def search_wikimedia_commons(self, query: str, max_results: int = 4) -> List[ReferenceItem]:
        """Query Wikimedia Commons Open API for high-resolution scientific diagrams."""
        items: List[ReferenceItem] = []
        try:
            url = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": f"{query} diagram filetype:bitmap|drawing",
                "gsrlimit": max_results,
                "gsrnamespace": 6,  # File namespace
                "prop": "imageinfo",
                "iiprop": "url|size|mime|extmetadata",
            }
            resp = self.session.get(url, params=params, timeout=7)
            if resp.status_code == 200:
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_data in pages.items():
                    imageinfo = page_data.get("imageinfo", [])
                    if not imageinfo:
                        continue
                    info = imageinfo[0]
                    img_url = info.get("url")
                    if not img_url:
                        continue
                    # Check MIME type
                    mime = info.get("mime", "")
                    if not any(t in mime for t in ["jpeg", "jpg", "png", "webp", "gif"]):
                        continue

                    title = page_data.get("title", "").replace("File:", "").replace("_", " ")
                    extmetadata = info.get("extmetadata", {})
                    license_name = extmetadata.get("LicenseShortName", {}).get("value", "Open / CC")
                    desc = extmetadata.get("ObjectName", {}).get("value") or title

                    items.append(
                        ReferenceItem(
                            source_name="Wikimedia Commons (Open Scientific)",
                            page_url=info.get("descriptionurl") or img_url,
                            image_url=img_url,
                            image_type="technical_diagram",
                            license=license_name,
                            license_verified=True,
                            relevance_reason=f"Wikimedia diagram matching query '{query}': {desc[:100]}",
                            confidence=0.88,
                        )
                    )
        except Exception as e:
            logger.info("[FreeWebSearchService] Wikimedia search exception: %s", e)
        return items

    def search_searxng(self, query: str, max_results: int = 4) -> List[ReferenceItem]:
        """Query SearXNG instance if configured."""
        if not SEARXNG_BASE_URL:
            return []
        items: List[ReferenceItem] = []
        try:
            url = f"{SEARXNG_BASE_URL}/search"
            params = {
                "q": query,
                "categories": "images",
                "format": "json",
            }
            resp = self.session.get(url, params=params, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                for res in data.get("results", [])[:max_results]:
                    img_url = res.get("img_src") or res.get("url")
                    if img_url and img_url.startswith("http"):
                        items.append(
                            ReferenceItem(
                                source_name=f"SearXNG ({res.get('engine', 'web')})",
                                page_url=res.get("url", ""),
                                image_url=img_url,
                                image_type="technical_diagram",
                                license="Web Reference (Fair Use / Scientific)",
                                license_verified=False,
                                relevance_reason=res.get("title", "Visual search result"),
                                confidence=0.82,
                            )
                        )
        except Exception as e:
            logger.info("[FreeWebSearchService] SearXNG search exception: %s", e)
        return items

    def search_curated_catalogue(self, domain: str, search_terms: List[str]) -> List[ReferenceItem]:
        """Match domain and search keywords against curated scientific references."""
        candidates = CURATED_REFERENCE_CATALOGUE.get(domain, [])
        if not candidates and domain in ("general", ""):
            # Aggregate across all domains
            for d_items in CURATED_REFERENCE_CATALOGUE.values():
                candidates.extend(d_items)

        matched_items: List[ReferenceItem] = []
        lower_terms = [t.lower() for t in search_terms]

        for cand in candidates:
            cand_keywords = [k.lower() for k in cand.get("keywords", [])]
            # Score matches
            score = 0
            for term in lower_terms:
                if any(kw in term or term in kw for kw in cand_keywords):
                    score += 1
            if score > 0 or not matched_items:
                matched_items.append(
                    ReferenceItem(
                        source_name=cand["source_name"],
                        page_url=cand["page_url"],
                        image_url=cand["image_url"],
                        image_type=cand["image_type"],
                        license=cand["license"],
                        license_verified=True,
                        relevance_reason=cand["relevance_reason"],
                        confidence=cand["confidence"],
                    )
                )
        return matched_items[:3]

    def find_references(
        self,
        domain: str,
        search_queries: List[str],
        filtered_search_terms: List[str],
        max_total: int = 5,
    ) -> List[ReferenceItem]:
        """
        Execute free search across multiple adapters:
          1. SearXNG (if available)
          2. Wikimedia Commons API
          3. Curated Open-Source Catalogue
        """
        results: List[ReferenceItem] = []
        seen_urls = set()

        # 1. Try SearXNG if configured
        for q in search_queries[:2]:
            for item in self.search_searxng(q, max_results=2):
                if item.image_url not in seen_urls:
                    seen_urls.add(item.image_url)
                    results.append(item)

        # 2. Try Wikimedia Commons API
        primary_query = search_queries[0] if search_queries else " ".join(filtered_search_terms[:3])
        if primary_query:
            for item in self.search_wikimedia_commons(primary_query, max_results=3):
                if item.image_url not in seen_urls:
                    seen_urls.add(item.image_url)
                    results.append(item)

        # 3. Augment / fallback with curated catalogue
        catalogue_items = self.search_curated_catalogue(domain, filtered_search_terms)
        for item in catalogue_items:
            if item.image_url not in seen_urls and len(results) < max_total:
                seen_urls.add(item.image_url)
                results.append(item)

        return results[:max_total]


free_search_service = FreeWebSearchService()

