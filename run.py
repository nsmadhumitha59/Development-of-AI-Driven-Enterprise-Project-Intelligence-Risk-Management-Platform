"""
Main Entrypoint and CLI Launcher for AI Project Intelligence & Risk Advisor (Milestone 1).
"""
import sys
import argparse
from pathlib import Path
import uvicorn

from configs.settings import settings
from src.ingestion.manager import IngestionManager
from src.rag.retriever import SemanticRetriever
from src.rag.embeddings import EmbeddingService
from src.rag.vectorstore import ChromaVectorStore


def cmd_serve(args):
    """Starts the FastAPI Web and API Server."""
    port = args.port or settings.PORT
    host = args.host or settings.HOST
    print(f"\n=======================================================")
    print(f"🚀 Starting {settings.APP_NAME} (Milestone 1)")
    print(f"📍 Web UI & Portal:  http://{host}:{port}/")
    print(f"📚 API Documentation: http://{host}:{port}/docs")
    print(f"⚡ Embedding Model:   {settings.EMBEDDING_MODEL_NAME}")
    print(f"💾 Vector Store:      ChromaDB ({settings.VECTOR_DB_DIR})")
    print(f"=======================================================\n")
    uvicorn.run("src.api.app:app", host=host, port=port, reload=args.reload)


def cmd_ingest(args):
    """Ingests and indexes one or more documents from CLI."""
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)

    print(f"📄 Ingesting document: {file_path.name}...")
    manager = IngestionManager()
    parsed_doc = manager.process_file(file_path)

    print(f"✅ Extracted {parsed_doc.metadata.char_count} characters across {len(parsed_doc.sections)} sections.")
    
    print("🧩 Chunking, embedding, and indexing into vector store...")
    retriever = SemanticRetriever()
    chunks = retriever.index_document(parsed_doc)
    manager.update_document_chunk_count(parsed_doc.metadata.document_id, len(chunks))

    print(f"🎉 Successfully indexed {len(chunks)} chunks for {file_path.name} (Doc ID: {parsed_doc.metadata.document_id})")


def cmd_query(args):
    """Performs semantic vector retrieval from CLI."""
    query_text = args.query
    print(f"\n🔍 Query: '{query_text}' (top_k={args.top_k})")
    
    retriever = SemanticRetriever()
    results = retriever.retrieve(query=query_text, top_k=args.top_k)

    if not results:
        print("ℹ️ No matching chunks found.")
        return

    print(f"\n--- Retrieved {len(results)} Chunks ---")
    for idx, r in enumerate(results, 1):
        score_pct = round(r.score * 100, 1)
        print(f"\n[{idx}] Document: {r.metadata.filename} | Score: {score_pct}% | Chunk #{r.metadata.chunk_index + 1}")
        if r.metadata.page_number:
            print(f"    Location: Page {r.metadata.page_number}")
        elif r.metadata.row_number:
            print(f"    Location: Row {r.metadata.row_number}")
        print(f"    Content: {r.content[:250]}..." if len(r.content) > 250 else f"    Content: {r.content}")


