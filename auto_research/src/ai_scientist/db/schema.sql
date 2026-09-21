-- AI Scientist Database Schema
-- Full-text search enabled with FTS5

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    seed_question TEXT,
    domain TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Papers table (arXiv papers, stored metadata)
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    arxiv_id TEXT,
    title TEXT NOT NULL,
    authors TEXT,
    abstract TEXT,
    categories TEXT,
    published_date TEXT,
    updated_date TEXT,
    pdf_url TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Full-text search for papers
CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
    title, abstract, authors, content='papers', content_rowid='rowid'
);

-- Research directions
CREATE TABLE IF NOT EXISTS directions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    hypothesis TEXT,
    novelty TEXT,
    feasibility REAL DEFAULT 0.5,
    importance REAL DEFAULT 0.5,
    status TEXT DEFAULT 'CANDIDATE',
    decision_reason TEXT,
    kill_votes INTEGER DEFAULT 0,
    total_votes INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Research questions
CREATE TABLE IF NOT EXISTS research_questions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    direction_id TEXT,
    question_text TEXT NOT NULL,
    clarity TEXT DEFAULT 'BROAD',
    feasibility TEXT DEFAULT 'THEORETICAL',
    novelty_score REAL DEFAULT 0.5,
    theories_applicable TEXT DEFAULT '[]',
    mechanisms_proposed TEXT DEFAULT '[]',
    suggested_method TEXT,
    status TEXT DEFAULT 'PROPOSED',
    rejection_reason TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (direction_id) REFERENCES directions(id)
);

-- Evidence entries
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    paper_id TEXT,
    direction_id TEXT,
    evidence_type TEXT,
    content TEXT NOT NULL,
    source TEXT,
    relevance REAL DEFAULT 0.5,
    quality REAL DEFAULT 0.5,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (paper_id) REFERENCES papers(id),
    FOREIGN KEY (direction_id) REFERENCES directions(id)
);

