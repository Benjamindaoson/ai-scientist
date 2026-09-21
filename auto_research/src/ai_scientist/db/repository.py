"""Database repository for AI Scientist.

Handles all database operations with SQLite.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator


def _dt_now() -> str:
    return datetime.utcnow().isoformat()


def _gen_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


class Database:
    """SQLite database wrapper with connection management."""

    def __init__(self, db_path: str | Path = "ai_scientist.db"):
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        # Resolve to absolute path to avoid path issues (except for :memory:)
        if str(self.db_path) != ":memory:" and not self.db_path.is_absolute():
            self.db_path = Path.cwd() / self.db_path

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections."""
        # For :memory:, use a persistent connection
        if str(self.db_path) == ":memory:":
            if self._conn is None:
                self._conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA foreign_keys = ON")
            yield self._conn
            # Don't close for :memory: - connection is persistent
        else:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query with parameters."""
        with self.connect() as conn:
            return conn.execute(sql, params)

    def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        """Fetch a single row."""
        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        """Fetch all rows."""
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def commit(self) -> None:
        """Commit pending transaction."""
        with self.connect() as conn:
            conn.execute("COMMIT")

    def init_schema(self) -> None:
        """Initialize database schema from SQL file."""
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            with self.connect() as conn:
                conn.executescript(schema_sql)


class Repository:
    """Repository pattern for database operations."""

    def __init__(self, db: Database):
        self.db = db

    # ──────────────────────────────────────────────
    # Projects
    # ──────────────────────────────────────────────

    def create_project(
        self,
        name: str,
        description: str = "",
        seed_question: str = "",
        domain: str = "",
    ) -> dict:
        """Create a new research project."""
        project_id = _gen_id("proj_")
        self.db.execute(
            """INSERT INTO projects (id, name, description, seed_question, domain)
               VALUES (?, ?, ?, ?, ?)""",
            (project_id, name, description, seed_question, domain),
        )
        return self.get_project(project_id)

    def get_project(self, project_id: str) -> dict | None:
        """Get project by ID."""
        return self.db.fetch_one("SELECT * FROM projects WHERE id = ?", (project_id,))

    def list_projects(self) -> list[dict]:
        """List all projects."""
        return self.db.fetch_all("SELECT * FROM projects ORDER BY created_at DESC")

    # ──────────────────────────────────────────────
    # Papers
    # ──────────────────────────────────────────────

    def create_paper(
        self,
        project_id: str,
        title: str,
        arxiv_id: str = "",
        authors: str = "",
        abstract: str = "",
        categories: str = "",
    ) -> dict:
        """Create a new paper entry."""
        paper_id = _gen_id("paper_")
        self.db.execute(
            """INSERT INTO papers (id, project_id, arxiv_id, title, authors, abstract, categories)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (paper_id, project_id, arxiv_id, title, authors, abstract, categories),
        )
        return self.get_paper(paper_id)

    def get_paper(self, paper_id: str) -> dict | None:
        """Get paper by ID."""
        return self.db.fetch_one("SELECT * FROM papers WHERE id = ?", (paper_id,))

    def list_papers(self, project_id: str) -> list[dict]:
        """List papers for a project."""
        return self.db.fetch_all(
            "SELECT * FROM papers WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )

    def search_papers(self, query: str, project_id: str) -> list[dict]:
        """Full-text search papers."""
        with self.db.connect() as conn:
            rows = conn.execute(
                """SELECT p.* FROM papers p
                   JOIN papers_fts fts ON p.rowid = fts.rowid
                   WHERE papers_fts MATCH ? AND p.project_id = ?
                   ORDER BY rank""",
                (query, project_id),
            ).fetchall()
            return [dict(row) for row in rows]

    # ──────────────────────────────────────────────
    # Directions
    # ──────────────────────────────────────────────

    def create_direction(
        self,
        project_id: str,
        title: str,
        hypothesis: str = "",
        novelty: str = "",
        feasibility: float = 0.5,
        importance: float = 0.5,
    ) -> dict:
        """Create a new research direction."""
        direction_id = _gen_id("dir_")
        self.db.execute(
            """INSERT INTO directions
               (id, project_id, title, hypothesis, novelty, feasibility, importance)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (direction_id, project_id, title, hypothesis, novelty, feasibility, importance),
        )
        return self.get_direction(direction_id)

    def get_direction(self, direction_id: str) -> dict | None:
        """Get direction by ID."""
        return self.db.fetch_one(
            "SELECT * FROM directions WHERE id = ?", (direction_id,)
        )

    def list_directions(
        self, project_id: str, status: str | None = None
    ) -> list[dict]:
        """List directions for a project, optionally filtered by status."""
        if status:
            return self.db.fetch_all(
                "SELECT * FROM directions WHERE project_id = ? AND status = ? "
                "ORDER BY importance DESC, feasibility DESC",
                (project_id, status),
            )
        return self.db.fetch_all(
            "SELECT * FROM directions WHERE project_id = ? "
            "ORDER BY importance DESC, feasibility DESC",
            (project_id,),
        )

    def update_direction_status(
        self, direction_id: str, new_status: str, decision_reason: str = ""
    ) -> None:
        """Update direction status after debate."""
        self.db.execute(
            "UPDATE directions SET status = ?, decision_reason = ?, updated_at = ? "
            "WHERE id = ?",
            (new_status, decision_reason, _dt_now(), direction_id),
        )

    def update_direction_votes(
        self, direction_id: str, kill_votes: int, total_votes: int
    ) -> None:
        """Update vote counts for a direction."""
        self.db.execute(
            "UPDATE directions SET kill_votes = ?, total_votes = ?, updated_at = ? "
            "WHERE id = ?",
            (kill_votes, total_votes, _dt_now(), direction_id),
        )

    # ──────────────────────────────────────────────
    # Research Questions
    # ──────────────────────────────────────────────

    def create_research_question(
        self,
        project_id: str,
        question_text: str,
        direction_id: str | None = None,
        theories_applicable: list[str] | None = None,
        mechanisms_proposed: list[str] | None = None,
        suggested_method: str = "",
        novelty_score: float = 0.5,
    ) -> dict:
        """Create a research question."""
        rq_id = _gen_id("rq_")
        self.db.execute(
            """INSERT INTO research_questions
               (id, project_id, direction_id, question_text, theories_applicable,
                mechanisms_proposed, suggested_method, novelty_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                rq_id,
                project_id,
                direction_id if direction_id else None,  # NULL for empty string
                question_text,
                json.dumps(theories_applicable or []),
                json.dumps(mechanisms_proposed or []),
                suggested_method,
                novelty_score,
            ),
        )
        return self.get_research_question(rq_id)

    def get_research_question(self, rq_id: str) -> dict | None:
        """Get research question by ID."""
        return self.db.fetch_one(
            "SELECT * FROM research_questions WHERE id = ?", (rq_id,)
        )

    def list_research_questions(
        self, project_id: str, status: str | None = None
    ) -> list[dict]:
        """List research questions for a project."""
        if status:
            return self.db.fetch_all(
                "SELECT * FROM research_questions WHERE project_id = ? AND status = ? "
                "ORDER BY novelty_score DESC",
                (project_id, status),
            )
        return self.db.fetch_all(
            "SELECT * FROM research_questions WHERE project_id = ? "
            "ORDER BY novelty_score DESC",
            (project_id,),
        )

    def update_research_question(self, rq_id: str, **kwargs) -> None:
        """Update research question fields."""
        set_clauses = []
        values = []
        for key, value in kwargs.items():
            set_clauses.append(f"{key} = ?")
            if isinstance(value, list):
                values.append(json.dumps(value))
            else:
                values.append(value)
        set_clauses.append("updated_at = ?")
        values.append(_dt_now())
        values.append(rq_id)
        self.db.execute(
            f"UPDATE research_questions SET {', '.join(set_clauses)} WHERE id = ?",
            tuple(values),
        )

    # ──────────────────────────────────────────────
    # Evidence
    # ──────────────────────────────────────────────

    def create_evidence(
        self,
        project_id: str,
        content: str,
        evidence_type: str = "",
        paper_id: str = "",
        direction_id: str = "",
        source: str = "",
        relevance: float = 0.5,
        quality: float = 0.5,
    ) -> dict:
        """Create an evidence entry."""
        evidence_id = _gen_id("ev_")
        self.db.execute(
            """INSERT INTO evidence
               (id, project_id, paper_id, direction_id, evidence_type, content,
                source, relevance, quality)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                evidence_id,
                project_id,
                paper_id,
                direction_id,
                evidence_type,
                content,
                source,
                relevance,
                quality,
            ),
        )
        return self.get_evidence(evidence_id)

    def get_evidence(self, evidence_id: str) -> dict | None:
        """Get evidence by ID."""
        return self.db.fetch_one("SELECT * FROM evidence WHERE id = ?", (evidence_id,))

    def list_evidence(
        self,
        project_id: str,
        direction_id: str | None = None,
        paper_id: str | None = None,
    ) -> list[dict]:
        """List evidence for a project."""
        query = "SELECT * FROM evidence WHERE project_id = ?"
        params: tuple = (project_id,)
        if direction_id:
            query += " AND direction_id = ?"
            params += (direction_id,)
        if paper_id:
            query += " AND paper_id = ?"
            params += (paper_id,)
        query += " ORDER BY relevance DESC, quality DESC"
        return self.db.fetch_all(query, params)

    # ──────────────────────────────────────────────
    # Events
    # ──────────────────────────────────────────────

    def create_event(
        self,
        project_id: str,
        event_type: str,
        content: str = "",
        metadata: dict | None = None,
    ) -> dict:
        """Create an event log entry."""
        event_id = _gen_id("evt_")
        self.db.execute(
            """INSERT INTO events (id, project_id, event_type, content, metadata)
               VALUES (?, ?, ?, ?, ?)""",
            (event_id, project_id, event_type, content, json.dumps(metadata or {})),
        )
        return self.get_event(event_id)

    def get_event(self, event_id: str) -> dict | None:
        """Get event by ID."""
        return self.db.fetch_one("SELECT * FROM events WHERE id = ?", (event_id,))

    def list_events(
        self, project_id: str, event_type: str | None = None, limit: int = 100
    ) -> list[dict]:
        """List events for a project."""
        if event_type:
            return self.db.fetch_all(
                "SELECT * FROM events WHERE project_id = ? AND event_type = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (project_id, event_type, limit),
            )
        return self.db.fetch_all(
            "SELECT * FROM events WHERE project_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (project_id, limit),
        )

    # ──────────────────────────────────────────────
    # Research Phenomena
    # ──────────────────────────────────────────────

    def create_phenomenon(
        self,
        project_id: str,
        raw_description: str,
        phenomenon_type: str,
        domain: str = "",
        scope: str = "micro",
        **kwargs,
    ) -> dict:
        """Create a research phenomenon."""
        phen_id = _gen_id("phen_")
        self.db.execute(
            """INSERT INTO phenomena
               (id, project_id, raw_description, phenomenon_type, domain, scope)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (phen_id, project_id, raw_description, phenomenon_type, domain, scope),
        )
        # Update additional fields
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.db.execute(
                    f"UPDATE phenomena SET {key} = ? WHERE id = ?",
                    (json.dumps(value), phen_id),
                )
        return self.get_phenomenon(phen_id)

    def get_phenomenon(self, phen_id: str) -> dict | None:
        """Get phenomenon by ID."""
        return self.db.fetch_one("SELECT * FROM phenomena WHERE id = ?", (phen_id,))

    def list_phenomena(self, project_id: str) -> list[dict]:
        """List phenomena for a project."""
        return self.db.fetch_all(
            "SELECT * FROM phenomena WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )

    # ──────────────────────────────────────────────
    # Research Puzzles
    # ──────────────────────────────────────────────

    def create_puzzle(
        self,
        phenomenon_id: str,
        project_id: str,
        puzzle_statement: str,
        puzzle_type: str,
        **kwargs,
    ) -> dict:
        """Create a research puzzle."""
        puzzle_id = _gen_id("puz_")
        self.db.execute(
            """INSERT INTO puzzles
               (id, phenomenon_id, project_id, puzzle_statement, puzzle_type)
               VALUES (?, ?, ?, ?, ?)""",
            (puzzle_id, phenomenon_id, project_id, puzzle_statement, puzzle_type),
        )
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.db.execute(
                    f"UPDATE puzzles SET {key} = ? WHERE id = ?",
                    (json.dumps(value), puzzle_id),
                )
        return self.get_puzzle(puzzle_id)

    def get_puzzle(self, puzzle_id: str) -> dict | None:
        """Get puzzle by ID."""
        return self.db.fetch_one("SELECT * FROM puzzles WHERE id = ?", (puzzle_id,))

    def list_puzzles(self, project_id: str, phenomenon_id: str | None = None) -> list[dict]:
        """List puzzles."""
        if phenomenon_id:
            return self.db.fetch_all(
                "SELECT * FROM puzzles WHERE phenomenon_id = ? ORDER BY created_at DESC",
                (phenomenon_id,),
            )
        return self.db.fetch_all(
            "SELECT * FROM puzzles WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )

    # ──────────────────────────────────────────────
    # Paper Analyses
    # ──────────────────────────────────────────────

    def create_paper_analysis(
        self, paper_id: str, project_id: str, **kwargs
    ) -> dict:
        """Create a paper analysis."""
        analysis_id = _gen_id("ana_")
        self.db.execute(
            """INSERT INTO paper_analyses (id, paper_id, project_id)
               VALUES (?, ?, ?)""",
            (analysis_id, paper_id, project_id),
        )
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.db.execute(
                    f"UPDATE paper_analyses SET {key} = ? WHERE id = ?",
                    (json.dumps(value), analysis_id),
                )
        return self.get_paper_analysis(analysis_id)

    def get_paper_analysis(self, analysis_id: str) -> dict | None:
        """Get paper analysis by ID."""
        return self.db.fetch_one(
            "SELECT * FROM paper_analyses WHERE id = ?", (analysis_id,)
        )

    def get_paper_analysis_by_paper(self, paper_id: str) -> dict | None:
        """Get analysis for a paper."""
        return self.db.fetch_one(
            "SELECT * FROM paper_analyses WHERE paper_id = ?", (paper_id,)
        )

    def list_paper_analyses(self, project_id: str) -> list[dict]:
        """List paper analyses for a project."""
        return self.db.fetch_all(
            "SELECT * FROM paper_analyses WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )

    # ──────────────────────────────────────────────
    # Nearest Neighbor Papers
    # ──────────────────────────────────────────────

    def create_nearest_neighbor(self, paper_id: str, project_id: str, **kwargs) -> dict:
        """Create a nearest neighbor entry."""
        nn_id = _gen_id("nn_")
        self.db.execute(
            """INSERT INTO nearest_neighbors (id, paper_id, project_id)
               VALUES (?, ?, ?)""",
            (nn_id, paper_id, project_id),
        )
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.db.execute(
                    f"UPDATE nearest_neighbors SET {key} = ? WHERE id = ?",
                    (json.dumps(value), nn_id),
                )
        return self.get_nearest_neighbor(nn_id)

    def get_nearest_neighbor(self, nn_id: str) -> dict | None:
        """Get nearest neighbor by ID."""
        return self.db.fetch_one(
            "SELECT * FROM nearest_neighbors WHERE id = ?", (nn_id,)
        )

    def list_nearest_neighbors(
        self, research_question_id: str | None = None, project_id: str | None = None
    ) -> list[dict]:
        """List nearest neighbors."""
        if research_question_id:
            return self.db.fetch_all(
                "SELECT * FROM nearest_neighbors WHERE research_question_id = ?",
                (research_question_id,),
            )
        if project_id:
            return self.db.fetch_all(
                "SELECT * FROM nearest_neighbors WHERE project_id = ?",
                (project_id,),
            )
        return []

    # ──────────────────────────────────────────────
    # Theories
    # ──────────────────────────────────────────────

    def create_theory(self, project_id: str, theory_name: str, **kwargs) -> dict:
        """Create a theory."""
        theory_id = _gen_id("theo_")
        self.db.execute(
            """INSERT INTO theories (id, project_id, theory_name)
               VALUES (?, ?, ?)""",
            (theory_id, project_id, theory_name),
        )
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.db.execute(
                    f"UPDATE theories SET {key} = ? WHERE id = ?",
                    (json.dumps(value), theory_id),
                )
        return self.get_theory(theory_id)

    def get_theory(self, theory_id: str) -> dict | None:
        """Get theory by ID."""
        return self.db.fetch_one("SELECT * FROM theories WHERE id = ?", (theory_id,))

    def list_theories(self, project_id: str) -> list[dict]:
        """List theories for a project."""
        return self.db.fetch_all(
            "SELECT * FROM theories WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )

    # ──────────────────────────────────────────────
    # Constructs
    # ──────────────────────────────────────────────

    def create_construct(
        self, project_id: str, construct_name: str, **kwargs
    ) -> dict:
        """Create a construct."""
        construct_id = _gen_id("cons_")
        self.db.execute(
            """INSERT INTO constructs (id, project_id, construct_name)
               VALUES (?, ?, ?)""",
            (construct_id, project_id, construct_name),
        )
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.db.execute(
                    f"UPDATE constructs SET {key} = ? WHERE id = ?",
                    (json.dumps(value), construct_id),
                )
        return self.get_construct(construct_id)

    def get_construct(self, construct_id: str) -> dict | None:
        """Get construct by ID."""
        return self.db.fetch_one(
            "SELECT * FROM constructs WHERE id = ?", (construct_id,)
        )

    def list_constructs(self, project_id: str, theory_id: str | None = None) -> list[dict]:
        """List constructs."""
        if theory_id:
            return self.db.fetch_all(
                "SELECT * FROM constructs WHERE theory_id = ?",
                (theory_id,),
            )
        return self.db.fetch_all(
            "SELECT * FROM constructs WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )

    # ──────────────────────────────────────────────
    # Mechanisms
    # ──────────────────────────────────────────────

    def create_mechanism(
        self, project_id: str, mechanism_name: str, **kwargs
    ) -> dict:
        """Create a mechanism."""
        mech_id = _gen_id("mech_")
        self.db.execute(
            """INSERT INTO mechanisms (id, project_id, mechanism_name)
               VALUES (?, ?, ?)""",
            (mech_id, project_id, mechanism_name),
        )
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.db.execute(
                    f"UPDATE mechanisms SET {key} = ? WHERE id = ?",
                    (json.dumps(value), mech_id),
                )
        return self.get_mechanism(mech_id)

    def get_mechanism(self, mech_id: str) -> dict | None:
        """Get mechanism by ID."""
        return self.db.fetch_one("SELECT * FROM mechanisms WHERE id = ?", (mech_id,))

    def list_mechanisms(self, project_id: str) -> list[dict]:
        """List mechanisms for a project."""
        return self.db.fetch_all(
            "SELECT * FROM mechanisms WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )

    # ──────────────────────────────────────────────
    # Alternative Explanations
    # ──────────────────────────────────────────────

    def create_alternative_explanation(
        self, project_id: str, explanation_name: str, **kwargs
    ) -> dict:
        """Create an alternative explanation."""
        alt_id = _gen_id("alt_")
        self.db.execute(
            """INSERT INTO alternative_explanations (id, project_id, explanation_name)
               VALUES (?, ?, ?)""",
            (alt_id, project_id, explanation_name),
        )
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.db.execute(
                    f"UPDATE alternative_explanations SET {key} = ? WHERE id = ?",
                    (json.dumps(value), alt_id),
                )
        return self.get_alternative_explanation(alt_id)

    def get_alternative_explanation(self, alt_id: str) -> dict | None:
        """Get alternative explanation by ID."""
        return self.db.fetch_one(
            "SELECT * FROM alternative_explanations WHERE id = ?", (alt_id,)
        )

    def list_alternative_explanations(self, project_id: str) -> list[dict]:
        """List alternative explanations."""
        return self.db.fetch_all(
            "SELECT * FROM alternative_explanations WHERE project_id = ? "
            "ORDER BY threat_level DESC",
            (project_id,),
        )

    # ──────────────────────────────────────────────
    # Research Methods
    # ──────────────────────────────────────────────

    def create_research_method(
        self, research_question_id: str, project_id: str, method_name: str, **kwargs
    ) -> dict:
        """Create a research method."""
        method_id = _gen_id("meth_")
        self.db.execute(
            """INSERT INTO research_methods
               (id, research_question_id, project_id, method_name)
               VALUES (?, ?, ?, ?)""",
            (method_id, research_question_id, project_id, method_name),
        )
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.db.execute(
                    f"UPDATE research_methods SET {key} = ? WHERE id = ?",
                    (json.dumps(value), method_id),
                )
        return self.get_research_method(method_id)

    def get_research_method(self, method_id: str) -> dict | None:
        """Get research method by ID."""
        return self.db.fetch_one(
            "SELECT * FROM research_methods WHERE id = ?", (method_id,)
        )

    def list_research_methods(self, research_question_id: str) -> list[dict]:
        """List research methods for a question."""
        return self.db.fetch_all(
            "SELECT * FROM research_methods WHERE research_question_id = ?",
            (research_question_id,),
        )

    # ──────────────────────────────────────────────
    # Data Sources
    # ──────────────────────────────────────────────

    def create_data_source(
        self, project_id: str, source_name: str, **kwargs
    ) -> dict:
        """Create a data source."""
        ds_id = _gen_id("ds_")
        self.db.execute(
            """INSERT INTO data_sources (id, project_id, source_name)
               VALUES (?, ?, ?)""",
            (ds_id, project_id, source_name),
        )
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.db.execute(
                    f"UPDATE data_sources SET {key} = ? WHERE id = ?",
                    (json.dumps(value), ds_id),
                )
        return self.get_data_source(ds_id)

    def get_data_source(self, ds_id: str) -> dict | None:
        """Get data source by ID."""
        return self.db.fetch_one("SELECT * FROM data_sources WHERE id = ?", (ds_id,))

    def list_data_sources(self, project_id: str) -> list[dict]:
        """List data sources for a project."""
        return self.db.fetch_all(
            "SELECT * FROM data_sources WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )

    # ──────────────────────────────────────────────
    # State Snapshots
    # ──────────────────────────────────────────────

    def create_state_snapshot(
        self, project_id: str, snapshot_name: str, snapshot_type: str, **kwargs
    ) -> dict:
        """Create a state snapshot."""
        snap_id = _gen_id("snap_")
        self.db.execute(
            """INSERT INTO state_snapshots (id, project_id, snapshot_name, snapshot_type)
               VALUES (?, ?, ?, ?)""",
            (snap_id, project_id, snapshot_name, snapshot_type),
        )
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.db.execute(
                    f"UPDATE state_snapshots SET {key} = ? WHERE id = ?",
                    (json.dumps(value), snap_id),
                )
        return self.get_state_snapshot(snap_id)

    def get_state_snapshot(self, snap_id: str) -> dict | None:
        """Get state snapshot by ID."""
        return self.db.fetch_one(
            "SELECT * FROM state_snapshots WHERE id = ?", (snap_id,)
        )

    def list_state_snapshots(self, project_id: str) -> list[dict]:
        """List state snapshots for a project."""
        return self.db.fetch_all(
            "SELECT * FROM state_snapshots WHERE project_id = ? "
            "ORDER BY created_at DESC",
            (project_id,),
        )

    # ──────────────────────────────────────────────
    # Contract Versions
    # ──────────────────────────────────────────────

    def create_contract_version(
        self, research_question_id: str, project_id: str, version_number: int, **kwargs
    ) -> dict:
        """Create a contract version."""
        cv_id = _gen_id("cv_")
        self.db.execute(
            """INSERT INTO contract_versions
               (id, research_question_id, project_id, version_number)
               VALUES (?, ?, ?, ?)""",
            (cv_id, research_question_id, project_id, version_number),
        )
        for key, value in kwargs.items():
            if isinstance(value, list):
                self.db.execute(
                    f"UPDATE contract_versions SET {key} = ? WHERE id = ?",
                    (json.dumps(value), cv_id),
                )
        return self.get_contract_version(cv_id)

    def get_contract_version(self, cv_id: str) -> dict | None:
        """Get contract version by ID."""
        return self.db.fetch_one(
            "SELECT * FROM contract_versions WHERE id = ?", (cv_id,)
        )

    def list_contract_versions(self, research_question_id: str) -> list[dict]:
        """List contract versions for a question."""
        return self.db.fetch_all(
            "SELECT * FROM contract_versions WHERE research_question_id = ? "
            "ORDER BY version_number DESC",
            (research_question_id,),
        )

    # ──────────────────────────────────────────────
    # Debates
    # ──────────────────────────────────────────────

    def create_debate(
        self,
        project_id: str,
        direction_id: str | None = None,
        max_rounds: int = 4,
        kill_threshold: float = 0.6,
    ) -> dict:
        """Create a new debate."""
        debate_id = _gen_id("debate_")
        self.db.execute(
            """INSERT INTO debates
               (id, project_id, direction_id, max_rounds, kill_threshold)
               VALUES (?, ?, ?, ?, ?)""",
            (debate_id, project_id, direction_id, max_rounds, kill_threshold),
        )
        return self.get_debate(debate_id)

    def get_debate(self, debate_id: str) -> dict | None:
        """Get debate by ID."""
        return self.db.fetch_one("SELECT * FROM debates WHERE id = ?", (debate_id,))

    def update_debate(
        self, debate_id: str, status: str | None = None, current_round: int | None = None,
        final_status: str | None = None, conclusion: str | None = None
    ) -> None:
        """Update debate fields."""
        updates = []
        values = []
        if status is not None:
            updates.append("status = ?")
            values.append(status)
        if current_round is not None:
            updates.append("current_round = ?")
            values.append(current_round)
        if final_status is not None:
            updates.append("final_status = ?")
            values.append(final_status)
        if conclusion is not None:
            updates.append("conclusion = ?")
            values.append(conclusion)
        updates.append("updated_at = ?")
        values.append(_dt_now())
        values.append(debate_id)
        self.db.execute(
            f"UPDATE debates SET {', '.join(updates)} WHERE id = ?", tuple(values)
        )

    def list_debates(self, project_id: str) -> list[dict]:
        """List debates for a project."""
        return self.db.fetch_all(
            "SELECT * FROM debates WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )

    # ──────────────────────────────────────────────
    # Debate Rounds
    # ──────────────────────────────────────────────

    def create_debate_round(
        self,
        debate_id: str,
        round_number: int,
        agent_role: str,
        agent_position: str = "",
        arguments: list | None = None,
        objections: list | None = None,
        votes: dict | None = None,
    ) -> dict:
        """Create a debate round."""
        round_id = _gen_id("round_")
        self.db.execute(
            """INSERT INTO debate_rounds
               (id, debate_id, round_number, agent_role, agent_position)
               VALUES (?, ?, ?, ?, ?)""",
            (round_id, debate_id, round_number, agent_role, agent_position),
        )
        if arguments:
            self.db.execute(
                "UPDATE debate_rounds SET arguments = ? WHERE id = ?",
                (json.dumps(arguments), round_id),
            )
        if objections:
            self.db.execute(
                "UPDATE debate_rounds SET objections = ? WHERE id = ?",
                (json.dumps(objections), round_id),
            )
        if votes:
            self.db.execute(
                "UPDATE debate_rounds SET votes = ? WHERE id = ?",
                (json.dumps(votes), round_id),
            )
        return self.get_debate_round(round_id)

    def get_debate_round(self, round_id: str) -> dict | None:
        """Get debate round by ID."""
        return self.db.fetch_one(
            "SELECT * FROM debate_rounds WHERE id = ?", (round_id,)
        )

    def list_debate_rounds(self, debate_id: str) -> list[dict]:
        """List rounds for a debate."""
        return self.db.fetch_all(
            "SELECT * FROM debate_rounds WHERE debate_id = ? ORDER BY round_number",
            (debate_id,),
        )

    # ──────────────────────────────────────────────
    # Persistent Objection Ledger (v4)
    # ──────────────────────────────────────────────

    def create_objection(self, objection: dict) -> dict:
        """Create a new scientific objection.

        Args:
            objection: Dict with all objection fields (see ScientificObjection model)

        Returns:
            The created objection record
        """
        objection_id = objection.get("id") or _gen_id("obj_")

        # Ensure JSON fields are serialized
        supporting_evidence = json.dumps(objection.get("supporting_evidence_ids", []))
        contradictory_evidence = json.dumps(objection.get("contradictory_evidence_ids", []))
        resolved_by_evidence = json.dumps(objection.get("resolved_by_evidence_ids", []))
        review_notes = json.dumps(objection.get("review_notes", []))

        self.db.execute(
            """INSERT INTO scientific_objections
               (id, project_id, target_type, target_id, category, severity, title,
                argument, supporting_evidence_ids, contradictory_evidence_ids,
                introduced_in_run, last_reviewed_in_run, status,
                resolution_type, resolution_reason, resolved_by_evidence_ids,
                raised_by, review_notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                objection_id,
                objection["project_id"],
                objection["target_type"],
                objection["target_id"],
                objection["category"],
                objection["severity"],
                objection["title"],
                objection["argument"],
                supporting_evidence,
                contradictory_evidence,
                objection.get("introduced_in_run", 0),
                objection.get("last_reviewed_in_run", 0),
                objection.get("status", "OPEN"),
                objection.get("resolution_type"),
                objection.get("resolution_reason", ""),
                resolved_by_evidence,
                objection.get("raised_by", "RED_TEAM"),
                review_notes,
            ),
        )
        return self.get_objection(objection_id)

    def get_objection(self, objection_id: str) -> dict | None:
        """Get objection by ID."""
        row = self.db.fetch_one(
            "SELECT * FROM scientific_objections WHERE id = ?", (objection_id,)
        )
        if row:
            return self._deserialize_objection(row)
        return None

    def list_objections(
        self,
        project_id: str,
        target_type: str | None = None,
        target_id: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        introduced_in_run: int | None = None,
    ) -> list[dict]:
        """List objections with optional filters.

        Args:
            project_id: Project to list objections for
            target_type: Filter by target type (RESEARCH_QUESTION, DIRECTION, etc.)
            target_id: Filter by specific target ID
            severity: Filter by severity (FATAL, MAJOR, MINOR)
            status: Filter by status (OPEN, UNDER_REVIEW, RESOLVED, etc.)
            introduced_in_run: Filter by run number

        Returns:
            List of objection records
        """
        sql = "SELECT * FROM scientific_objections WHERE project_id = ?"
        params: list = [project_id]

        if target_type:
            sql += " AND target_type = ?"
            params.append(target_type)
        if target_id:
            sql += " AND target_id = ?"
            params.append(target_id)
        if severity:
            sql += " AND severity = ?"
            params.append(severity)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if introduced_in_run is not None:
            sql += " AND introduced_in_run = ?"
            params.append(introduced_in_run)

        sql += " ORDER BY CASE severity WHEN 'FATAL' THEN 0 WHEN 'MAJOR' THEN 1 ELSE 2 END, created_at"

        rows = self.db.fetch_all(sql, tuple(params))
        return [self._deserialize_objection(row) for row in rows]

    def get_open_objections(
        self,
        project_id: str,
        severity: str | None = None,
    ) -> list[dict]:
        """Get all open (non-resolved) objections.

        Args:
            project_id: Project to check
            severity: Optional severity filter (FATAL only by default if specified)

        Returns:
            List of open objection records
        """
        sql = """SELECT * FROM scientific_objections
                 WHERE project_id = ?
                 AND status IN ('OPEN', 'UNDER_REVIEW', 'REQUIRES_HUMAN')"""
        params: list = [project_id]

        if severity:
            sql += " AND severity = ?"
            params.append(severity)

        sql += " ORDER BY CASE severity WHEN 'FATAL' THEN 0 WHEN 'MAJOR' THEN 1 ELSE 2 END"

        rows = self.db.fetch_all(sql, tuple(params))
        return [self._deserialize_objection(row) for row in rows]

    def get_fatal_objections(self, project_id: str) -> list[dict]:
        """Get all open FATAL objections for a project.

        These block research continuation.

        Returns:
            List of open FATAL objection records
        """
        return self.get_open_objections(project_id, severity="FATAL")

    def get_objections_by_run(self, project_id: str, run_number: int) -> list[dict]:
        """Get all objections introduced in or reviewed in a specific run.

        Args:
            project_id: Project to check
            run_number: Run number to filter by

        Returns:
            List of objection records
        """
        rows = self.db.fetch_all(
            """SELECT * FROM scientific_objections
               WHERE project_id = ?
               AND (introduced_in_run = ? OR last_reviewed_in_run = ?)
               ORDER BY CASE severity WHEN 'FATAL' THEN 0 WHEN 'MAJOR' THEN 1 ELSE 2 END""",
            (project_id, run_number, run_number),
        )
        return [self._deserialize_objection(row) for row in rows]

    def update_objection_status(
        self,
        objection_id: str,
        status: str,
        resolution_type: str | None = None,
        resolution_reason: str = "",
        resolved_by_evidence_ids: list | None = None,
        last_reviewed_in_run: int | None = None,
        review_note: str | None = None,
    ) -> dict | None:
        """Update objection status and resolution.

        Args:
            objection_id: ID of objection to update
            status: New status (RESOLVED, INVALIDATED, ACCEPTED_RISK, etc.)
            resolution_type: How it was resolved (ADDRESSED, DISMISSED, etc.)
            resolution_reason: Explanation of resolution
            resolved_by_evidence_ids: Evidence that resolved it
            last_reviewed_in_run: Update the last reviewed run number
            review_note: Add a note to the review history

        Returns:
            Updated objection record or None if not found
        """
        updates = ["status = ?", "updated_at = ?"]
        params: list = [status, _dt_now()]

        if resolution_type:
            updates.append("resolution_type = ?")
            params.append(resolution_type)
        if resolution_reason:
            updates.append("resolution_reason = ?")
            params.append(resolution_reason)
        if resolved_by_evidence_ids is not None:
            updates.append("resolved_by_evidence_ids = ?")
            params.append(json.dumps(resolved_by_evidence_ids))
        if last_reviewed_in_run is not None:
            updates.append("last_reviewed_in_run = ?")
            params.append(last_reviewed_in_run)
        if review_note:
            # Load existing notes, append new one, save back
            existing = self.get_objection(objection_id)
            if existing:
                notes = existing.get("review_notes", [])
                if isinstance(notes, str):
                    notes = json.loads(notes)
                notes.append(review_note)
                updates.append("review_notes = ?")
                params.append(json.dumps(notes))

        params.append(objection_id)

        self.db.execute(
            f"UPDATE scientific_objections SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        return self.get_objection(objection_id)

    def mark_objection_reviewed(
        self,
        objection_id: str,
        run_number: int,
        review_note: str | None = None,
    ) -> dict | None:
        """Mark an objection as reviewed in the current run.

        Args:
            objection_id: ID of objection to mark
            run_number: Current run number
            review_note: Optional review note to add

        Returns:
            Updated objection record
        """
        updates = ["last_reviewed_in_run = ?", "status = CASE WHEN status = 'OPEN' THEN 'UNDER_REVIEW' ELSE status END", "updated_at = ?"]
        params: list = [run_number, _dt_now()]

        if review_note:
            existing = self.get_objection(objection_id)
            if existing:
                notes = existing.get("review_notes", [])
                if isinstance(notes, str):
                    notes = json.loads(notes)
                notes.append(review_note)
                updates.append("review_notes = ?")
                params.append(json.dumps(notes))

        params.append(objection_id)

        self.db.execute(
            f"UPDATE scientific_objections SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        return self.get_objection(objection_id)

    def delete_objection(self, objection_id: str) -> bool:
        """Delete an objection.

        Args:
            objection_id: ID of objection to delete

        Returns:
            True if deleted, False if not found
        """
        self.db.execute(
            "DELETE FROM scientific_objections WHERE id = ?", (objection_id,)
        )
        return True

    def _deserialize_objection(self, row: dict) -> dict:
        """Deserialize a scientific_objections row.

        Converts JSON string fields back to Python objects.
        """
        result = dict(row)

        # Parse JSON fields
        for field in ["supporting_evidence_ids", "contradictory_evidence_ids",
                      "resolved_by_evidence_ids", "review_notes"]:
            if field in result and isinstance(result[field], str):
                try:
                    result[field] = json.loads(result[field])
                except (json.JSONDecodeError, TypeError):
                    result[field] = []

        # Parse datetime fields
        for field in ["created_at", "updated_at"]:
            if field in result and result[field]:
                result[field] = str(result[field])

        return result