def cmd_agent(args):
    """Executes Milestone 2 intelligence agents from CLI."""
    from src.agents import (
        ScopeExtractionAgent,
        RiskForecastAgent,
        BlockerActionAgent,
        Milestone2MultiAgentPipeline
    )
    
    agent_type = args.agent_type
    focus_query = args.focus
    
    if agent_type == "scope":
        print("\n🔎 Running Scope & Deliverable Extraction Agent...")
        agent = ScopeExtractionAgent()
        result = agent.analyze(query_context=focus_query)
        print(f"\n📋 Project: {result.project_title}")
        goals = result.project_goals or result.goals
        if goals:
            print(f"🎯 Project Goals ({len(goals)}):")
            for g in goals:
                print(f"  • [{g.category.upper()}] {g.statement} (ID: {g.goal_id})")
        else:
            print(f"🎯 Project Goals: {result.empty_goals_message or 'No explicit project goals found in the uploaded documents.'}")

        print(f"\n📦 Deliverables ({len(result.deliverables)}):")
        for d in result.deliverables:
            print(f"  • {d.name} (Owner: {d.owner}, Status: {d.status})")

        print(f"\n🚩 Milestones ({len(result.milestones)}):")
        for m in result.milestones:
            print(f"  • {m.title} -> Target: {m.target_timeline or 'TBD'}")

        if result.timelines:
            print(f"\n⏱️ Timelines ({len(result.timelines)}):")
            for t in result.timelines:
                print(f"  • {t.milestone_or_task} -> Due: {t.target_deadline}")
            
    elif agent_type == "risk":
        print("\n⚠️ Running Risk Detection & Delivery Forecasting Agent...")
        agent = RiskForecastAgent()
        result = agent.analyze(query_context=focus_query)
        print(f"\n📊 Forecast Status: {result.forecast.overall_status.value} (Slippage Probability: {round(result.forecast.slippage_probability * 100, 1)}%)")
        print(f"🛡️ Detected Risks ({result.total_risks_detected}):")
        for r in result.detected_risks:
            print(f"  • [{r.level.value}] {r.title}")
            print(f"    Reason: {r.reason}")
            print(f"    Mitigation: {r.suggested_mitigation}")
            
    elif agent_type == "blockers":
        print("\n🚧 Running Blocker & Action Item Identification Agent...")
        agent = BlockerActionAgent()
        result = agent.analyze(query_context=focus_query)
        blockers = result.active_blockers or result.blockers
        if blockers:
            print(f"\n🛑 Active Blockers ({len(blockers)}):")
            for b in blockers:
                print(f"  • [{b.severity.value}] {b.description} (Category: {b.category})")
        else:
            print(f"\n🛑 Active Blockers: {result.empty_blockers_message or 'No active blockers identified from the uploaded documents.'}")

        print(f"\n✅ Action Items ({result.total_action_items}):")
        for a in result.action_items:
            print(f"  • {a.task_description} (Assignee: {a.assignee}, Due: {a.due_date or 'TBD'})")

        print(f"\n⚖️ Pending Decisions ({result.total_pending_decisions}):")
        for p in result.pending_decisions:
            print(f"  • {p.decision_needed} (Urgency: {p.urgency.upper()})")

    elif agent_type == "all":
        print("\n🤖 Running Full Milestone 2 Multi-Agent Pipeline...")
        pipeline = Milestone2MultiAgentPipeline()
        result = pipeline.run_all(focus_query=focus_query)
        print(f"\n=======================================================")
        print(f"🌟 MILESTONE 2 ANALYSIS REPORT: {result.project_title}")
        print(f"=======================================================")
        print(f"\n{result.overall_executive_summary}\n")
        print(f"Execution time: {result.total_execution_time_ms}ms")


def cmd_docs(args):
    """Executes Documentation Generation Agent from CLI (Milestone 3)."""
    from src.agents import DocumentationGenerationAgent
    doc_type = args.doc_type
    focus_query = args.focus
    agent = DocumentationGenerationAgent()

    if doc_type == "stories":
        print("\n📖 Generating Agile User Stories...")
        chunks = agent.retrieve_context(custom_query=focus_query)
        stories = agent.generate_user_stories(chunks)
        print(f"\n✅ Generated {len(stories)} User Stories:\n")
        for s in stories:
            print(f"[{s.story_id}] {s.title} ({s.priority} Priority)")
            print(f"  As a {s.as_a}, I want {s.i_want}, So that {s.so_that}")
            print(f"  Source: {s.source_document}\n")

    elif doc_type == "risks":
        print("\n🛡️ Generating Enterprise Risk Register...")
        chunks = agent.retrieve_context(custom_query=focus_query)
        risks = agent.generate_risk_register(chunks)
        print(f"\n✅ Generated {len(risks)} Risk Register Entries:\n")
        for r in risks:
            print(f"[{r.risk_id}] {r.risk_title} | Severity: {r.severity} | Category: {r.category}")
            print(f"  Mitigation: {r.mitigation_strategy}")
            print(f"  Source: {r.source_document}\n")

    elif doc_type == "actions":
        print("\n✅ Generating Action Items Checklist...")
        chunks = agent.retrieve_context(custom_query=focus_query)
        actions = agent.generate_action_items(chunks)
        print(f"\n✅ Generated {len(actions)} Action Items:\n")
        for a in actions:
            due = f" (Due: {a.target_date})" if a.target_date else ""
            print(f"[{a.item_id}] {a.task_description} — Assignee: {a.assignee}{due} | Status: {a.status}")

    elif doc_type == "all":
        print("\n📋 Generating Complete Project Documentation Package...")
        res = agent.analyze(query_context=focus_query)
        print(f"\n{res.executive_summary}\n")
        print(res.markdown_export)


