### **ADR-002: Streamline Source Ingestion to a Single Landing Layer**

**Status:** Proposed

**Date:** 2025-09-21

**Context:**

The current DPAS platform architecture, implements a multi-layered data warehousing strategy using PostgreSQL, orchestrated by Airflow, with transformations handled by dbt.

The existing data flow for ingestion is as follows:
1.  **Source:** Mainframe EOD files, external vendor files
2.  **Ingestion (DHUB):** All soruce files will be handled via DHUB central pipeline
3.  **Load to Raw Layer:** 
This architecture creates a distinct separation between ingestion (managed by Airflow) and transformation (managed by dbt), with the `raw` layer acting as the handoff point. While robust, this introduces an additional layer that can increase complexity and latency, as data must be written and read an extra time before transformations begin.

**Decision:**

We will consolidate the ingestion process by eliminating the separate, persistent `raw` layer within the data paltform. The new, streamlined data flow will be:
1.  **Source:** External sources (unchanged).
2.  **Ingestion (Airflow):** An Airflow DAG extracts data from the source.
3.  **Load to Landing Layer:** The Airflow task loads the data directly into a table within a new `landing` schema in PostgreSQL (e.g., `landing.github_repos`). **These landing tables are considered ephemeral and are fully replaced on each run.**
4.  **Transformation:**
    *   The dbt `sources.yml` will be updated to point to the tables in the `landing` schema.
    *   The first layer of dbt models (`staging` models) will now read directly from the `landing` source tables. They will be responsible for all initial transformations (casting, renaming, basic cleaning) that were previously split between the conceptual raw and staging layers.
    *   The rest of the dbt model flow (`marts`) remains unchanged.

This decision effectively merges the "raw" and "staging" concepts into a single, dbt-centric workflow, where the `landing` zone is the direct input for the entire dbt transformation pipeline.

**Consequences:**

**Positive:**
*   **Reduced Complexity:** The architecture becomes simpler with one fewer data layer to manage, monitor, and document. The boundary is clear: Airflow lands the data, and dbt handles everything from that point forward.
*   **Lower Latency:** Eliminates the intermediate step of writing to a `raw` table and then having dbt read from it, making data available for transformation more quickly.
*   **Single Source of Transformation Logic:** All transformations, including initial type casting and column renaming, are consolidated within dbt, making the dbt project the single source of truth for all business logic.
*   **Reduced Storage:** We no longer store two initial versions of the data (raw and staged). This can lead to cost savings, especially with large datasets.

**Negative (Trade-offs):**


**Alternatives Considered:**

