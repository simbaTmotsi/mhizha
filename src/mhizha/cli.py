"""Dev harness CLI. RUNTIME commands are offline; ingest and index are build time.

The Android app does not ship typer or rich. This module is the developer's interface to
the same code paths the app uses, so a behaviour proven here is the behaviour shipped.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import Config, load_config
from .errors import MhizhaError

app = typer.Typer(add_completion=False, help="Mhizha: offline on-device agronomy co-pilot")
models_app = typer.Typer(help="Candidate model shortlist and device budget")
i18n_app = typer.Typer(help="Locale checks")
review_app = typer.Typer(help="Human validation ledger")
app.add_typer(models_app, name="models")
app.add_typer(i18n_app, name="i18n")
app.add_typer(review_app, name="review")

console = Console()

BAND_STYLE = {"high": "green", "medium": "yellow", "low": "red"}


def _cfg() -> Config:
    try:
        return load_config()
    except MhizhaError as exc:
        console.print(f"[red]config error:[/red] {exc}")
        raise typer.Exit(code=2)


# ------------------------------------------------------------------ ingest


@app.command()
def ingest(
    path: Path = typer.Option(None, "--path", help="Single file instead of the whole raw dir"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Report only, write nothing"),
) -> None:
    """BUILD TIME. Ingest data/raw/ into data/corpus/ with provenance."""
    from .corpus.ingest import ingest_directory, ingest_file

    cfg = _cfg()
    cfg.corpus.dir.mkdir(parents=True, exist_ok=True)

    if path is not None:
        try:
            documents = [ingest_file(path)]
            quarantined: list[tuple[Path, str]] = []
            warnings: list[tuple[Path, str]] = []
        except MhizhaError as exc:
            console.print(f"[red]quarantined[/red] {path}: {exc}")
            raise typer.Exit(code=1)
    else:
        result = ingest_directory(cfg.corpus.raw_dir)
        documents, quarantined, warnings = (
            result.documents, result.quarantined, result.warnings
        )

    for src, warning in warnings:
        console.print(f"[yellow]warning[/yellow] {src.name}: {warning}")
    for src, reason in quarantined:
        console.print(f"[red]quarantined[/red] {src.name}: {reason}")

    if not dry_run:
        for doc in documents:
            out = cfg.corpus.dir / f"{doc.doc_id}.md"
            front = "\n".join(
                f"{k}: {getattr(doc, k)}"
                for k in ("source", "publisher", "refresh_date", "lang", "crop",
                          "region", "season", "topic", "placeholder")
            )
            out.write_text(
                f"---\n{front}\nsource_path: {doc.source_path}\n"
                f"sha256: {doc.sha256}\ningested_at: {doc.ingested_at}\n---\n\n{doc.text}\n",
                encoding="utf-8",
            )

    verb = "would ingest" if dry_run else "ingested"
    console.print(
        f"[green]{verb}[/green] {len(documents)} document(s), "
        f"{len(quarantined)} quarantined"
    )
    if not documents and not quarantined:
        console.print(
            f"[dim]nothing in {cfg.corpus.raw_dir}. Drop PDFs or DOCX there, with a "
            f"sidecar <name>.meta.yaml supplying source, publisher, refresh_date, lang.[/dim]"
        )


# ------------------------------------------------------------------ chunk


@app.command()
def chunk(
    inspect: int = typer.Option(0, "--inspect", help="Print N chunks with metadata"),
) -> None:
    """BUILD TIME. Chunk data/corpus/ documents and apply the review ledger."""
    from .corpus.ingest import ingest_file
    from .corpus.chunk import chunk_document
    from .corpus.review import ReviewLedger
    from .corpus.schema import chunks_to_json

    cfg = _cfg()
    ledger = ReviewLedger(cfg.corpus.review_ledger)
    total = 0
    counts_all = {"approved": 0, "rejected": 0, "stale": 0, "unreviewed": 0}
    shown = 0

    sources = [p for p in sorted(cfg.corpus.dir.glob("*.md"))]
    if not sources:
        console.print(f"[red]no documents in {cfg.corpus.dir}[/red]")
        raise typer.Exit(code=1)

    for path in sources:
        doc = ingest_file(path)
        chunks = chunk_document(doc, cfg.corpus.chunk)
        chunks, counts = ledger.apply(chunks)
        for key, value in counts.items():
            counts_all[key] += value
        out = cfg.corpus.dir / f"{doc.doc_id}.chunks.json"
        out.write_text(chunks_to_json(chunks), encoding="utf-8")
        total += len(chunks)

        while inspect and shown < inspect and shown < len(chunks):
            c = chunks[shown]
            console.print(
                Panel(
                    c.text[:400],
                    title=f"{c.chunk_id}  crop={c.crop} region={c.region} "
                          f"season={c.season} validated={c.validated}",
                    subtitle=c.citation(),
                )
            )
            shown += 1

    console.print(
        f"[green]chunked[/green] {total} chunk(s) from {len(sources)} document(s)"
    )
    console.print(
        f"validation: {counts_all['approved']} approved, "
        f"{counts_all['unreviewed']} unreviewed, {counts_all['stale']} stale, "
        f"{counts_all['rejected']} rejected"
    )
    if counts_all["approved"] == 0:
        console.print(
            "[yellow]no chunk is human-validated yet.[/yellow] "
            "retrieval.validated_only must stay false until a reviewer signs off: "
            "`mhizha review sign <chunk_id> --reviewer \"Name\"`"
        )


@app.command()
def embed() -> None:
    """Alias for `chunk`. Vectors are produced by `index`."""
    chunk(inspect=0)


# ------------------------------------------------------------------ index


@app.command()
def index(
    stats: bool = typer.Option(False, "--stats", help="Report on the existing index"),
) -> None:
    """BUILD TIME. Embed chunks and build the single-file sqlite index."""
    from .rag.index import build_index, index_stats

    cfg = _cfg()
    if stats:
        table = Table(title="index")
        table.add_column("key")
        table.add_column("value")
        for key, value in index_stats(cfg).items():
            table.add_row(key, str(value))
        console.print(table)
        return

    try:
        report = build_index(cfg)
    except MhizhaError as exc:
        console.print(f"[red]index build failed:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(
        f"[green]built[/green] {report.chunk_count} chunks, dim {report.dim}, "
        f"backend [bold]{report.backend}[/bold], "
        f"{report.file_size_mb:.2f} MB at {cfg.index.path}"
    )
    console.print(f"embedder: {report.embedder_id}")
    console.print(f"corpus snapshot: {report.corpus_sha256[:16]}")
    if report.placeholder_count:
        console.print(
            f"[yellow]{report.placeholder_count} of {report.chunk_count} chunks are "
            f"PLACEHOLDER[/yellow] and carry no real agronomic information"
        )
    if report.validated_count == 0:
        console.print("[yellow]0 chunks are human-validated[/yellow]")


# ------------------------------------------------------------------ ask


@app.command()
def ask(
    question: str = typer.Argument(..., help="The farmer's question"),
    lang: str = typer.Option("en", "--lang", help="en | sn | nd"),
    explain: bool = typer.Option(False, "--explain", help="Passages, scores, and trace"),
    as_json: bool = typer.Option(False, "--json", help="Machine-readable response"),
    crop: str = typer.Option(None, "--crop"),
    region: str = typer.Option(None, "--region"),
    backend: str = typer.Option(None, "--backend", help="stub | llamacpp"),
) -> None:
    """RUNTIME (offline). Ask a question and get a cited, confidence-scored answer."""
    from .app.answer import answer_question
    from .llm.loader import load_backend
    from .rag.embedder import load_embedder
    from .rag.index import open_index
    from .rag.store import Filters

    cfg = _cfg()
    try:
        store = open_index(cfg)
        embedder = load_embedder(cfg.embedder)
        llm = load_backend(cfg, backend=backend)
    except MhizhaError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    filters = Filters(
        crop=crop,
        region=region,
        validated_only=cfg.retrieval.validated_only,
        allow_placeholder=cfg.retrieval.allow_placeholder,
    )
    result = answer_question(
        question, cfg=cfg, store=store, embedder=embedder, backend=llm,
        lang=lang, filters=filters,
    )

    if as_json:
        console.print_json(json.dumps(result.to_dict()))
        return

    band = result.confidence_band
    style = BAND_STYLE.get(band, "white")
    title = "Mhizha (abstained)" if result.abstained else "Mhizha"
    console.print(Panel(result.answer_text, title=title, border_style=style))

    for notice in result.notices:
        console.print(f"[yellow]{notice}[/yellow]")

    # Sources are never optional and never hidden behind a flag.
    if result.sources:
        table = Table(title="Based on", show_lines=False)
        table.add_column("id", style="dim")
        table.add_column("source")
        table.add_column("score", justify="right")
        for source in result.sources:
            table.add_row(source.passage_id, source.line(), f"{source.score:.3f}")
        console.print(table)
    elif not result.abstained:
        console.print("[red]no sources: this answer should not have been shown[/red]")

    console.print(
        f"Confidence: [{style}]{band}[/{style}] "
        f"({result.confidence.score:.3f}, top1={result.confidence.top1:.3f}, "
        f"margin={result.confidence.margin:.3f})"
    )
    if result.abstained and result.abstain_reason:
        console.print(f"[dim]reason: {result.abstain_reason}[/dim]")
    if result.fallback_from:
        console.print(
            f"[dim]language fallback to English for {len(result.fallback_from)} "
            f"string(s): translation not available yet[/dim]"
        )

    if explain:
        console.print(Panel(json.dumps(result.trace, indent=2, default=str),
                            title="trace", border_style="blue"))
        for finding in result.safety_findings:
            console.print(f"[magenta]{finding.rule} {finding.severity}[/magenta]: "
                          f"{finding.detail}")


# ------------------------------------------------------------------ eval


@app.command()
def eval(
    which: str = typer.Option("all", "--set", help="all | grounding | abstention | redteam"),
    backend: str = typer.Option(None, "--backend"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    """Run the agronomy accuracy and safety eval harness."""
    from .evaluate import run_evals

    cfg = _cfg()
    try:
        report = run_evals(cfg, which=which, backend=backend)
    except MhizhaError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    table = Table(title=f"eval ({report.backend}, corpus {report.corpus_hash[:12]})")
    table.add_column("set")
    table.add_column("cases", justify="right")
    table.add_column("passed", justify="right")
    table.add_column("metric")
    for section in report.sections:
        table.add_row(section.name, str(section.total), str(section.passed),
                      section.metric_line())
    console.print(table)

    for section in report.sections:
        # Skips are printed, never silent: a quietly skipped safety case is worse than
        # a failing one, because it looks like coverage.
        for case in section.skipped:
            console.print(f"[dim]SKIP[/dim] [{section.name}] {case.case_id}: {case.detail}")
        for case in section.failures:
            severity = "red" if case.critical else "yellow"
            console.print(
                f"[{severity}]FAIL[/{severity}] [{section.name}] {case.case_id}: "
                f"{case.detail}"
            )
            if verbose:
                console.print(f"  Q: {case.question}")
                console.print(f"  got: {case.got[:300]}")

    if report.critical_failures:
        console.print(
            f"\n[red bold]{report.critical_failures} critical failure(s). "
            f"This blocks release.[/red bold]"
        )
        raise typer.Exit(code=1)
    console.print("\n[green]no critical failures[/green]")


# ------------------------------------------------------------------ doctor


@app.command()
def doctor() -> None:
    """Report device budget, backends, index health, and offline posture."""
    from .llm.registry import budget_report
    from .rag.index import index_stats

    cfg = _cfg()
    console.print(f"[bold]profile:[/bold] {cfg.profile}   config: {cfg.source_path}")

    stats = index_stats(cfg)
    idx_table = Table(title="index")
    idx_table.add_column("key")
    idx_table.add_column("value")
    for key, value in stats.items():
        idx_table.add_row(key, str(value))
    console.print(idx_table)

    index_mb = float(stats.get("file_size_mb", 0) or 0)
    report = budget_report(cfg, index_mb=index_mb)

    budget = Table(title=f"memory budget: {cfg.device.label}")
    budget.add_column("component")
    budget.add_column("MB", justify="right")
    budget.add_column("note")
    for line in report.lines:
        budget.add_row(line.component, f"{line.mb:.0f}", line.note)
    budget.add_row("[bold]total[/bold]", f"[bold]{report.total_mb:.0f}[/bold]", "")
    budget.add_row("app budget", f"{cfg.device.app_budget_mb}", "before the LMK intervenes")
    console.print(budget)

    if report.fits:
        console.print(
            f"[green]fits[/green] with {report.headroom_mb:.0f} MB headroom "
            f"(model: {report.model.id if report.model else 'none selected'})"
        )
    else:
        console.print(
            f"[red]OVER BUDGET by {-report.headroom_mb:.0f} MB[/red] on "
            f"{cfg.device.key}. Pick a smaller model: `mhizha models list`"
        )

    emb_ok = cfg.embedder.path.is_dir() and any(cfg.embedder.path.iterdir())
    console.print(
        f"embedder weights: {'[green]present[/green]' if emb_ok else '[yellow]absent, hash fallback active[/yellow]'}"
        f"  ({cfg.embedder.path})"
    )
    if not cfg.embedder.multilingual:
        console.print(
            "[yellow]embedder is not multilingual[/yellow]: a Shona or Ndebele query "
            "cannot match an English passage. See docs/model-shortlist.md"
        )

    from .i18n import check_locales

    locale_report = check_locales(cfg.i18n.locales_dir, list(cfg.i18n.languages))
    for lang, issues in locale_report.items():
        console.print(
            f"locale {lang}: {len(issues['untranslated'])} untranslated, "
            f"{len(issues['missing'])} missing, {len(issues['orphaned'])} orphaned"
        )


# ------------------------------------------------------------------ models


@models_app.command("list")
def models_list() -> None:
    """Candidate models with sizes and whether they fit the active profile."""
    from .llm.registry import SHORTLIST, fits_profile

    cfg = _cfg()
    table = Table(
        title=f"model shortlist against {cfg.device.key} "
              f"({cfg.device.weights_budget_mb} MB for weights + embedder + index)"
    )
    table.add_column("id")
    table.add_column("params", justify="right")
    table.add_column("quant")
    table.add_column("size")
    table.add_column("licence")
    table.add_column("fits", justify="center")
    for model in SHORTLIST:
        ok = fits_profile(model, cfg.device, embedder_mb=cfg.embedder.est_size_mb)
        table.add_row(
            model.id, f"{model.params_b:.2f}B", model.quant, model.size_label,
            model.licence, "[green]yes[/green]" if ok else "[red]no[/red]",
        )
    console.print(table)
    console.print(
        "[dim]All sizes are approximate until measured on target hardware "
        "(data/SOURCES.md gap G-09).[/dim]"
    )


@models_app.command("fit")
def models_fit(profile: str = typer.Option(None, "--profile")) -> None:
    """Show which candidates fit a given device profile."""
    from .llm.registry import fits_profile, SHORTLIST

    cfg = _cfg()
    target = cfg.device_profiles.get(profile or cfg.device.key)
    if target is None:
        console.print(f"[red]unknown profile {profile!r}[/red]. "
                      f"Known: {', '.join(cfg.device_profiles)}")
        raise typer.Exit(code=1)
    console.print(f"[bold]{target.label}[/bold] "
                  f"weights budget {target.weights_budget_mb} MB")
    for model in SHORTLIST:
        ok = fits_profile(model, target, embedder_mb=cfg.embedder.est_size_mb)
        mark = "[green]fits[/green]" if ok else "[red]over [/red]"
        console.print(f"  {mark}  {model.id:<38} {model.resident_mb} MB  {model.note}")


# ------------------------------------------------------------------ i18n


@i18n_app.command("check")
def i18n_check() -> None:
    """Report missing, untranslated, and orphaned locale keys."""
    from .i18n import check_locales

    cfg = _cfg()
    report = check_locales(cfg.i18n.locales_dir, list(cfg.i18n.languages))
    problems = 0
    for lang, issues in report.items():
        console.print(f"[bold]{lang}[/bold]")
        for kind, keys in issues.items():
            if not keys:
                continue
            style = "red" if kind in ("missing", "orphaned") else "yellow"
            if kind in ("missing", "orphaned"):
                problems += len(keys)
            console.print(f"  [{style}]{kind}[/{style}] ({len(keys)}): "
                          f"{', '.join(keys[:8])}{' ...' if len(keys) > 8 else ''}")
    if problems:
        raise typer.Exit(code=1)
    console.print("[green]no missing or orphaned keys[/green]")


# ------------------------------------------------------------------ review


@review_app.command("sign")
def review_sign(
    chunk_id: str = typer.Argument(...),
    reviewer: str = typer.Option(..., "--reviewer", help="Named human. Required."),
    verdict: str = typer.Option("approved", "--verdict", help="approved | rejected"),
    note: str = typer.Option("", "--note"),
) -> None:
    """Record a human sign-off for a chunk against its exact text hash."""
    from .corpus.review import ReviewLedger
    from .corpus.schema import chunks_from_json

    cfg = _cfg()
    target = None
    for path in cfg.corpus.dir.glob("*.chunks.json"):
        for c in chunks_from_json(path.read_text(encoding="utf-8")):
            if c.chunk_id == chunk_id:
                target = c
                break
        if target:
            break
    if target is None:
        console.print(f"[red]no chunk {chunk_id}[/red]. Run `mhizha chunk` first.")
        raise typer.Exit(code=1)
    if target.placeholder:
        console.print(
            "[red]refusing to sign off a PLACEHOLDER chunk.[/red] "
            "Placeholder text contains no real agronomic information."
        )
        raise typer.Exit(code=1)

    ledger = ReviewLedger(cfg.corpus.review_ledger)
    record = ledger.sign(target, reviewer, verdict=verdict, note=note)
    console.print(
        f"[green]recorded[/green] {record.verdict} by {record.reviewer} "
        f"on {record.reviewed_on} for {record.chunk_id}"
    )
    console.print("[dim]re-run `mhizha chunk && mhizha index` to apply.[/dim]")


@review_app.command("status")
def review_status() -> None:
    """Validation state across the corpus."""
    from .corpus.review import ReviewLedger
    from .corpus.schema import chunks_from_json

    cfg = _cfg()
    ledger = ReviewLedger(cfg.corpus.review_ledger)
    counts = {"approved": 0, "rejected": 0, "stale": 0, "unreviewed": 0}
    placeholders = 0
    for path in sorted(cfg.corpus.dir.glob("*.chunks.json")):
        for c in chunks_from_json(path.read_text(encoding="utf-8")):
            counts[ledger.status(c)] += 1
            placeholders += int(c.placeholder)
    table = Table(title="review ledger")
    table.add_column("state")
    table.add_column("chunks", justify="right")
    for state, n in counts.items():
        table.add_row(state, str(n))
    table.add_row("[dim]of which placeholder[/dim]", str(placeholders))
    console.print(table)


def main() -> None:  # pragma: no cover
    try:
        app()
    except MhizhaError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