-- Events (research activity log)
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    content TEXT,
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Research phenomena
CREATE TABLE IF NOT EXISTS phenomena (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    raw_description TEXT NOT NULL,
    phenomenon_type TEXT,
    domain TEXT,
    scope TEXT,
    key_entities TEXT DEFAULT '[]',
    key_behaviors TEXT DEFAULT '[]',
    boundary_conditions TEXT DEFAULT '[]',
    anomalies_noted TEXT DEFAULT '[]',
    confidence TEXT DEFAULT 'MEDIUM',
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Research puzzles
CREATE TABLE IF NOT EXISTS puzzles (
    id TEXT PRIMARY KEY,
    phenomenon_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    puzzle_type TEXT,
    puzzle_statement TEXT NOT NULL,
    why_important TEXT DEFAULT '',
    current_explanations TEXT DEFAULT '[]',
    gaps_in_explanations TEXT DEFAULT '[]',
    related_constructs TEXT DEFAULT '[]',
    difficulty TEXT DEFAULT 'MEDIUM',
    tractability TEXT DEFAULT 'MEDIUM',
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (phenomenon_id) REFERENCES phenomena(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Paper analyses
CREATE TABLE IF NOT EXISTS paper_analyses (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    primary_research_question TEXT DEFAULT '',
    secondary_questions TEXT DEFAULT '[]',
    novelty_claimed TEXT DEFAULT '',
    novelty_gaps_identified TEXT DEFAULT '[]',
    contribution_type TEXT DEFAULT '',
    theories_used TEXT DEFAULT '[]',
    constructs_examined TEXT DEFAULT '[]',
    mechanisms_proposed TEXT DEFAULT '[]',
    alternative_explanations_discussed TEXT DEFAULT '[]',
    boundary_conditions TEXT DEFAULT '[]',
    research_method TEXT DEFAULT '',
    data_sources TEXT DEFAULT '[]',
    sample_size TEXT DEFAULT '',
    measurement_approaches TEXT DEFAULT '[]',
    identification_strategy TEXT DEFAULT '',
    key_findings TEXT DEFAULT '[]',
    evidence_quality TEXT DEFAULT 'MEDIUM',
    limitations TEXT DEFAULT '[]',
    cited_by_papers TEXT DEFAULT '[]',
    references_to_papers TEXT DEFAULT '[]',
    original_evidence_passages TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (paper_id) REFERENCES papers(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Nearest neighbor papers
CREATE TABLE IF NOT EXISTS nearest_neighbors (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    research_question_id TEXT,
    neighbor_type TEXT DEFAULT 'DIRECT_COMPETITOR',
    relationship_description TEXT DEFAULT '',
    similar_phenomenon INTEGER DEFAULT 0,
    similar_research_question INTEGER DEFAULT 0,
    similar_method INTEGER DEFAULT 0,
    similar_theory INTEGER DEFAULT 0,
    key_differences TEXT DEFAULT '[]',
    opportunities_from_difference TEXT DEFAULT '[]',
    novelty_threat_level TEXT DEFAULT 'MEDIUM',
    novelty_threat_explanation TEXT DEFAULT '',
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (paper_id) REFERENCES papers(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (research_question_id) REFERENCES research_questions(id)
);

-- Theories
CREATE TABLE IF NOT EXISTS theories (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    theory_name TEXT NOT NULL,
    origin_domain TEXT,
    theory_level TEXT,
    core_constructs TEXT DEFAULT '[]',
    core_propositions TEXT DEFAULT '[]',
    assumed_relationships TEXT DEFAULT '[]',
    scope_conditions TEXT DEFAULT '[]',
    excluded_contexts TEXT DEFAULT '[]',
    applicability_to_research TEXT DEFAULT '',
    adaptations_needed TEXT DEFAULT '[]',
    source_paper_id TEXT,
    source_authors TEXT DEFAULT '[]',
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (source_paper_id) REFERENCES papers(id)
);

-- Constructs
CREATE TABLE IF NOT EXISTS constructs (
    id TEXT PRIMARY KEY,
    theory_id TEXT,
    project_id TEXT NOT NULL,
    construct_name TEXT NOT NULL,
    construct_definition TEXT,
    is_latent INTEGER DEFAULT 1,
    is_multi_dimensional INTEGER DEFAULT 0,
    dimensions TEXT DEFAULT '[]',
    operationalization_status TEXT DEFAULT 'PROPOSED',
    proposed_measurements TEXT DEFAULT '[]',
    antecedent_constructs TEXT DEFAULT '[]',
    consequent_constructs TEXT DEFAULT '[]',
    role_in_research TEXT DEFAULT '',
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (theory_id) REFERENCES theories(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Mechanisms
CREATE TABLE IF NOT EXISTS mechanisms (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    mechanism_name TEXT NOT NULL,
    mechanism_type TEXT,
    causal_logic TEXT,
    necessary_conditions TEXT DEFAULT '[]',
    sufficient_conditions TEXT DEFAULT '[]',
    input_constructs TEXT DEFAULT '[]',
    output_constructs TEXT DEFAULT '[]',
    intermediate_steps TEXT DEFAULT '[]',
    theory_id TEXT,
    theoretical_rationale TEXT DEFAULT '',
    alternative_mechanisms TEXT DEFAULT '[]',
    why_this_mechanism TEXT DEFAULT '',
    scope_conditions TEXT DEFAULT '[]',
    failure_conditions TEXT DEFAULT '[]',
    testable_predictions TEXT DEFAULT '[]',
    required_evidence TEXT DEFAULT '[]',
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (theory_id) REFERENCES theories(id)
);

-- Alternative explanations
CREATE TABLE IF NOT EXISTS alternative_explanations (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    explanation_name TEXT NOT NULL,
    description TEXT,
    target_puzzle_id TEXT,
    target_phenomenon_id TEXT,
    key_differentiators TEXT DEFAULT '[]',
    supporting_evidence TEXT DEFAULT '[]',
    supporting_papers TEXT DEFAULT '[]',
    contradicting_evidence TEXT DEFAULT '[]',
    plausibility TEXT DEFAULT 'MEDIUM',
    testability TEXT DEFAULT 'MEDIUM',
    threat_level TEXT DEFAULT 'MEDIUM',
    distinguishing_tests TEXT DEFAULT '[]',
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (target_puzzle_id) REFERENCES puzzles(id),
    FOREIGN KEY (target_phenomenon_id) REFERENCES phenomena(id)
);

-- Research methods
CREATE TABLE IF NOT EXISTS research_methods (
    id TEXT PRIMARY KEY,
    research_question_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    method_type TEXT,
    method_name TEXT NOT NULL,
    method_description TEXT,
    key_design_features TEXT DEFAULT '[]',
    required_conditions TEXT DEFAULT '[]',
    internal_validity_concerns TEXT DEFAULT '[]',
    external_validity_concerns TEXT DEFAULT '[]',
    identification_strategy TEXT DEFAULT '',
    identification_strength TEXT DEFAULT 'MEDIUM',
    alternative_methods TEXT DEFAULT '[]',
    why_this_method TEXT DEFAULT '',
    feasibility_assessment TEXT DEFAULT 'MEDIUM',
    resource_requirements TEXT DEFAULT '[]',
    estimated_time TEXT DEFAULT '',
    status TEXT DEFAULT 'PROPOSED',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (research_question_id) REFERENCES research_questions(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Data sources
CREATE TABLE IF NOT EXISTS data_sources (
    id TEXT PRIMARY KEY,
    research_method_id TEXT,
    project_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_type TEXT,
    access_requirements TEXT DEFAULT '[]',
    cost_estimate TEXT DEFAULT '',
    availability_timeline TEXT DEFAULT '',
    sample_size TEXT DEFAULT '',
    time_span TEXT DEFAULT '',
    coverage TEXT DEFAULT '',
    data_quality_assessment TEXT DEFAULT 'MEDIUM',
    known_issues TEXT DEFAULT '[]',
    cleaning_required INTEGER DEFAULT 0,
    variables_available TEXT DEFAULT '[]',
    key_variables TEXT DEFAULT '[]',
    fit_assessment TEXT DEFAULT 'MEDIUM',
    fit_rationale TEXT DEFAULT '',
    status TEXT DEFAULT 'IDENTIFIED',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (research_method_id) REFERENCES research_methods(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Measurements
CREATE TABLE IF NOT EXISTS measurements (
    id TEXT PRIMARY KEY,
    construct_id TEXT,
    project_id TEXT NOT NULL,
    measurement_name TEXT NOT NULL,
    measurement_type TEXT,
    measurement_description TEXT,
    measurement_items TEXT DEFAULT '[]',
    validity_evidence TEXT DEFAULT '[]',
    reliability_evidence TEXT DEFAULT '[]',
    known_limitations TEXT DEFAULT '[]',
    construct_validity_concerns TEXT DEFAULT '[]',
    alternative_measurements TEXT DEFAULT '[]',
    status TEXT DEFAULT 'PROPOSED',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (construct_id) REFERENCES constructs(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Identification strategies
CREATE TABLE IF NOT EXISTS identification_strategies (
    id TEXT PRIMARY KEY,
    research_method_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    strategy_type TEXT,
    identification_logic TEXT,
    key_assumptions TEXT DEFAULT '[]',
    threats_to_identification TEXT DEFAULT '[]',
    how_addressed TEXT DEFAULT '[]',
    identification_strength TEXT DEFAULT 'MEDIUM',
    robustness_checks TEXT DEFAULT '[]',
    status TEXT DEFAULT 'PROPOSED',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (research_method_id) REFERENCES research_methods(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- State snapshots
CREATE TABLE IF NOT EXISTS state_snapshots (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    snapshot_name TEXT NOT NULL,
    snapshot_type TEXT,
    research_phenomena TEXT DEFAULT '[]',
    research_puzzles TEXT DEFAULT '[]',
    research_directions TEXT DEFAULT '[]',
    research_questions TEXT DEFAULT '[]',
    theories TEXT DEFAULT '[]',
    constructs TEXT DEFAULT '[]',
    mechanisms TEXT DEFAULT '[]',
    methods TEXT DEFAULT '[]',
    evidence TEXT DEFAULT '[]',
    papers TEXT DEFAULT '[]',
    decision_made TEXT DEFAULT '',
    decision_rationale TEXT DEFAULT '',
    parent_snapshot_id TEXT,
    branch_name TEXT,
    stage TEXT DEFAULT '',
    key_insights TEXT DEFAULT '[]',
    open_questions TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (parent_snapshot_id) REFERENCES state_snapshots(id)
);

-- Contract versions
CREATE TABLE IF NOT EXISTS contract_versions (
    id TEXT PRIMARY KEY,
    research_question_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    version_number INTEGER,
    version_status TEXT DEFAULT 'DRAFT',
    research_question TEXT DEFAULT '',
    theoretical_grounding TEXT DEFAULT '',
    proposed_mechanism TEXT DEFAULT '',
    alternative_explanations TEXT DEFAULT '[]',
    proposed_method TEXT DEFAULT '',
    data_source TEXT DEFAULT '',
    measurement_plan TEXT DEFAULT '',
    expected_contribution TEXT DEFAULT '',
    reviewer_notes TEXT DEFAULT '',
    revision_requests TEXT DEFAULT '[]',
    approved_by TEXT DEFAULT '',
    changes_from_previous TEXT DEFAULT '[]',
    previous_version_id TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (research_question_id) REFERENCES research_questions(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (previous_version_id) REFERENCES contract_versions(id)
);

-- Debates
CREATE TABLE IF NOT EXISTS debates (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    direction_id TEXT,
    status TEXT DEFAULT 'IN_PROGRESS',
    current_round INTEGER DEFAULT 0,
    max_rounds INTEGER DEFAULT 4,
    kill_threshold REAL DEFAULT 0.6,
    final_status TEXT,
    conclusion TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (direction_id) REFERENCES directions(id)
);

-- Debate rounds
CREATE TABLE IF NOT EXISTS debate_rounds (
    id TEXT PRIMARY KEY,
    debate_id TEXT NOT NULL,
    round_number INTEGER NOT NULL,
    agent_role TEXT NOT NULL,
    agent_position TEXT,
    arguments TEXT DEFAULT '[]',
    objections TEXT DEFAULT '[]',
    votes TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (debate_id) REFERENCES debates(id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_papers_project ON papers(project_id);
CREATE INDEX IF NOT EXISTS idx_papers_arxiv ON papers(arxiv_id);
CREATE INDEX IF NOT EXISTS idx_directions_project ON directions(project_id);
CREATE INDEX IF NOT EXISTS idx_directions_status ON directions(status);
CREATE INDEX IF NOT EXISTS idx_research_questions_project ON research_questions(project_id);
CREATE INDEX IF NOT EXISTS idx_research_questions_direction ON research_questions(direction_id);
CREATE INDEX IF NOT EXISTS idx_evidence_project ON evidence(project_id);
CREATE INDEX IF NOT EXISTS idx_events_project ON events(project_id);
CREATE INDEX IF NOT EXISTS idx_phenomena_project ON phenomena(project_id);
CREATE INDEX IF NOT EXISTS idx_puzzles_phenomenon ON puzzles(phenomenon_id);
CREATE INDEX IF NOT EXISTS idx_puzzles_project ON puzzles(project_id);
CREATE INDEX IF NOT EXISTS idx_paper_analyses_paper ON paper_analyses(paper_id);
CREATE INDEX IF NOT EXISTS idx_nearest_neighbors_paper ON nearest_neighbors(paper_id);
CREATE INDEX IF NOT EXISTS idx_nearest_neighbors_rq ON nearest_neighbors(research_question_id);
CREATE INDEX IF NOT EXISTS idx_theories_project ON theories(project_id);
CREATE INDEX IF NOT EXISTS idx_constructs_theory ON constructs(theory_id);
CREATE INDEX IF NOT EXISTS idx_constructs_project ON constructs(project_id);
CREATE INDEX IF NOT EXISTS idx_mechanisms_project ON mechanisms(project_id);
CREATE INDEX IF NOT EXISTS idx_mechanisms_theory ON mechanisms(theory_id);
CREATE INDEX IF NOT EXISTS idx_research_methods_rq ON research_methods(research_question_id);
CREATE INDEX IF NOT EXISTS idx_data_sources_method ON data_sources(research_method_id);
CREATE INDEX IF NOT EXISTS idx_measurements_construct ON measurements(construct_id);
CREATE INDEX IF NOT EXISTS idx_state_snapshots_project ON state_snapshots(project_id);
CREATE INDEX IF NOT EXISTS idx_contract_versions_rq ON contract_versions(research_question_id);
CREATE INDEX IF NOT EXISTS idx_debates_project ON debates(project_id);
CREATE INDEX IF NOT EXISTS idx_debate_rounds_debate ON debate_rounds(debate_id);

-- Persistent Objection Ledger (v4)
CREATE TABLE IF NOT EXISTS scientific_objections (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    target_type TEXT NOT NULL,              -- RESEARCH_QUESTION, DIRECTION, THEORY, MECHANISM, etc.
    target_id TEXT NOT NULL,                -- ID of the target entity

    category TEXT NOT NULL,                 -- INTERNAL_CONSISTENCY, EVIDENCE_QUALITY, etc.
    severity TEXT NOT NULL,                 -- FATAL, MAJOR, MINOR
    title TEXT NOT NULL,                    -- Short summary
    argument TEXT NOT NULL,                 -- Full argument/proof

    supporting_evidence_ids TEXT DEFAULT '[]',   -- JSON array of evidence IDs
    contradictory_evidence_ids TEXT DEFAULT '[]', -- JSON array of evidence IDs

    introduced_in_run INTEGER DEFAULT 0,    -- Which run first raised this
    last_reviewed_in_run INTEGER DEFAULT 0, -- Last run where reviewed
    status TEXT DEFAULT 'OPEN',             -- OPEN, UNDER_REVIEW, RESOLVED, INVALIDATED, ACCEPTED_RISK, REQUIRES_HUMAN

    resolution_type TEXT,                   -- ADDRESSED, DISMISSED, ACCEPTED, RETRACTED, PIVOTED_AROUND, UNRESOLVED
    resolution_reason TEXT DEFAULT '',
    resolved_by_evidence_ids TEXT DEFAULT '[]', -- JSON array

    raised_by TEXT DEFAULT 'RED_TEAM',      -- Who raised: RED_TEAM, DEBATE, HUMAN, etc.
    review_notes TEXT DEFAULT '[]',         -- JSON array of review history

    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),

    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Indexes for scientific_objections
CREATE INDEX IF NOT EXISTS idx_objections_project ON scientific_objections(project_id);
CREATE INDEX IF NOT EXISTS idx_objections_target ON scientific_objections(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_objections_severity ON scientific_objections(severity);
CREATE INDEX IF NOT EXISTS idx_objections_status ON scientific_objections(status);
CREATE INDEX IF NOT EXISTS idx_objections_run ON scientific_objections(introduced_in_run, last_reviewed_in_run);
