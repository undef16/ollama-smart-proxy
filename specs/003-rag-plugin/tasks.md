# Tasks: RAG Plugin

**Input**: Design documents from `/specs/003-rag-plugin/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are not requested in the feature specification, so they are not included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Plugin**: `src/plugins/rag/` following hexagonal architecture
- **Domain**: `src/plugins/rag/domain/`
- **Infrastructure**: `src/plugins/rag/infrastructure/`
- **Tests**: `src/plugins/rag/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic plugin structure

- [ ] T001 Create plugin directory structure per implementation plan
- [ ] T002 Initialize Python package files (__init__.py) in all directories
- [ ] T003 [P] Configure plugin dependencies in pyproject.toml or requirements.txt

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core plugin infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create base agent class extending BaseAgent in src/plugins/rag/__init__.py
- [ ] T005 [P] Implement configuration loading from config.json in src/plugins/rag/infrastructure/config.py
- [ ] T006 [P] Create domain entities (Query, Document, RelevanceScore) in src/plugins/rag/domain/entities/
- [ ] T007 [P] Define domain ports (RagRepository, SearchService) in src/plugins/rag/domain/ports/
- [ ] T008 Setup error handling and logging infrastructure in src/plugins/rag/infrastructure/logging.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Enable RAG-enhanced responses (Priority: P1) 🎯 MVP

**Goal**: Implement basic RAG functionality that intercepts /rag commands and enhances responses with local knowledge base context

**Independent Test**: Send a /rag prompt and verify that the response includes context from LightRAG without web search

### Implementation for User Story 1

- [ ] T009 [US1] Create main RagAgent class implementing on_retrieve method in src/plugins/rag/agent.py
- [ ] T010 [US1] Implement LightRAG adapter in src/plugins/rag/infrastructure/adapters/lightrag_adapter.py
- [ ] T011 [US1] Create CRAG graph with retrieve and grade nodes in src/plugins/rag/infrastructure/langgraph/crag_graph.py
- [ ] T012 [US1] Implement inject node for prompt enhancement in src/plugins/rag/infrastructure/langgraph/nodes/inject_node.py
- [ ] T013 [US1] Add plugin registration and command detection in src/plugins/rag/__init__.py
- [ ] T014 [US1] Integrate with proxy on_retrieve event handling

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Fallback to web search (Priority: P2)

**Goal**: Add web search capability when local knowledge is insufficient

**Independent Test**: Send a /rag prompt for unknown topic and verify web search is triggered and results are injected

### Implementation for User Story 2

- [ ] T015 [US2] Implement SearxNG adapter in src/plugins/rag/infrastructure/adapters/searxng_adapter.py
- [ ] T016 [US2] Create web search node in src/plugins/rag/infrastructure/langgraph/nodes/web_search_node.py
- [ ] T017 [US2] Implement query transformation node in src/plugins/rag/infrastructure/langgraph/nodes/transform_query_node.py
- [ ] T018 [US2] Update CRAG graph to include web search transitions in src/plugins/rag/infrastructure/langgraph/crag_graph.py
- [ ] T019 [US2] Add relevance threshold checking in grade node

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T020 [P] Add performance monitoring in src/plugins/rag/infrastructure/monitoring/performance_monitor.py
- [ ] T021 [P] Implement circuit breaker for external services in src/plugins/rag/infrastructure/resilience/circuit_breaker.py
- [ ] T022 Add comprehensive error handling and logging
- [ ] T023 [P] Documentation updates in specs/003-rag-plugin/
- [ ] T024 Code cleanup and refactoring
- [ ] T025 Run quickstart.md validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Builds on US1 but should be independently testable

### Within Each User Story

- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all foundational entities together:
Task: "Create domain entities (Query, Document, RelevanceScore) in src/plugins/rag/domain/entities/"
Task: "Define domain ports (RagRepository, SearchService) in src/plugins/rag/domain/ports/"

# Launch all adapters for User Story 1 together:
Task: "Implement LightRAG adapter in src/plugins/rag/infrastructure/adapters/lightrag_adapter.py"
Task: "Create CRAG graph with retrieve and grade nodes in src/plugins/rag/infrastructure/langgraph/crag_graph.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence