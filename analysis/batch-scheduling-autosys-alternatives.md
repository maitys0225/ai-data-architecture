
## Batch Orchestration Analysis - Alternatives to Autosys

### **Executive Summary & Shortlist**

The goal is to replace Autosys with a modern orchestration tool that bridges mainframe and distributed/cloud environments, is event-driven (especially via Kafka), and integrates deeply with the Azure ecosystem. The core challenge lies in the **mainframe integration requirement**. This single constraint significantly narrows the field, pushing commercial, enterprise-grade platforms to the forefront, as they have decades of experience and dedicated agents for these environments. Purely open-source, cloud-native tools, while excellent in their domains, lack out-of-the-box, supported mainframe connectivity.

#### **Shortlist**

*   **Best Overall Fit (Enterprise):**
    *   **BMC Control-M / Helix Control-M:** A primary market competitor to Autosys with deep Azure & Kubernetes plugins, Kafka/event-driven patterns, and a formal conversion tool for migration.
    *   **Stonebranch Universal Automation Center (UAC):** A close runner-up with strong hybrid automation, z/OS agents, a rich Integration Hub, and packaged AutoSys migration services.
*   **Solid Alternative (Enterprise):**
    *   **Tidal Automation (by Redwood):** An enterprise scheduler with pre-built Azure Data Factory + Databricks adapters and migration programs for AutoSys.
*   **Open-Source Options (for Cloud-Native Workloads):**
    *   **Apache Airflow, Dagster, Prefect:** Excellent for cloud-native workloads with strong engineering ergonomics, but would require significant custom development to orchestrate mainframe jobs, making them unsuitable as a single, centralized solution for the entire estate.

---

### **1. Deconstructing the Requirements & Market Implications**

Before diving into the tools, let's analyze the key requirements and what they imply.

*   **Mainframe + Non-Mainframe Orchestration:** This is the most critical differentiator. True mainframe integration requires dedicated, secure agents that can run on z/OS, submit JCL, track job status (e.g., JES), and handle file transfers. This is the traditional domain of enterprise workload automation (WLA) vendors.
*   **Cross-Subscription & Secrets Management:** This is a standard cloud security posture. Any modern tool must integrate with Azure Active Directory, Managed Identities, and Azure Key Vault to manage credentials on a per-subscription basis without hardcoding secrets.
*   **Native Kafka Support:** This signifies a shift from time-based scheduling to event-based orchestration. This requires a tool with persistent listeners or event-driven triggers.
*   **Centralized Hosting & Dependency Resolution:** The tool must act as a central "brain" for all batch processes, understanding complex cross-application and cross-platform dependencies.
*   **Native Azure Integration (ADF, Databricks, AKS):** The tool can't just run scripts. It needs deep integration to natively start, monitor, and manage jobs within these Azure services.
*   **Migration Support:** Migrating thousands of Autosys jobs (defined in JIL) is a massive undertaking. A vendor-provided, semi-automated conversion utility is a significant accelerator and de-risking factor.

---

### **2. Tool Candidate Analysis**

#### **Category 1: Enterprise Workload Automation Platforms**

These are commercial products designed as direct replacements for systems like Autosys.

##### **A) Control-M (from BMC)**

Control-M is often seen as the primary market competitor to Autosys. It has a strong heritage in mainframe and has aggressively modernized for cloud and DevOps paradigms.

*   **Orchestration Capabilities (MF/Non-MF):** **Excellent**. Provides dedicated z/OS agents for full mainframe job lifecycle management (JES2/3, JCL). Simultaneously manages jobs on Windows, Linux, and in the cloud.
*   **Cross-Subscription Functionality:** **Excellent**. Integrates with Azure AD and Key Vault. Connections can be configured using Service Principals or Managed Identities scoped to specific subscriptions, ensuring credential isolation.
*   **Event-Driven Orchestration:** **Excellent**. Control-M has a feature called "Application Integrator" and native event-driven capabilities. It can listen to Kafka topics, webhooks, file arrivals, etc., to trigger workflows.
*   **Integration (BigPanda, Azure):** **Excellent**.
    *   **BigPanda:** Provides out-of-the-box integration for sending events and alerts. Can be customized to fit ASR schedules. BigPanda supports webhooks/custom integrations, so this is feasible.
    *   **Azure:** Its breadth of plugins covers Databricks, ADF, Kubernetes/AKS, Azure Functions, and Azure Container Instances in a supported way, reducing custom code.
*   **Migration Support:** **Excellent**. BMC provides a dedicated, official **Conversion Tool** and professional services to migrate from Autosys to Control-M, automatically converting a high percentage of JIL definitions.
*   **UI and Visualization:** **Excellent**. Offers a rich web-based GUI (Viewpoints/Services dashboards) for workflow design, monitoring (single-pane-of-glass), and reporting.

##### **B) Stonebranch Universal Automation Center (UAC)**

Stonebranch is another leader in the enterprise automation space, focusing heavily on hybrid-cloud orchestration and a modern, "automation-as-code" approach.

*   **Orchestration Capabilities (MF/Non-MF):** **Excellent**. Similar to Control-M, Stonebranch has Universal Agents for z/OS that provide full, native mainframe integration alongside agents for distributed and cloud systems.
*   **Cross-Subscription Functionality:** **Excellent**. Securely manages credentials via its own vault or by integrating with third-party tools like Azure Key Vault. Supports standard Azure authentication methods for subscription isolation.
*   **Event-Driven Orchestration:** **Excellent**. Event-driven automation is a core pillar. It has native support for Kafka (**Kafka Event Monitor**), JMS, MQTT, file triggers, and webhooks, allowing for real-time orchestration.
*   **Integration (BigPanda, Azure):** **Excellent**.
    *   **BigPanda:** Integrates via webhooks or email-based event handling. Its flexible event engine can be configured to meet custom notification requirements for ASR.
    *   **Azure:** Provides a rich set of integrations available on the Stonebranch Integration Hub, including for ADF, Databricks, Azure Automation, and AKS.
*   **Migration Support:** **Excellent**. Stonebranch offers packaged **AutoSys replacement services**, automated conversion utilities, and a defined methodology to migrate from schedulers like Autosys.
*   **UI and Visualization:** **Very Good**. Provides a modern, web-based UI for designing, monitoring, and analyzing workflows. It supports "Jobs-as-Code" and offers OpenTelemetry feeds to tools like Dynatrace/Grafana.

##### **C) Tidal Automation (by Redwood)**

A solid enterprise alternative with a focus on Azure integrations.

*   **Orchestration Capabilities (MF/Non-MF):** Mainframe integration via z/OS gateways/agents to integrate MF jobs into enterprise flows.
*   **Azure Integration:** Enterprise scheduler with pre-built, native **Azure Data Factory** and **Databricks** adapters.
*   **Event-Driven Orchestration:** Kafka support is dependent on adapters/REST and may be less turnkey than competitors.
*   **Migration Support:** Offers **migration services** and specific "AutoSys alternative" programs.

---

#### **Category 2: Open-Source Orchestrators**

These tools are incredibly powerful for cloud-native workloads but have significant gaps regarding legacy systems and packaged enterprise features.

##### **D) Apache Airflow**

Airflow is the de-facto open-source standard for authoring, scheduling, and monitoring data pipelines. Workflows are defined as Python code (DAGs).

*   **Orchestration Capabilities (MF/Non-MF):** **Poor**. This is the critical weakness. Airflow has **no native, supported mainframe agent**. Achieving this would require a massive custom development effort.
*   **Cross-Subscription Functionality:** **Good**. Airflow's provider model allows for connections to different Azure subscriptions. It can leverage an **Azure Key Vault secrets backend** for authentication.
*   **Event-Driven Orchestration:** **Good**. Modern Airflow supports "Deferrable Operators" which can wait for external events. It has a first-class **Kafka provider** with sensors and operators. A common pattern is to have an external service trigger a DAG run via Airflow's robust REST API.
*   **Integration (BigPanda, Azure):** **Very Good**.
    *   **BigPanda:** Integration is done via custom Python code (e.g., using `on_failure_callback`) to call the BigPanda API.
    *   **Azure:** The official `apache-airflow-providers-microsoft-azure` package is excellent and provides operators for ADF, Databricks, Azure Batch, AKS, and more.
*   **Migration Support:** **Poor**. There is no standard tool to convert Autosys JIL to Airflow Python DAGs. This would be an entirely manual or custom-scripted process.
*   **UI and Visualization:** **Good**. The Airflow UI is functional for monitoring DAG runs. For advanced dashboards, it's common to export metrics via StatsD/OTel and visualize them in Grafana.

