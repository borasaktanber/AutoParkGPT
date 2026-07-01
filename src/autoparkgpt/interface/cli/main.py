"""Command-line interface for AutoParkGPT."""

from __future__ import annotations

from pathlib import Path

import typer

from autoparkgpt import __version__
from autoparkgpt.container import build_container
from autoparkgpt.infrastructure.config import RetrievalSettings
from autoparkgpt.infrastructure.observability import configure_tracing
from autoparkgpt.infrastructure.vectorstore import IngestionPipeline, load_documents

app = typer.Typer(help="AutoParkGPT — parking reservation chatbot.", no_args_is_help=True)


@app.command()
def version() -> None:
    """Print the application version."""

    typer.echo(__version__)


@app.command()
def ingest(
    directory: Path = typer.Argument(
        Path("data/static"),
        help="Directory of .md/.txt knowledge documents to index.",
    ),
) -> None:
    """Load, chunk, embed, and index static knowledge into the vector store."""

    if not directory.is_dir():
        typer.echo(f"Directory not found: {directory}", err=True)
        raise typer.Exit(code=1)

    container = build_container()
    settings = container.settings()
    documents = load_documents(directory)
    if not documents:
        typer.echo("No documents found to ingest.", err=True)
        raise typer.Exit(code=1)

    pipeline = IngestionPipeline(
        embedding=container.embedding(),
        vector_store=container.vector_store(),
        settings=RetrievalSettings(**settings.retrieval.model_dump()),
    )
    indexed = pipeline.ingest(documents)
    typer.echo(f"Ingested {len(documents)} documents into {indexed} chunks.")


@app.command()
def chat(session_id: str = typer.Option("cli", help="Conversation session id.")) -> None:
    """Start an interactive chat session in the terminal."""

    container = build_container()
    configure_tracing(container.settings().observability)
    service = container.chat_service()
    typer.echo("AutoParkGPT ready. Type 'exit' to quit.\n")
    while True:
        try:
            message = typer.prompt("you")
        except (EOFError, KeyboardInterrupt):  # pragma: no cover - interactive only
            break
        if message.strip().lower() in {"exit", "quit"}:
            break
        reply = service.respond(session_id, message)
        typer.echo(f"bot: {reply.message}\n")


if __name__ == "__main__":  # pragma: no cover
    app()
