"""Knowledge-Graph-Berechnung aus pgvector-Embeddings.

on-demand: UMAP 2D + HDBSCAN-Clustering + Cosine-Similarity-Edges.
Subsampling auf max. MAX_NODES damit D3 flüssig bleibt.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

MAX_NODES = 3000
MIN_CLUSTER_SIZE = 10
EDGE_THRESHOLD = 0.82
TOP_K_EDGES = 3


async def build_graph(
    event_type: str | None = None,
    agent_name: str | None = None,
    username: str | None = None,
    limit: int = MAX_NODES,
) -> dict:
    from hydrahive.db import mirror
    pool = mirror._pool
    if not pool:
        return {"active": False, "nodes": [], "edges": []}

    limit = min(limit, MAX_NODES)

    try:
        rows = await _load_rows(pool, event_type, agent_name, username, limit)
    except Exception as e:
        logger.warning("Graph: DB-Abfrage fehlgeschlagen: %s", e)
        return {"active": False, "nodes": [], "edges": []}

    if len(rows) < 10:
        return {"active": True, "nodes": [], "edges": [], "error": "Zu wenige eingebettete Events"}

    try:
        return await _compute(rows)
    except Exception as e:
        logger.warning("Graph: Berechnung fehlgeschlagen: %s", e)
        return {"active": True, "nodes": [], "edges": [], "error": str(e)}


async def _load_rows(pool, event_type, agent_name, username, limit) -> list[dict]:
    import asyncio
    conditions = ["embedding IS NOT NULL"]
    params: list[Any] = []

    if event_type:
        params.append(event_type)
        conditions.append(f"event_type = ${len(params)}")
    if agent_name:
        params.append(agent_name)
        conditions.append(f"agent_name = ${len(params)}")
    if username:
        params.append(username)
        conditions.append(f"username = ${len(params)}")

    params.append(limit)
    where = " AND ".join(conditions)

    async with pool.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT id, event_type, agent_name, username,
                   coalesce(nullif(text,''), nullif(tool_output,''), '') AS label,
                   embedding::text AS emb_str,
                   created_at
            FROM events
            WHERE {where}
            ORDER BY random()
            LIMIT ${len(params)}
        """, *params)

    result = []
    for r in rows:
        emb_str = r["emb_str"]
        if not emb_str:
            continue
        vec = [float(x) for x in emb_str.strip("[]").split(",")]
        result.append({
            "id": r["id"],
            "event_type": r["event_type"] or "",
            "agent_name": r["agent_name"] or "",
            "username": r["username"] or "",
            "label": (r["label"] or "")[:80],
            "vec": vec,
        })
    return result


async def _compute(rows: list[dict]) -> dict:
    import asyncio
    import numpy as np

    vecs = np.array([r["vec"] for r in rows], dtype=np.float32)

    # UMAP + HDBSCAN laufen synchron — in Thread auslagern
    coords, labels = await asyncio.get_running_loop().run_in_executor(
        None, _umap_hdbscan, vecs
    )

    # Nodes
    nodes = []
    for i, r in enumerate(rows):
        nodes.append({
            "id": r["id"],
            "x": float(coords[i, 0]),
            "y": float(coords[i, 1]),
            "cluster": int(labels[i]),
            "event_type": r["event_type"],
            "agent_name": r["agent_name"],
            "username": r["username"],
            "label": r["label"],
        })

    # Edges via Cosine-Similarity (normalisierte Vektoren → Dot-Product)
    edges = await asyncio.get_running_loop().run_in_executor(
        None, _cosine_edges, vecs, [r["id"] for r in rows]
    )

    return {"active": True, "nodes": nodes, "edges": edges}


def _umap_hdbscan(vecs):
    import numpy as np
    import umap
    import hdbscan

    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=15,
        min_dist=0.1,
        metric="cosine",
        random_state=42,
        low_memory=True,
    )
    coords = reducer.fit_transform(vecs)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=MIN_CLUSTER_SIZE,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    labels = clusterer.fit_predict(coords)

    return coords, labels


def _cosine_edges(vecs, ids: list[str]) -> list[dict]:
    import numpy as np

    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    normed = vecs / norms

    edges = []
    # Batch-weise um RAM zu schonen
    batch = 500
    n = len(ids)
    for i in range(0, n, batch):
        sims = normed[i:i+batch] @ normed.T
        for bi, row in enumerate(sims):
            gi = i + bi
            top = np.argsort(row)[::-1]
            count = 0
            for j in top:
                if j == gi:
                    continue
                if row[j] < EDGE_THRESHOLD:
                    break
                if count >= TOP_K_EDGES:
                    break
                if gi < j:
                    edges.append({
                        "source": ids[gi],
                        "target": ids[j],
                        "weight": float(row[j]),
                    })
                count += 1

    return edges