##### **E) Dagster & Prefect**

These are modern open-source alternatives to Airflow, also focused on cloud-native data workloads.

*   **Mainframe Support:** Same as Airflow - none built-in; would require external tools and custom development.
*   **Event-Driven (Kafka):** Both have strong support. Dagster has **Sensors** and a `dagster-kafka` package. Prefect is built around **event-driven automations**.
*   **Azure Integration:** Both have strong Azure support, including for Key Vault, AKS deployment patterns, and dedicated integration packages (`prefect-azure`).
*   **UI/Visualization:** Both offer modern UIs focused on asset lineage (Dagster) and observability (Prefect).
*   **Migration/Enterprise Features:** Like Airflow, they lack built-in Autosys migration tooling and enterprise features like sophisticated calendars and SLA management, which would need to be built.

---

### **3. Comparative Study Tables**

#### **Table 1: Qualitative Feature Comparison**

| Feature / Requirement | Control-M (BMC) | Stonebranch UAC | Apache Airflow |
| :--- | :--- | :--- | :--- |
| **Mainframe Orchestration** | **Excellent** (Native z/OS agents) | **Excellent** (Native z/OS agents) | **Poor** (Requires significant custom development) |
| **Cross-Subscription (Azure)** | **Excellent** (Native, secure credential mgmt) | **Excellent** (Native, secure credential mgmt) | **Good** (Achievable via providers & connections) |
| **Event-Driven (Kafka)** | **Excellent** (Native event listeners) | **Excellent** (Native event framework) | **Good** (Achievable via API triggers or sensors) |
| **Centralized Hosting** | **Excellent** (Core architecture) | **Excellent** (Core architecture) | **Excellent** (Core architecture) |
| **Dependency Resolution** | **Excellent** (Cross-platform, graphical) | **Excellent** (Cross-platform, visual & as-code) | **Good** (Within Airflow; cross-platform is complex) |
| **Azure Native Integration** | **Excellent** (Dedicated integrations) | **Excellent** (Rich set of integrations) | **Very Good** (Extensive official provider) |
| **BigPanda Integration** | **Excellent** (Out-of-the-box support) | **Very Good** (Flexible event-based integration) | **Fair** (Requires custom Python code) |
| **Migration from Autosys** | **Excellent** (Automated tools & services) | **Excellent** (Automated tools & services) | **Poor** (Manual effort, no standard tools) |
| **UI & Visualization** | **Excellent** (Rich GUI, single-pane-of-glass) | **Very Good** (Modern web UI, Jobs-as-Code) | **Good** (Functional UI, often paired with Grafana) |
| **Operating Model** | Commercial (License + Support) | Commercial (License + Support) | Open-Source (Self-supported or managed service) |
| **Best For** | Complex, mission-critical, hybrid environments needing high reliability and vendor support. | Modern, hybrid environments focused on event-driven automation and DevOps (as-code) practices. | Cloud-native, data-centric workloads where the team has strong Python skills and no mainframe requirement. |

#### **Table 2: Requirement-by-Requirement Feature Details**