def cmd_health(args):
    """Executes Project Health Scoring Module from CLI (Milestone 3)."""
    from src.agents import ProjectHealthScorer
    print("\n🚦 Calculating Project Health Score & Diagnostic Dimensions...")
    scorer = ProjectHealthScorer()
    res = scorer.analyze(query_context=args.focus)
    print(f"\n=======================================================")
    print(f"🎯 OVERALL HEALTH SCORE: {res.overall_health_score}/100 [{res.health_status.upper()}]")
    print(f"=======================================================")
    print(f"\n{res.executive_summary}\n")
    print("📊 Dimension Breakdown:")
    for d in res.dimensions:
        print(f"  • {d.dimension_name}: {d.score}/100 [{d.status}]")
        for f in d.key_factors:
            print(f"      - {f}")

    if res.recommendations:
        print("\n💡 Actionable Recommendations:")
        for r in res.recommendations:
            print(f"  • [{r.priority.upper()}] ({r.category}) {r.action} (Target: {r.target_owner})")


def cmd_chat(args):
    """Executes Conversational Project Intelligence Assistant from CLI (Milestone 3)."""
    from src.agents import ProjectIntelligenceChatAssistant
    assistant = ProjectIntelligenceChatAssistant()
    question = args.question
    print(f"\n💬 User Question: \"{question}\"")
    print("🤖 Synthesizing answer grounded in project documents...\n")
    res = assistant.answer_question(question=question)
    print("-------------------------------------------------------")
    print(res.answer)
    print("-------------------------------------------------------")
    if res.grounded_document_names:
        print(f"\n📄 Sources: {', '.join(res.grounded_document_names)} ({len(res.source_references)} chunk references)")
    if res.suggested_followups:
        print("\n💡 Suggested Follow-up Questions:")
        for f in res.suggested_followups:
            print(f"  • {f}")


def cmd_stats(args):
    """Displays current document and vector store statistics."""
    manager = IngestionManager()
    store = ChromaVectorStore()
    docs = manager.list_documents()
    stats = store.get_stats()

    print(f"\n📊 System Knowledge Base Stats:")
    print(f" - Total Ingested Documents: {len(docs)}")
    print(f" - Total Indexed Vectors:    {stats.get('total_chunks_indexed', 0)}")
    print(f" - Vector Database Path:     {stats.get('persist_directory')}")
    print(f" - Embedding Model:          {settings.EMBEDDING_MODEL_NAME}")
    
    if docs:
        print("\nDocument Registry:")
        for d in docs:
            print(f"  • {d.original_name} [{d.file_type.upper()}] - {d.chunk_count} chunks (ID: {d.document_id[:8]}...)")


def main():
    parser = argparse.ArgumentParser(description="AI Project Intelligence & Risk Advisor CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Run the FastAPI Web UI and REST API server")
    serve_parser.add_argument("--host", default=settings.HOST, help="Host address to bind")
    serve_parser.add_argument("--port", type=int, default=settings.PORT, help="Port number")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code changes")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a local document (PDF, DOCX, CSV, TXT)")
    ingest_parser.add_argument("file", help="Path to file")

    # Query command
    query_parser = subparsers.add_parser("query", help="Query the RAG semantic vector index")
    query_parser.add_argument("query", help="Search query text")
    query_parser.add_argument("--top-k", type=int, default=5, help="Number of top chunks to return")

    # Agent command (Milestone 2)
    agent_parser = subparsers.add_parser("agent", help="Run Milestone 2 intelligence agents")
    agent_parser.add_argument("agent_type", choices=["scope", "risk", "blockers", "all"], help="Which agent to run")
    agent_parser.add_argument("--focus", default=None, help="Optional focus query or topic")

    # Docs command (Milestone 3)
    docs_parser = subparsers.add_parser("docs", help="Run Milestone 3 Documentation Generation Agent")
    docs_parser.add_argument("doc_type", choices=["stories", "risks", "actions", "all"], help="Document type to generate")
    docs_parser.add_argument("--focus", default=None, help="Optional focus context")

    # Health command (Milestone 3)
    health_parser = subparsers.add_parser("health", help="Run Milestone 3 Project Health Scoring Module")
    health_parser.add_argument("--focus", default=None, help="Optional focus context")

    # Chat command (Milestone 3)
    chat_parser = subparsers.add_parser("chat", help="Ask a question to Conversational Project Intelligence Assistant")
    chat_parser.add_argument("question", help="Question text (e.g., 'Are we on track?', 'What are our biggest risks?')")

    # Stats command
    subparsers.add_parser("stats", help="Show system knowledge base stats")

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "agent":
        cmd_agent(args)
    elif args.command == "docs":
        cmd_docs(args)
    elif args.command == "health":
        cmd_health(args)
    elif args.command == "chat":
        cmd_chat(args)
    elif args.command == "stats":
        cmd_stats(args)
    else:
        # Default action: run server
        cmd_serve(args)


if __name__ == "__main__":
    main()