| Requirement | Control-M | Stonebranch UAC | Tidal Automation | Airflow (OSS) | Dagster (OSS) | Prefect (OSS) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **MF + non-MF orchestration** | Native **z/OS** product line + distributed, single pane of glass. | **z/OS Universal Agent** to manage mainframe + distributed/cloud centrally. | z/OS gateways/agents to integrate MF jobs into enterprise flows. | No native mainframe; would need external schedulers/bridges. | | |
| **Cross-subscription (Azure) with separate secrets/credentials** | Dedicated plugins incl. **Azure Resource Manager**; per-connection credentials; enterprise secrets mgmt. | Microsoft integrations + Key Vault-friendly deployment patterns. | Native ADF/Databricks adapters with own connections. | **Azure Key Vault secrets backend**; per-connection service principals. | Key Vault in AKS and Azure deployment guidance. | `prefect-azure` blocks + credentials handling. |
| **Event-driven orchestration (Kafka)** | Event-driven orchestration patterns; Kafka via App Integrator/community packages. | **Kafka Event Monitor** & publish/consume extensions (no-code). | Kafka support depends on adapters/REST; less turnkey than Stonebranch. | First-class **Kafka provider** (sensors/operators). | **Sensors** & `dagster-kafka` package for event triggers. | Event-driven automations; Kafka via community patterns. |
| **Central hosting & inter-app dependencies** | Mature central EM + cross-folder dependencies, services, SLAs. | Central **Universal Controller** with cross-platform dependencies. | Central master with dependency mgmt; ADF/Azure adapters. | Central webserver/scheduler; cross-DAG deps possible but DIY governance. | Strong asset-graph dependency model in UI. | Central API/UI; dependencies supported in flows/deployments. |
| **Integrate with BigPanda & support ASR shift schedule** | Integration via webhooks/custom API; schedules handled in-tool. | Webhook/API to BigPanda; UAC calendars/schedules for shifts. | Same approach; native calendars. | Webhooks to BigPanda; Airflow calendars for shifts. | Webhooks to BigPanda; schedules via sensors/schedules. | Webhooks to BigPanda; schedules via deployments/automations. |
| **Migration support from AutoSys** | **Official Conversion Tool** (accelerators, reports). | **Packaged AutoSys replacement services & tooling**. | **Migration services** & "AutoSys alternative" programs. | None built-in; manual re-authoring or third-party services/tools. | | |
| **UI/visualization (single pane; Grafana)** | Rich **Web Monitoring (Viewpoints/Services)**; export metrics to enterprise monitors. | Real-time web UI; **OpenTelemetry** to Dynatrace/others. | Web console, dashboards; varies by version. | Airflow Web UI + **Grafana integrations** (StatsD/OTel). | Modern UI (asset graph, run views). | Prefect UI / Cloud observability. |
| **Native Azure integration (ADF, Databricks, AKS)** | **ADF**, **Azure Databricks**, **Azure Functions**, **Azure Container Instances**, **Kubernetes/AKS** plugins. | **ADF** + **Databracks** templates, Azure storage, etc. | **ADF** + **Databricks** adapters. | Azure providers, **Key Vault** backend; **cncf-kubernetes** for AKS. | Azure Key Vault + AKS deployment patterns. | `prefect-azure` (ACI, Blob, creds). |

---

### **4. Final Recommendation and Next Steps**

Given the stringent requirement for seamless mainframe and non-mainframe orchestration, the choice is clearly between the enterprise-grade platforms.

#### **Recommendation**

1.  **Primary Contenders: Control-M or Stonebranch UAC**
    *   You cannot meet your core requirements with an open-source tool like Airflow without undertaking a significant, high-risk, and costly custom development project to build mainframe integration.
    *   **Choose Control-M if:** Your organization prioritizes a long-standing, market-leading solution with the broadest feature set, deepest Azure integrations, and a proven, purpose-built tool for large-scale Autosys migrations.
    *   **Choose Stonebranch if:** Your organization is leaning towards a more modern, "as-code" DevOps approach, and you value a highly flexible, event-driven architecture with no-code Kafka monitors and a strong OpenTelemetry story.

2.  **Alternative: Tidal Automation**
    *   A good option if ADF/Databricks coverage is paramount. Validate mainframe specifics and Kafka triggers for your use cases.

#### **Quick Due-Diligence Checklist for a Proof of Concept (POC)**

1.  **Engage Vendors:** Request detailed demos and a PoC from BMC (Control-M), Stonebranch, and potentially Tidal.
2.  **Pilot a Migration:** Provide each vendor with a representative sample of complex Autosys jobs (including mainframe, distributed, and cross-platform dependencies). Ask them to demonstrate their migration utilities.
3.  **Validate Key Integrations:** In the PoC, validate the most critical integrations:
    *   **Hybrid Workflow:** Execute a JCL job on the mainframe and have its successful completion trigger a Databricks job in Azure.
    *   **Event-Driven:** Set up a Kafka topic and demonstrate a message triggering a multi-step workflow.
    *   **Azure Cross-Subscription:** Prove credential separation using Azure Key Vault per subscription.
    *   **Monitoring:** Configure a job failure to route an alert to BigPanda via webhooks. Confirm ASR shift calendars can be managed in the tool without being tightly coupled to BigPanda.
    *   **Observability:** Export scheduler metrics to Grafana (e.g., via OpenTelemetry or StatsD).
4.  **Total Cost of Ownership (TCO) Analysis:** Compare the licensing, support, and professional services costs of the commercial vendors against the estimated cost of a dedicated engineering team required to build and maintain a custom solution.

